"""Automated sensors for the agentic harness itself (L04, L08, L09).

Verifies:
1. `AGENTS.md` stays concise (<= 150 lines).
2. `feature_list.json` obeys structural invariants (at most 1 `in_progress`, valid types/statuses,
   `done` requires non-empty `evidence`, valid dependency references).
3. Required harness files (skills, reviewer, hooks, state docs) exist, every `.agents` skill has
   a `.claude` stub, and both tools wire the Stop hook to `stop_gate.py` (ADR 0003).
4. `stop_gate.py` allows stopping when no code changed, blocks while checks fail, and gives up
   after `MAX_ATTEMPTS`, in both tools' reply formats. It runs in a throwaway git repo so the
   result never depends on this repo's git state (a clean checkout in CI must behave like a
   dirty laptop).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VALID_TYPES = {"feature", "spike", "chore"}
VALID_STATUSES = {"todo", "in_progress", "blocked", "done"}


class FeatureItem(TypedDict):
    id: str
    type: str
    name: str
    stories: list[str]
    status: str
    dependencies: list[str]
    spec: str | None
    evidence: str


class FeatureListDoc(TypedDict):
    features: list[FeatureItem]


def test_agents_md_line_limit() -> None:
    agents_md = REPO_ROOT / "AGENTS.md"
    assert agents_md.is_file(), "AGENTS.md must exist at repository root"
    lines = agents_md.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 150, f"AGENTS.md has {len(lines)} lines (limit is 150)"


def test_feature_list_invariants() -> None:
    path = REPO_ROOT / "feature_list.json"
    data: FeatureListDoc = json.loads(path.read_text(encoding="utf-8"))
    features = data["features"]
    assert len(features) > 0

    ids: set[str] = set()
    in_progress_count = 0

    for item in features:
        feat_id = item["id"]
        assert feat_id not in ids, f"Duplicate feature id: {feat_id}"
        ids.add(feat_id)

        assert item["type"] in VALID_TYPES, f"{feat_id} has invalid type {item['type']}"
        assert item["status"] in VALID_STATUSES, f"{feat_id} has invalid status {item['status']}"

        if item["status"] == "in_progress":
            in_progress_count += 1
        if item["status"] == "done":
            assert item["evidence"].strip(), f"{feat_id} is 'done' without evidence"
        if item["type"] in {"feature", "spike"}:
            assert item["spec"], f"{feat_id} ({item['type']}) must reference a spec/spike path"

    assert in_progress_count <= 1, (
        f"At most 1 feature may be in_progress (found {in_progress_count})"
    )

    for item in features:
        for dep in item["dependencies"]:
            assert dep in ids, f"{item['id']} depends on unknown id {dep}"


def test_required_harness_files_exist() -> None:
    required = [
        "AGENTS.md",
        "PROGRESS.md",
        "LEARNING.md",
        "feature_list.json",
        "docs/product.md",
        "docs/workflow.md",
        "docs/harness-log.md",
        ".agents/hooks.json",
        ".agents/agents/reviewer.md",
        ".agents/skills/start/SKILL.md",
        ".agents/skills/handoff/SKILL.md",
        ".agents/skills/spec/SKILL.md",
        ".agents/skills/review/SKILL.md",
        ".agents/skills/tutor/SKILL.md",
        ".agents/skills/defend/SKILL.md",
        "scripts/hooks/stop_gate.py",
        "CLAUDE.md",
        "docs/conventions.md",
        ".claude/settings.json",
        ".claude/agents/reviewer.md",
        ".github/workflows/pr-gates.yml",
        "scripts/ci/pr_gates.py",
    ]
    for rel_path in required:
        assert (REPO_ROOT / rel_path).is_file(), f"Missing harness file: {rel_path}"


def test_every_skill_has_a_claude_code_stub() -> None:
    """`.agents/` is the single source (ADR 0003); `.claude/` stubs must point at it."""
    agents_skills = {p.parent.name for p in (REPO_ROOT / ".agents" / "skills").glob("*/SKILL.md")}
    claude_skills = {p.parent.name for p in (REPO_ROOT / ".claude" / "skills").glob("*/SKILL.md")}
    assert agents_skills == claude_skills, (
        f"Skills without a .claude stub: {sorted(agents_skills - claude_skills)}; "
        f"stubs without a source skill: {sorted(claude_skills - agents_skills)}"
    )
    for name in agents_skills:
        stub = (REPO_ROOT / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert f".agents/skills/{name}/SKILL.md" in stub, f".claude stub for {name} must load it"

    reviewer_stub = (REPO_ROOT / ".claude" / "agents" / "reviewer.md").read_text(encoding="utf-8")
    assert ".agents/agents/reviewer.md" in reviewer_stub


def test_both_tools_wire_the_stop_gate() -> None:
    for config in (".agents/hooks.json", ".claude/settings.json"):
        text = (REPO_ROOT / config).read_text(encoding="utf-8")
        assert "scripts/hooks/stop_gate.py" in text, f"{config} must run stop_gate.py on Stop"


FAILING_CHECK = f"{sys.executable} -c import_error_xyz"
PASSING_CHECK = f"{sys.executable} -V"
ANTIGRAVITY_STOP = {"terminationReason": "NO_TOOL_CALL"}
CLAUDE_STOP = {"hook_event_name": "Stop", "stop_hook_active": False}


@pytest.fixture
def gate_repo(tmp_path: Path) -> Path:
    """A throwaway git repo holding a copy of `stop_gate.py` and no code changes."""
    hooks_dir = tmp_path / "scripts" / "hooks"
    hooks_dir.mkdir(parents=True)
    shutil.copy(REPO_ROOT / "scripts" / "hooks" / "stop_gate.py", hooks_dir)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    # Hide the copied script itself, otherwise it counts as an untracked change in `scripts/`.
    (tmp_path / ".git" / "info" / "exclude").write_text("scripts/hooks/stop_gate.py\n")
    return tmp_path


def run_stop_gate(
    repo: Path,
    check_cmd: str,
    payload: Mapping[str, object] = ANTIGRAVITY_STOP,
    *,
    bom: bool = False,
) -> dict[str, str]:
    """Run the gate copy; returns its JSON reply, or `{}` when it prints nothing."""
    result = subprocess.run(
        [sys.executable, str(repo / "scripts" / "hooks" / "stop_gate.py")],
        input=("﻿" if bom else "") + json.dumps(payload),
        encoding="utf-8",
        capture_output=True,
        text=True,
        env={**os.environ, "STOP_GATE_CMD": check_cmd},
        check=True,
    )
    out = result.stdout.strip()
    return json.loads(out) if out else {}


def add_code_change(repo: Path) -> None:
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("x = 1\n")


def test_stop_gate_allows_stop_without_checking_when_no_code_changed(gate_repo: Path) -> None:
    assert run_stop_gate(gate_repo, FAILING_CHECK)["decision"] == "allow"
    assert not (gate_repo / ".harness" / "stop_gate_attempts").exists()


def test_stop_gate_blocks_until_check_passes(gate_repo: Path) -> None:
    add_code_change(gate_repo)
    counter = gate_repo / ".harness" / "stop_gate_attempts"

    blocked = run_stop_gate(gate_repo, FAILING_CHECK)
    assert blocked["decision"] == "continue"
    assert "attempt 1/3" in blocked["reason"]
    assert counter.read_text().strip() == "1"

    assert run_stop_gate(gate_repo, PASSING_CHECK)["decision"] == "allow"
    assert not counter.exists()


def test_stop_gate_gives_up_after_max_attempts(gate_repo: Path) -> None:
    add_code_change(gate_repo)
    counter = gate_repo / ".harness" / "stop_gate_attempts"
    counter.parent.mkdir()
    counter.write_text("3")

    assert run_stop_gate(gate_repo, FAILING_CHECK)["decision"] == "allow"
    assert not counter.exists()


def test_stop_gate_speaks_claude_code_format(gate_repo: Path) -> None:
    """Claude Code blocks with `decision: block`; an empty reply lets it stop."""
    assert run_stop_gate(gate_repo, FAILING_CHECK, CLAUDE_STOP) == {}

    add_code_change(gate_repo)
    blocked = run_stop_gate(gate_repo, FAILING_CHECK, CLAUDE_STOP)
    assert blocked["decision"] == "block"
    assert "attempt 1/3" in blocked["reason"]

    assert run_stop_gate(gate_repo, PASSING_CHECK, CLAUDE_STOP) == {}


def test_stop_gate_reads_payload_with_bom(gate_repo: Path) -> None:
    """Windows PowerShell 5.1 prefixes piped text with a BOM; the gate must still parse it."""
    assert run_stop_gate(gate_repo, FAILING_CHECK, CLAUDE_STOP, bom=True) == {}


def test_stop_gate_blocks_when_failing_check_prints_non_ascii(gate_repo: Path) -> None:
    """import-linter prints UTF-8 box art; on Windows the default codec (cp1252) can't decode it."""
    add_code_change(gate_repo)
    noisy_check = gate_repo / "noisy_failing_check.py"
    noisy_check.write_text(
        "import sys\nsys.stdout.buffer.write('╔══╗ BROKEN'.encode())\nsys.exit(1)\n",
        encoding="utf-8",
    )
    blocked = run_stop_gate(gate_repo, f"{sys.executable} {noisy_check}")
    assert blocked["decision"] == "continue"
    assert "BROKEN" in blocked["reason"]


@pytest.mark.parametrize(
    ("changed", "labels", "passes"),
    [
        ("src/watch_tonight/domain/x.py,tests/unit/test_x.py", "", True),
        ("tests/acceptance/test_dry_run.py", "", False),
        ("evals/queries.yaml", "documentation", False),
        ("tests/acceptance/test_dry_run.py,evals/queries.yaml", "tests-approved", True),
        ("tests/acceptance_helpers.py", "", True),
    ],
)
def test_pr_gate_protects_acceptance_tests_and_evals(
    changed: str, labels: str, passes: bool
) -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "ci" / "pr_gates.py")],
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PR_GATES_CHANGED_FILES": changed, "LABELS": labels},
        check=False,
    )
    assert (result.returncode == 0) == passes, result.stdout
    if not passes:
        assert "tests-approved" in result.stdout
