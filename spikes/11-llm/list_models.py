"""List the models each API key can see (feat-011 evidence for which models exist today).

Run: uv run --no-project python spikes/11-llm/list_models.py
Writes spikes/11-llm/models.json. Never prints keys.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from envfile import require

OUT = Path(__file__).resolve().parent / "models.json"


def get_json(url: str, headers: dict[str, str]) -> dict[str, object]:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def gemini_models() -> list[dict[str, object]]:
    key = require("GEMINI_API_KEY")
    out: list[dict[str, object]] = []
    token = ""
    while True:
        url = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200"
        if token:
            url += f"&pageToken={token}"
        data = get_json(url, {"x-goog-api-key": key})
        for m in data.get("models", []):  # type: ignore[union-attr]
            methods = m.get("supportedGenerationMethods", [])
            if "generateContent" in methods:
                out.append(
                    {
                        "name": m.get("name"),
                        "displayName": m.get("displayName"),
                        "inputTokenLimit": m.get("inputTokenLimit"),
                        "outputTokenLimit": m.get("outputTokenLimit"),
                        "thinking": m.get("thinking"),
                    }
                )
        token = str(data.get("nextPageToken") or "")
        if not token:
            return out


def openai_models() -> list[str]:
    key = require("OPENAI_API_KEY")
    data = get_json("https://api.openai.com/v1/models", {"Authorization": f"Bearer {key}"})
    return sorted(str(m["id"]) for m in data.get("data", []))  # type: ignore[union-attr]


def main() -> None:
    report: dict[str, object] = {"checked_at": datetime.now(UTC).isoformat()}
    for name, fn in (("gemini", gemini_models), ("openai", openai_models)):
        try:
            report[name] = fn()
        except Exception as exc:  # spike: record and keep going
            report[name] = {"error": f"{type(exc).__name__}: {exc}"}
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    gem = report["gemini"]
    oai = report["openai"]
    print("gemini:", [m["name"] for m in gem] if isinstance(gem, list) else gem)
    print("openai:", oai)


if __name__ == "__main__":
    main()
