#!/usr/bin/env bash
# Startup and verification entrypoint (feat-014): same steps as the Startup Workflow in AGENTS.md.
# Runs on macOS, Linux and Git Bash on Windows. `uv run poe check` stays the main command;
# in PowerShell run the two commands below by hand.
set -euo pipefail
cd "$(dirname "$0")"
uv sync
uv run poe check
