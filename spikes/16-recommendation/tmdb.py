"""feat-016 spike: tiny thread-safe TMDB client (stdlib only). THROWAWAY.

Same auth handling as spikes/08-tmdb (v3 key as query param, v4 token as bearer).
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BASE_URL = "https://api.themoviedb.org/3"
REPO_ROOT = Path(__file__).resolve().parents[2]


def load_key(name: str = "TMDB_API_KEY") -> str:
    if os.environ.get(name):
        return os.environ[name].strip()
    env = REPO_ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            if line.strip().startswith(f"{name}="):
                return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit(f"{name} not set in environment or .env")


class Tmdb:
    def __init__(self) -> None:
        self._key = load_key()
        self._lock = threading.Lock()
        self.calls = 0
        self.status: dict[int, int] = {}

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = dict(params or {})
        headers = {"Accept": "application/json", "User-Agent": "watch-tonight-spike-16/0.1"}
        if len(self._key) <= 40 and not self._key.startswith("eyJ"):
            query["api_key"] = self._key
        else:
            headers["Authorization"] = f"Bearer {self._key}"
        url = f"{BASE_URL}{path}?{urllib.parse.urlencode(query)}"
        for attempt in range(5):
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    self._count(resp.status)
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                self._count(exc.code)
                if exc.code == 429 or exc.code >= 500:
                    time.sleep(float(exc.headers.get("Retry-After", "1.5")) * (attempt + 1))
                    continue
                return {"_http_error": exc.code}
            except (urllib.error.URLError, TimeoutError):
                time.sleep(1.0 * (attempt + 1))
        return {"_http_error": "retries_exhausted"}

    def _count(self, status: int) -> None:
        with self._lock:
            self.calls += 1
            self.status[status] = self.status.get(status, 0) + 1
