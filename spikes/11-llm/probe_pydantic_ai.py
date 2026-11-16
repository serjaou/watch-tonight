"""feat-011 spike Q5: what does Pydantic AI add over the plain SDKs for our two structured calls?

THROWAWAY. Same schemas and prompts as probe_llm.py. Demonstrates, with evidence:
  1. switching provider = changing one model object (same Agent, same output_type);
  2. output_validator + ModelRetry: our step-6 checks become retries WITH the error fed back;
  3. FallbackModel: primary fails (bad key) -> secondary answers, same call site;
  4. TestModel / FunctionModel: unit tests with no network (like a Moq fake of the port);
  5. rough overhead vs the plain SDK on the same calls (latency, tokens, output mode).

Run:
  uv run --no-project --python 3.13 --with "pydantic-ai-slim[openai,google]" --with fastembed \
      python -W ignore::SyntaxWarning spikes/11-llm/probe_pydantic_ai.py \
      --openai-model gpt-6-luna --gemini-model gemini-3.5-flash-lite
Add --fallback-only to re-run just the FallbackModel rows (keeps the earlier live rows; its own
args go to "fallback_args"). Offline fallback/retry checks: probe_fallback_offline.py.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

import prompts  # noqa: E402
import schemas  # noqa: E402
from envfile import require  # noqa: E402
from probe_llm import MOVIES_PATH, QUERIES_PATH, Retriever  # noqa: E402
from pydantic_ai import Agent, ModelRetry, NativeOutput, RunContext  # noqa: E402
from pydantic_ai.models.fallback import FallbackModel  # noqa: E402
from pydantic_ai.models.function import AgentInfo, FunctionModel  # noqa: E402
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings  # noqa: E402
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings  # noqa: E402
from pydantic_ai.models.test import TestModel  # noqa: E402
from pydantic_ai.providers.google import GoogleProvider  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402

OUT_PATH = SPIKE_DIR / "runs_pydantic_ai.json"


def build_models(args: argparse.Namespace) -> dict[str, tuple[Any, Any]]:
    oai = OpenAIChatModel(
        args.openai_model, provider=OpenAIProvider(api_key=require("OPENAI_API_KEY"))
    )
    gem = GoogleModel(args.gemini_model, provider=GoogleProvider(api_key=require("GEMINI_API_KEY")))
    oai_settings = OpenAIChatModelSettings(openai_reasoning_effort=args.openai_reasoning)  # type: ignore[typeddict-item]
    gem_settings = GoogleModelSettings(
        google_thinking_config={"thinking_level": args.gemini_thinking}
    )  # type: ignore[typeddict-item]
    return {"openai": (oai, oai_settings), "gemini": (gem, gem_settings)}


def understand_agent(native: bool) -> Agent[None, schemas.Intent]:
    output_type: Any = NativeOutput(schemas.Intent) if native else schemas.Intent
    agent: Agent[None, schemas.Intent] = Agent(
        output_type=output_type, instructions=prompts.UNDERSTAND_SYSTEM, retries=1
    )

    @agent.output_validator
    def _check(intent: schemas.Intent) -> schemas.Intent:
        problems = schemas.check_intent(intent)
        if problems:
            raise ModelRetry("Fix these problems: " + "; ".join(problems))
        return intent

    return agent


def rerank_agent(native: bool) -> Agent[set[int], schemas.Rerank]:
    output_type: Any = NativeOutput(schemas.Rerank) if native else schemas.Rerank
    agent: Agent[set[int], schemas.Rerank] = Agent(
        output_type=output_type,
        instructions=prompts.RERANK_SYSTEM,
        deps_type=set[int],  # candidate IDs, injected per run (like a scoped DI service)
        retries=1,
    )

    @agent.output_validator
    def _check(ctx: RunContext[set[int]], rerank: schemas.Rerank) -> schemas.Rerank:
        problems = schemas.check_rerank(rerank, ctx.deps)
        if problems:
            # Pydantic AI sends this text back to the model and asks again (one retry).
            raise ModelRetry("Fix these problems: " + "; ".join(problems))
        return rerank

    return agent


def usage_dict(result: Any) -> dict[str, Any]:
    u = result.usage()
    return {
        "requests": u.requests,
        "input_tokens": u.input_tokens,
        "output_tokens": u.output_tokens,
    }


def live_runs(args: argparse.Namespace, out: dict[str, Any]) -> None:
    movies = json.loads(MOVIES_PATH.read_text(encoding="utf-8"))
    queries = [q for q in json.loads(QUERIES_PATH.read_text(encoding="utf-8"))]
    queries = [q for q in queries if q["id"] in set(args.queries.split(","))]
    retriever = Retriever(movies)
    models = build_models(args)
    rows: list[dict[str, Any]] = []
    for provider, (model, settings) in models.items():
        for native in (False, True):
            und_agent = understand_agent(native)
            rr_agent = rerank_agent(native)
            for q in queries:
                row: dict[str, Any] = {
                    "provider": provider,
                    "output_mode": "native" if native else "tool (default)",
                    "query_id": q["id"],
                }
                try:
                    t0 = time.perf_counter()
                    res = und_agent.run_sync(
                        prompts.understand_user(q["text"]), model=model, model_settings=settings
                    )
                    row["understand_ms"] = round((time.perf_counter() - t0) * 1000)
                    row["understand_usage"] = usage_dict(res)
                    intent = res.output
                    candidates = retriever.top_k(intent.summary_en, 40)
                    ids = {int(m["tmdb_id"]) for m in candidates}
                    t0 = time.perf_counter()
                    res2 = rr_agent.run_sync(
                        prompts.rerank_user(intent, candidates),
                        model=model,
                        model_settings=settings,
                        deps=ids,
                    )
                    row["rerank_ms"] = round((time.perf_counter() - t0) * 1000)
                    row["rerank_usage"] = usage_dict(res2)
                    row["max_pitch_chars"] = max(len(p.pitch) for p in res2.output.picks)
                    row["ok"] = True
                except Exception as exc:  # spike: record
                    row["ok"] = False
                    row["error"] = f"{type(exc).__name__}: {exc}"[:400]
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False))
                time.sleep(args.min_interval)
    out["live"] = rows


def describe_exc(exc: BaseException) -> str:
    subs = getattr(exc, "exceptions", None)
    if subs:
        return f"{type(exc).__name__}: " + " | ".join(describe_exc(s) for s in subs)
    return f"{type(exc).__name__}: {exc}"[:300]


def fallback_runs(args: argparse.Namespace, out: dict[str, Any]) -> None:
    """FallbackModel: same call site, next model on API errors (4xx/5xx), not on bad output."""
    models = build_models(args)
    broken = OpenAIChatModel(args.openai_model, provider=OpenAIProvider(api_key="sk-invalid"))
    setups = {
        "broken_key_then_openai": FallbackModel(broken, models["openai"][0]),
        "gemini_free_then_openai": FallbackModel(models["gemini"][0], models["openai"][0]),
    }
    results: list[dict[str, Any]] = []
    for name, model in setups.items():
        for i in range(3 if name.startswith("gemini") else 1):
            t0 = time.perf_counter()
            try:
                res = understand_agent(True).run_sync(
                    prompts.understand_user("Something cosy and funny, under 100 minutes"),
                    model=model,
                )
                row = {
                    "setup": name,
                    "try": i + 1,
                    "ok": True,
                    "answered_by": res.response.model_name,
                    "ms": round((time.perf_counter() - t0) * 1000),
                }
            except Exception as exc:
                row = {"setup": name, "try": i + 1, "ok": False, "error": describe_exc(exc)}
            results.append(row)
            print("fallback:", json.dumps(row, ensure_ascii=False))
            time.sleep(args.min_interval)
    out["fallback"] = results


def offline_fakes(out: dict[str, Any]) -> None:
    """What a unit test of the use case would look like: no network, no keys."""
    # TestModel generates schema-valid data from output_type (like AutoFixture). That data is
    # not semantically valid (max_runtime_minutes=0), so our validator rejects it twice and the
    # run ends with UnexpectedModelBehavior: evidence that validators + the retry budget apply
    # to fakes too.
    from pydantic_ai import UnexpectedModelBehavior

    try:
        understand_agent(False).run_sync("anything", model=TestModel())
        out["testmodel_default"] = "accepted"
    except UnexpectedModelBehavior as exc:
        out["testmodel_default"] = f"rejected by output_validator: {exc}"
    valid = {
        "input_language": "en",
        "summary_en": "A light comedy.",
        "tone": ["light"],
        "themes": ["comedy"],
        "max_runtime_minutes": None,
        "avoid": [],
        "max_intensity": None,
    }
    res = understand_agent(False).run_sync("anything", model=TestModel(custom_output_args=valid))
    out["testmodel_output"] = res.output.model_dump()

    # FunctionModel scripts the reply; first reply invents an ID, so the validator retries.
    calls = {"n": 0}

    def scripted(messages: list[Any], info: AgentInfo) -> Any:
        from pydantic_ai.messages import ModelResponse, ToolCallPart

        calls["n"] += 1
        tool = info.output_tools[0].name
        bad = {"picks": [{"tmdb_id": 999, "pitch": "x"}]}
        good = {"picks": [{"tmdb_id": 1, "pitch": "A quiet, warm drama."}]}
        return ModelResponse(parts=[ToolCallPart(tool, bad if calls["n"] == 1 else good)])

    res2 = rerank_agent(False).run_sync("req", model=FunctionModel(scripted), deps={1})
    out["functionmodel_retry"] = {"model_calls": calls["n"], "output": res2.output.model_dump()}
    keys = ("testmodel_default", "testmodel_output", "functionmodel_retry")
    print("fakes:", json.dumps({k: out[k] for k in keys}))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--openai-model", required=True)
    ap.add_argument("--openai-reasoning", default="none")
    ap.add_argument("--gemini-model", required=True)
    ap.add_argument("--gemini-thinking", default="minimal")
    ap.add_argument(
        "--queries", default="q02-en-tense-no-gore,q06-es-light-90,q10-ja-heartwarming-anime"
    )
    ap.add_argument("--min-interval", type=float, default=4.0)
    ap.add_argument("--offline-only", action="store_true")
    ap.add_argument("--fallback-only", action="store_true", help="keep earlier live rows")
    args = ap.parse_args()

    import importlib.metadata as md

    out: dict[str, Any] = {"pydantic_ai_slim": md.version("pydantic-ai-slim"), "args": vars(args)}
    if args.fallback_only and OUT_PATH.exists():
        out = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        out["fallback_args"] = vars(args)
    else:
        offline_fakes(out)
        if not args.offline_only:
            live_runs(args, out)
    if not args.offline_only:
        fallback_runs(args, out)
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT_PATH.name}")


if __name__ == "__main__":
    main()
