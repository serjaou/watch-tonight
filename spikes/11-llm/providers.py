"""feat-011 spike: plain-SDK adapters (openai, google-genai) behind one tiny interface.

THROWAWAY. Shape of a future `LanguageModel` port: `structured(system, user, schema)` returns a
validated Pydantic object plus usage and timing. SDK-level retries are OFF (max_retries=0 /
no retry options) so latency is raw and 429s are visible; the spike's own retry policy lives in
`StructuredCaller.call`.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from envfile import require
from pydantic import BaseModel, ValidationError


@dataclass
class Attempt:
    ok: bool
    latency_ms: float
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    error: str = ""
    raw: str = ""
    raised: bool = False  # API error / exception: no response body (older runs: latency_ms == 0)


@dataclass
class CallResult:
    provider: str
    model: str
    kind: str
    parsed: Any = None
    attempts: list[Attempt] = field(default_factory=list)
    rate_limited: int = 0
    rate_limit_errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.parsed is not None

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["parsed"] = self.parsed.model_dump() if isinstance(self.parsed, BaseModel) else None
        return d


class Backend(Protocol):
    provider: str
    model: str

    def once(self, system: str, user: str, schema: type[BaseModel]) -> tuple[Attempt, str]: ...


def _is_rate_limit(exc: Exception) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return "429" in text or "ratelimit" in text or "resource_exhausted" in text or "quota" in text


def _is_daily_quota(exc: Exception) -> bool:
    text = str(exc).lower().replace("_", "")
    return "perday" in text or "requestsperday" in text or "insufficientquota" in text


class DailyQuotaExceeded(RuntimeError):
    """Raised so the orchestrator stops instead of waiting minutes per call."""


# ---------------------------------------------------------------------------
# OpenAI (Chat Completions + Structured Outputs, strict json_schema)
# ---------------------------------------------------------------------------
class OpenAIBackend:
    provider = "openai"

    def __init__(self, model: str, reasoning_effort: str | None) -> None:
        from openai import OpenAI

        self.model = model
        self.reasoning_effort = reasoning_effort
        self.client = OpenAI(api_key=require("OPENAI_API_KEY"), max_retries=0, timeout=90)

    def once(self, system: str, user: str, schema: type[BaseModel]) -> tuple[Attempt, str]:
        kwargs: dict[str, Any] = {}
        if self.reasoning_effort:
            kwargs["reasoning_effort"] = self.reasoning_effort
        start = time.perf_counter()
        # `parse` turns the Pydantic model into a strict JSON schema (response_format) and
        # validates the reply, like System.Text.Json deserialising into a record type.
        completion = self.client.chat.completions.parse(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format=schema,
            **kwargs,
        )
        latency = (time.perf_counter() - start) * 1000
        msg = completion.choices[0].message
        usage = completion.usage
        att = Attempt(ok=False, latency_ms=latency)
        if usage is not None:
            att.input_tokens = usage.prompt_tokens
            att.output_tokens = usage.completion_tokens
            if usage.prompt_tokens_details is not None:
                att.cached_tokens = usage.prompt_tokens_details.cached_tokens or 0
            if usage.completion_tokens_details is not None:
                att.reasoning_tokens = usage.completion_tokens_details.reasoning_tokens or 0
        raw = msg.content or ""
        if msg.refusal:
            att.error = f"refusal: {msg.refusal}"
        return att, raw


# ---------------------------------------------------------------------------
# Gemini (google-genai, response_mime_type=application/json + response_schema)
# ---------------------------------------------------------------------------
class GeminiBackend:
    provider = "gemini"

    def __init__(self, model: str, thinking: str | None, legacy_schema: bool = False) -> None:
        from google import genai

        self.model = model
        self.thinking = thinking  # "level:low", "level:minimal", "budget:0" or None
        # legacy_schema=True uses `response_schema` (OpenAPI subset). It rejects integer enums
        # such as Literal[1, 2, 3, 4, 5] client-side (spike finding), so the default is the newer
        # `response_json_schema`, which takes Pydantic's standard JSON Schema as-is.
        self.legacy_schema = legacy_schema
        self.client = genai.Client(api_key=require("GEMINI_API_KEY"))

    def _thinking_config(self) -> Any:
        from google.genai import types

        if not self.thinking:
            return None
        kind, _, value = self.thinking.partition(":")
        if kind == "budget":
            return types.ThinkingConfig(thinking_budget=int(value))
        return types.ThinkingConfig(thinking_level=types.ThinkingLevel(value.upper()))

    def once(self, system: str, user: str, schema: type[BaseModel]) -> tuple[Attempt, str]:
        from google.genai import types

        schema_kwargs: dict[str, Any] = (
            {"response_schema": schema}
            if self.legacy_schema
            else {"response_json_schema": schema.model_json_schema()}
        )
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            thinking_config=self._thinking_config(),
            **schema_kwargs,
        )
        start = time.perf_counter()
        response = self.client.models.generate_content(
            model=self.model, contents=user, config=config
        )
        latency = (time.perf_counter() - start) * 1000
        att = Attempt(ok=False, latency_ms=latency)
        meta = response.usage_metadata
        if meta is not None:
            att.input_tokens = meta.prompt_token_count or 0
            att.cached_tokens = meta.cached_content_token_count or 0
            att.output_tokens = meta.candidates_token_count or 0
            att.reasoning_tokens = meta.thoughts_token_count or 0
        return att, response.text or ""


# ---------------------------------------------------------------------------
# Spike retry policy: 1 retry on invalid output (query steps 2 and 6), and patient
# waiting on 429 so the free tier's per-minute limits don't end the run.
# ---------------------------------------------------------------------------
class StructuredCaller:
    def __init__(self, backend: Backend, min_interval_s: float = 0.0, max_429_waits: int = 6):
        self.backend = backend
        self.min_interval_s = min_interval_s
        self.max_429_waits = max_429_waits
        self._last_call = 0.0

    def _pace(self) -> None:
        wait = self.min_interval_s - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def call(
        self,
        kind: str,
        system: str,
        user: str,
        schema: type[BaseModel],
        checks: Any = None,
        retries: int = 1,
    ) -> CallResult:
        result = CallResult(provider=self.backend.provider, model=self.backend.model, kind=kind)
        tries = 0
        waits = 0
        while tries <= retries:
            self._pace()
            started = time.perf_counter()
            try:
                att, raw = self.backend.once(system, user, schema)
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - started) * 1000
                if _is_rate_limit(exc):
                    # Keep the provider's own words: Google publishes no free-tier numbers,
                    # but its 429 body names the quota metric and limit.
                    if len(result.rate_limit_errors) < 3:
                        result.rate_limit_errors.append(f"{type(exc).__name__}: {exc}"[:1500])
                    if _is_daily_quota(exc):
                        raise DailyQuotaExceeded(str(exc)[:1500]) from exc
                    if waits < self.max_429_waits:
                        waits += 1
                        result.rate_limited += 1
                        time.sleep(min(65, 10 * waits))
                        continue
                # Review fix: time failed attempts too (bench1 recorded them as 0 ms, which
                # understated Gemini's "incl. retries" latency; 429 back-off sleeps are still
                # excluded and counted separately in rate_limited).
                result.attempts.append(
                    Attempt(
                        ok=False,
                        latency_ms=elapsed_ms,
                        error=f"{type(exc).__name__}: {exc}"[:500],
                        raised=True,
                    )
                )
                tries += 1
                continue
            att.raw = raw
            tries += 1
            if not att.error:
                try:
                    parsed = schema.model_validate_json(raw)
                except ValidationError as exc:
                    att.error = f"schema: {exc.error_count()} errors: {str(exc)[:300]}"
                else:
                    problems = checks(parsed) if checks else []
                    if problems:
                        att.error = "checks: " + "; ".join(problems)
                    else:
                        att.ok = True
                        result.parsed = parsed
            result.attempts.append(att)
            if att.ok:
                break
        return result


def make_backend(provider: str, model: str, reasoning: str | None) -> Backend:
    if provider == "openai":
        return OpenAIBackend(model, reasoning)
    if provider == "gemini":
        return GeminiBackend(model, reasoning)
    raise SystemExit(f"unknown provider {provider}")
