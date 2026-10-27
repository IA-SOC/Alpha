import asyncio
import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

import agent.graph
from agent.follow_up import run_follow_up
from agent.graph import investigate, run_skill_validator
from agent.investigation import LEVELS

ROOT = Path(__file__).resolve().parent.parent
CASE_PATH = ROOT / "data" / "synthetic" / "pre_ransomware.json"
CASE = json.loads(CASE_PATH.read_text(encoding="utf-8"))


def test_mark_legitimate_revises_hypothesis_without_mutating_previous_report():
    baseline = asyncio.run(investigate(deepcopy(CASE), "follow-up-baseline"))
    previous_report = deepcopy(baseline["report"])
    previous_copy = deepcopy(previous_report)
    hypothesis_before = previous_report["hypotheses"][0]
    alert_id = hypothesis_before["evidence_for"][0]["alert_id"]

    revised = asyncio.run(
        run_follow_up(
            CASE,
            previous_report,
            {"type": "mark_legitimate", "alert_ids": [alert_id], "analyst": "l2"},
            "follow-up",
        )
    )
    technique_id = re.search(
        r"T\d{4}(?:\.\d{3})?", hypothesis_before["statement"]
    ).group(0)
    hypothesis_after = next(
        item
        for item in revised["report"]["hypotheses"]
        if technique_id in item["statement"]
    )
    change = next(
        item
        for item in revised["report"]["follow_up"]["changes"]
        if item["technique_id"] == technique_id
    )

    assert alert_id not in {
        item["alert_id"] for item in hypothesis_after["evidence_for"]
    }
    assert alert_id in {
        item["alert_id"] for item in hypothesis_after["evidence_against"]
    }
    assert LEVELS.index(hypothesis_after["confidence"]) <= LEVELS.index(
        hypothesis_before["confidence"]
    )
    assert change["change"] == "changed"
    assert revised["validation"]["ok"], revised["validation"]["output"]
    assert previous_report == previous_copy
    assert "## Analyst follow-up" in revised["report_markdown"]


@pytest.mark.parametrize(
    "instruction",
    [
        {"type": "mark_legitimate", "alert_ids": [], "analyst": "l2"},
        {"type": "wrong", "alert_ids": ["rw-1"], "analyst": "l2"},
        {"type": "mark_legitimate", "alert_ids": ["unknown"], "analyst": "l2"},
    ],
)
def test_invalid_instruction_fails_before_a_graph_runs(monkeypatch, instruction):
    def should_not_run():
        raise AssertionError("the graph must not run")

    monkeypatch.setattr(agent.graph, "build_graph", should_not_run)
    with pytest.raises(ValueError):
        asyncio.run(run_follow_up(CASE, {}, instruction, "invalid"))


def test_regular_investigation_has_no_follow_up():
    state = asyncio.run(investigate(deepcopy(CASE), "follow-up-regular"))
    assert "follow_up" not in state["report"]
    assert run_skill_validator(CASE, state["report"])["ok"]


def test_marking_all_support_keeps_report_valid_and_unrelated_hypotheses_intact():
    base = asyncio.run(investigate(deepcopy(CASE), "scope-base"))["report"]
    top = base["hypotheses"][0]
    marked = [e["alert_id"] for e in top["evidence_for"]]
    state = asyncio.run(
        run_follow_up(
            CASE,
            base,
            {"type": "mark_legitimate", "alert_ids": marked, "analyst": "ana"},
            "scope",
        )
    )
    assert state["validation"]["ok"], state["validation"]["output"]
    changed = {
        c["technique_id"]
        for c in state["report"]["follow_up"]["changes"]
        if c["change"] != "unchanged"
    }
    for hypothesis in base["hypotheses"]:
        evidence = {e["alert_id"] for e in hypothesis["evidence_for"]}
        technique = re.search(r"T\d{4}(?:\.\d{3})?", hypothesis["statement"])[0]
        if not evidence & set(marked):
            assert technique not in changed, technique
