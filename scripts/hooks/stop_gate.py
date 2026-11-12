"""Stop hook: the agent may stop only when `uv run poe check` passes.

Shared by both tools (ADR 0003); the stdin payload tells them apart:
- Antigravity (`.agents/hooks.json`) sends `terminationReason` and expects
  `{"decision": "continue", "reason": ...}` to keep the agent working.
- Claude Code (`.claude/settings.json`) sends `hook_event_name: "Stop"` and expects
  `{"decision": "block", "reason": ...}`; no output lets it stop.

Runs the check only on normal turn completion (Antigravity: `terminationReason ==
"NO_TOOL_CALL"`) when watched code/test directories have uncommitted or branch changes,
so Q&A sessions and user cancellations are never blocked. After MAX_ATTEMPTS consecutive
failures it lets the agent stop and hand control back to the owner.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

MAX_ATTEMPTS = 3
REPO_ROOT = Path(__file__).resolve().parents[2]
COUNTER = REPO_ROOT / ".harness" / "stop_gate_attempts"
WATCHED = ("src", "web", "tests", "scripts", "pyproject.toml")


def find_uv() -> str:
    """Locate the `uv` binary even when GUI/hook shells lack Homebrew or user PATH."""
    found = shutil.which("uv")
    if found:
        return found
    home = Path.home()
    candidates = [
        Path("/opt/homebrew/bin/uv"),
        Path("/usr/local/bin/uv"),
        home / ".local" / "bin" / "uv",
        home / ".cargo" / "bin" / "uv",
        home / ".local" / "bin" / "uv.exe",
        home / ".cargo" / "bin" / "uv.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return "uv"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run `cmd` and decode its output as UTF-8.

    Without an explicit encoding Windows decodes with the ANSI code page (cp1252), which
    crashes on the UTF-8 that git and import-linter print.
    """
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def git(*args: str) -> str:
    return run(["git", *args]).stdout


def has_code_changes() -> bool:
    untracked_or_unstaged = git("status", "--porcelain", "--", *WATCHED)
    if untracked_or_unstaged.strip():
        return True
    committed_on_branch = git("diff", "--name-only", "origin/main", "--", *WATCHED)
    return bool(committed_on_branch.strip())


def respond(allow: bool, reason: str = "", *, claude: bool = False) -> None:
    if claude:
        if not allow:
            print(json.dumps({"decision": "block", "reason": reason}))
        return
    if allow:
        print(json.dumps({"decision": "allow"}))
    else:
        print(json.dumps({"decision": "continue", "reason": reason}))


def read_payload() -> dict[str, Any]:
    # Decode as UTF-8 ourselves: on Windows `sys.stdin` uses the ANSI code page (cp1252) unless
    # PYTHONIOENCODING/PYTHONUTF8 happen to be set, and the payload is UTF-8 (Claude Code's
    # includes the last assistant message). "utf-8-sig" also drops the BOM that Windows
    # PowerShell 5.1 adds when it pipes text.
    raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace").strip()
    if not raw:
        return {}
    try:
        data: Any = json.loads(raw)
        if isinstance(data, dict):
            return {str(k): v for k, v in data.items()}  # type: ignore[misc]
        return {}
    except json.JSONDecodeError:
        return {}


def main() -> None:
    os.chdir(REPO_ROOT)
    payload = read_payload()
    claude = payload.get("hook_event_name") == "Stop"

    termination_reason = payload.get("terminationReason", "NO_TOOL_CALL")
    if termination_reason != "NO_TOOL_CALL":
        respond(allow=True, claude=claude)
        return

    if not has_code_changes():
        respond(allow=True, claude=claude)
        return

    uv_bin = find_uv()
    check_cmd = os.environ.get("STOP_GATE_CMD")
    cmd = check_cmd.split() if check_cmd else [uv_bin, "run", "--no-sync", "poe", "check"]

    result = run(cmd)
    if result.returncode == 0:
        COUNTER.unlink(missing_ok=True)
        respond(allow=True, claude=claude)
        return

    attempts = int(COUNTER.read_text().strip()) + 1 if COUNTER.exists() else 1
    if attempts > MAX_ATTEMPTS:
        COUNTER.unlink(missing_ok=True)
        respond(allow=True, claude=claude)
        return

    COUNTER.parent.mkdir(parents=True, exist_ok=True)
    COUNTER.write_text(str(attempts))

    tail = (result.stdout + result.stderr)[-3000:]
    respond(
        allow=False,
        reason=(
            f"`uv run poe check` failed (attempt {attempts}/{MAX_ATTEMPTS}). "
            f"Fix it before stopping.\n{tail}"
        ),
        claude=claude,
    )


if __name__ == "__main__":
    main()
