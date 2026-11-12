"""PR gate: rules that instructions alone can't enforce (ADR 0004).

A PR that changes `tests/acceptance/` or `evals/` fails until the owner reviews those files
and adds the `tests-approved` label. Agents must never change them on their own (AGENTS.md),
because they define what "done" means.

Run by `.github/workflows/pr-gates.yml`. Inputs (environment):
- `BASE_SHA`: the PR's base commit; changed files are `git diff --name-only BASE_SHA HEAD`.
- `LABELS`: the PR's labels, comma-separated.
- `PR_GATES_CHANGED_FILES`: comma-separated file list that replaces the git diff (tests only).
"""

from __future__ import annotations

import os
import subprocess
import sys

PROTECTED = ("tests/acceptance/", "evals/")
APPROVAL_LABEL = "tests-approved"


def changed_files() -> list[str]:
    override = os.environ.get("PR_GATES_CHANGED_FILES")
    if override is not None:
        return [path for path in override.split(",") if path]
    diff = subprocess.run(
        ["git", "diff", "--name-only", os.environ["BASE_SHA"], "HEAD"],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return diff.stdout.split()


def main() -> int:
    labels = {label.strip() for label in os.environ.get("LABELS", "").split(",") if label}
    protected = sorted(path for path in changed_files() if path.startswith(PROTECTED))
    if not protected or APPROVAL_LABEL in labels:
        print("PR gates passed.")
        return 0
    print(
        "Protected paths changed:\n"
        + "".join(f"  - {path}\n" for path in protected)
        + "Why: acceptance tests and evals define 'done'; only the owner may change them.\n"
        + f"Fix: the owner reviews these files and adds the `{APPROVAL_LABEL}` label to the PR."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
