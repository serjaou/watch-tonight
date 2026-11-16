"""Tiny .env reader for the feat-011 spike scripts (stdlib only, no python-dotenv).

Reads `.env` at the repo root with `utf-8-sig` so a BOM written by Windows
PowerShell (`Out-File`) does not end up glued to the first key name, and strips
`\\r` so CRLF line endings from Windows editors are harmless.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_env(path: Path = REPO_ROOT / ".env") -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def require(name: str) -> str:
    value = os.environ.get(name) or load_env().get(name)
    if not value:
        raise SystemExit(f"{name} is not set in the environment or .env")
    return value
