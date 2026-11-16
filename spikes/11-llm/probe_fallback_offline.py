"""feat-011 spike Q5/Q6: FallbackModel and retry defaults, exercised offline (no network, no keys).

THROWAWAY. Answers review findings that were stated from docs only:
  - which failures make FallbackModel move to the next model (503, 429, timeout, 401) and which
    don't (invalid output -> re-prompt the same model, never fall back);
  - the output retry budget when Agent(retries=...) is NOT passed.

Run: uv run --no-project --python 3.13 --with "pydantic-ai-slim[openai,google]" \
         python -W ignore spikes/11-llm/probe_fallback_offline.py
Writes spikes/11-llm/fallback_offline.json.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

import schemas  # noqa: E402
from pydantic_ai import Agent, ModelRetry, UnexpectedModelBehavior  # noqa: E402
from pydantic_ai import exceptions as exc  # noqa: E402
from pydantic_ai.messages import ModelResponse, ToolCallPart  # noqa: E402
from pydantic_ai.models.fallback import FallbackModel  # noqa: E402
from pydantic_ai.models.function import AgentInfo, FunctionModel  # noqa: E402

OUT_PATH = SPIKE_DIR / "fallback_offline.json"
GOOD = {"picks": [{"tmdb_id": 1, "pitch": "A quiet, warm drama."}]}
BAD = {"picks": [{"tmdb_id": 999, "pitch": "Invented."}]}  # not a candidate -> check fails


def rerank_agent(retries: int | None) -> Agent[set[int], schemas.Rerank]:
    kwargs: dict[str, Any] = {} if retries is None else {"retries": retries}
    agent: Agent[set[int], schemas.Rerank] = Agent(
        output_type=schemas.Rerank, deps_type=set[int], **kwargs
    )

    @agent.output_validator
    def _check(ctx: Any, rerank: schemas.Rerank) -> schemas.Rerank:
        problems = schemas.check_rerank(rerank, ctx.deps)
        if problems:
            raise ModelRetry("; ".join(problems))
        return rerank

    return agent


def replying(name: str, payload: dict[str, Any], counter: dict[str, int]) -> FunctionModel:
    def fn(messages: list[Any], info: AgentInfo) -> ModelResponse:
        counter[name] = counter.get(name, 0) + 1
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, payload)])

    return FunctionModel(fn, model_name=name)


def raising(name: str, make: Callable[[], Exception], counter: dict[str, int]) -> FunctionModel:
    def fn(messages: list[Any], info: AgentInfo) -> ModelResponse:
        counter[name] = counter.get(name, 0) + 1
        raise make()

    return FunctionModel(fn, model_name=name)


FAILURES: dict[str, Callable[[], Exception]] = {
    "503_unavailable": lambda: exc.ModelUnavailableError("primary", "503 high demand"),
    "503_http": lambda: exc.ModelHTTPError(503, "primary", {"error": "UNAVAILABLE"}),
    "429_rate_limit": lambda: exc.ModelHTTPError(429, "primary", {"error": "RESOURCE_EXHAUSTED"}),
    "timeout": lambda: exc.ModelTimeoutError("primary", "read timeout"),
    "401_auth": lambda: exc.ModelHTTPError(401, "primary", {"error": "invalid key"}),
}


def main() -> None:
    import importlib.metadata as md
    import inspect

    default_on = inspect.signature(FallbackModel.__init__).parameters["fallback_on"].default
    out: dict[str, Any] = {
        "pydantic_ai_slim": md.version("pydantic-ai-slim"),
        "fallback_on_default": [getattr(c, "__name__", repr(c)) for c in default_on],
        # The cases below raise Pydantic AI's exception types directly. They show how
        # FallbackModel reacts to each type; they do NOT show that the real OpenAI/Google
        # models map SDK 429s/timeouts to these types (only 401 and 503 were seen live).
        "api_failures": {},
        "invalid_output": {},
        "retry_budget": {},
    }

    # 1. API failures on the primary: does the call fall back to the secondary?
    for label, make in FAILURES.items():
        calls: dict[str, int] = {}
        model = FallbackModel(raising("primary", make, calls), replying("secondary", GOOD, calls))
        try:
            res = rerank_agent(None).run_sync("req", model=model, deps={1})
            row: dict[str, Any] = {"fell_back": True, "answered_by": res.response.model_name}
        except Exception as e:  # record whatever happens
            row = {"fell_back": False, "error": f"{type(e).__name__}: {e}"[:200]}
        row["calls"] = calls
        out["api_failures"][label] = row

    # 2. Invalid output on the primary: re-prompted on the same model, or fallback?
    calls = {}
    model = FallbackModel(replying("primary", BAD, calls), replying("secondary", GOOD, calls))
    try:
        res = rerank_agent(None).run_sync("req", model=model, deps={1})
        out["invalid_output"] = {"result": "answered", "by": res.response.model_name}
    except UnexpectedModelBehavior as e:
        out["invalid_output"] = {"result": f"{type(e).__name__}: {e}"}
    out["invalid_output"]["calls"] = calls

    # 3. Retry budget: model always returns invalid output; count model calls.
    for retries in (None, 0, 1, 2):
        calls = {}
        try:
            rerank_agent(retries).run_sync("req", model=replying("m", BAD, calls), deps={1})
            outcome = "accepted"
        except UnexpectedModelBehavior as e:
            outcome = str(e)
        key = "not passed" if retries is None else f"retries={retries}"
        out["retry_budget"][key] = {"model_calls": calls.get("m", 0), "outcome": outcome}

    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
