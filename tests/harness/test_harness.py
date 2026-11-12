"""Automated sensors for the agentic harness itself (L04, L08, L09).

Verifies:
1. `AGENTS.md` stays concise (<= 150 lines).
2. `feature_list.json` obeys structural invariants (at most 1 `in_progress`, valid types/statuses,
   `done` requires non-empty `evidence`, valid dependency references).
3. Required harness files (skills, reviewer, hooks, state docs) exist.
4. `stop_gate.py` blocks when checks fail and allows after `MAX_ATTEMPTS` or when checks pass.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

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
    ]
    for rel_path in required:
        assert (REPO_ROOT / rel_path).is_file(), f"Missing harness file: {rel_path}"


def test_stop_gate_blocks_on_failure_and_allows_on_success() -> None:
    script = REPO_ROOT / "scripts" / "hooks" / "stop_gate.py"
    counter = REPO_ROOT / ".harness" / "stop_gate_attempts"
    counter.unlink(missing_ok=True)

    try:
        # 1. Simulate a failing check command -> should return decision: "continue"
        env_fail = {**os.environ, "STOP_GATE_CMD": f"{sys.executable} -c import_error_xyz"}
        res_fail = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps({"terminationReason": "NO_TOOL_CALL"}),
            capture_output=True,
            text=True,
            env=env_fail,
            check=True,
        )
        out_fail: dict[str, str] = json.loads(res_fail.stdout.strip())
        assert out_fail["decision"] == "continue"
        assert "attempt 1/3" in out_fail["reason"]
        assert counter.is_file() and counter.read_text().strip() == "1"

        # 2. Simulate a passing check command -> should return decision: "allow" & clear counter
        env_pass = {**os.environ, "STOP_GATE_CMD": f"{sys.executable} -V"}
        res_pass = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps({"terminationReason": "NO_TOOL_CALL"}),
            capture_output=True,
            text=True,
            env=env_pass,
            check=True,
        )
        out_pass: dict[str, str] = json.loads(res_pass.stdout.strip())
        assert out_pass["decision"] == "allow"
        assert not counter.exists()
    finally:
        counter.unlink(missing_ok=True)
