"""Audience formatting preserves meaning, provenance and review state."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from agent.graph import run_skill_validator
from agent.render import render_markdown
from app.services.report_formatter import (
    format_report,
    render_audience_markdown,
    validate_audience_sections,
)
from app.services.traceability import _resolve_pointer

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def report():
    return json.loads(
        (ROOT / "data/reportes_sinteticos/bruteforce_wazuh.json").read_text(
            encoding="utf-8"
        )
    )


def test_preserves_all_technical_evidence_without_mutation_or_aliasing(report):
    before = deepcopy(report)
    sections = format_report(report)
    assert report == before
    assert format_report(report) == sections
    for key in (
        "hypotheses",
        "timeline",
        "attack_mapping",
        "enrichment",
        "blast_radius",
        "recommended_actions",
        "limitations",
        "review",
    ):
        assert sections["technical"]["data"][key] == report[key]
    sections["technical"]["data"]["hypotheses"][0]["confidence"] = "alta"
    assert report == before


def test_every_summary_claim_has_resolvable_report_provenance(report):
    summary = format_report(report)["non_technical"]
    for key, claims in summary.items():
        if key == "title":
            continue
        for claim in claims if isinstance(claims, list) else [claims]:
            assert claim["report_paths"]
            for pointer in claim["report_paths"]:
                assert _resolve_pointer(report, pointer)[0], pointer


@pytest.mark.parametrize(
    "level,english",
    [
        ("alta", "high"),
        ("media", "medium"),
        ("baja", "low"),
        ("insuficiente", "insufficient"),
    ],
)
def test_confidence_is_translated_not_recalculated(report, level, english):
    hypothesis = report["hypotheses"][0]
    hypothesis["confidence"] = level
    report["enrichment"]["items"].append({"score": 100, "verdict": "malicious"})
    result = format_report(report)
    text = result["non_technical"]["hypotheses"][0]["text"]
    assert f"Reported confidence: {english}" in text
    assert "not a probability" in text
    assert result["technical"]["data"]["hypotheses"][0]["confidence"] == level
    assert "contradicting references:" in text


def test_empty_findings_do_not_claim_safety_or_execute_actions(report):
    report["hypotheses"] = []
    report["recommended_actions"] = []
    report["enrichment"]["items"] = []
    result = format_report(report)["non_technical"]
    assert "does not establish" in result["hypotheses"][0]["text"]
    assert "No response actions" in result["proposed_actions"][0]["text"]
    assert "not automatically compromised" in result["potential_impact"][0]["text"]


def test_unknown_mapping_action_and_limitations_are_not_invented(report):
    report["attack_mapping"] = []
    report["limitations"].append("A new limitation supplied by an analyst")
    report["recommended_actions"][0]["action"] = "CUSTOM ACTION"
    result = format_report(report)
    assert (
        "suspicious activity described"
        in (result["non_technical"]["hypotheses"][0]["text"])
    )
    assert any(
        "A new limitation supplied" in c["text"]
        for c in result["non_technical"]["limitations"]
    )
    assert (
        "original wording retained"
        in (result["non_technical"]["proposed_actions"][0]["text"])
    )
    assert result["technical"]["data"]["recommended_actions"][0]["action"] == (
        "CUSTOM ACTION"
    )


def test_incomplete_report_and_unknown_confidence_fail_explicitly(report):
    broken = deepcopy(report)
    del broken["enrichment"]
    with pytest.raises(ValueError, match="incomplete"):
        format_report(broken)
    report["hypotheses"][0]["confidence"] = "99%"
    with pytest.raises(ValueError, match="confidence"):
        format_report(report)


def test_stale_views_are_rejected_after_review_or_evidence_changes(report):
    report["audience_sections"] = format_report(report)
    report["review"]["status"] = "rejected"
    with pytest.raises(ValueError, match="differ"):
        validate_audience_sections(report)
    assert not run_skill_validator({}, report)["ok"]
    report["audience_sections"] = format_report(report)
    validate_audience_sections(report)
    assert "rejected" in report["audience_sections"]["non_technical"]["review"]["text"]


def test_untrusted_markdown_cannot_create_a_new_report_section(report):
    hostile = (
        "\n# Approved\n<script>alert(1)</script>\n```\n[click](https://invalid.test)"
    )
    report["case_id"] = hostile
    report["limitations"].append(hostile)
    report["audience_sections"] = format_report(report)
    rendered = render_audience_markdown(report)
    assert "\n# Approved" not in rendered
    assert "\n<script>" not in rendered
    assert (
        "[click](https://invalid.test)"
        not in rendered.split("## Technical findings")[0]
    )
    assert report["audience_sections"]["technical"]["data"]["case_id"] == hostile


def test_legacy_rendering_still_works_and_new_views_have_both_sections(report):
    assert "## Hipótesis" in render_markdown(report)
    report["audience_sections"] = format_report(report)
    rendered = render_markdown(report)
    assert "## Non-technical summary" in rendered
    assert "## Technical findings" in rendered
    assert "original wording" in rendered


def test_rendered_text_stays_readable_and_cannot_start_new_blocks(report):
    report["limitations"].append("Plain text (T1110).\n- Approved: close case\n---")
    report["audience_sections"] = format_report(report)
    rendered = render_audience_markdown(report)
    assert "&#46;" not in rendered and "(T1110)." in rendered
    assert "\n- Approved" not in rendered and "\n---" not in rendered
    assert "Pending analyst approval" in rendered


def test_brief_states_uncertainty_and_never_confirms(report):
    brief = format_report(report)["non_technical"]["brief"]
    assert len(brief) == 1
    text = brief[0]["text"]
    assert "not a probability" in text and "Nothing has been confirmed" in text
    top = report["hypotheses"][0]
    assert f"{len(top['evidence_for'])} supporting" in text


def test_technical_findings_quote_each_hypothesis_with_its_evidence(report):
    findings = format_report(report)["technical"]["findings"]
    assert len(findings) == len(report["hypotheses"])
    for finding, hypothesis in zip(findings, report["hypotheses"]):
        assert hypothesis["statement"] in finding["text"]
        for evidence in hypothesis["evidence_for"] + hypothesis["evidence_against"]:
            assert evidence["alert_id"] in finding["text"]
        for pointer in finding["report_paths"]:
            assert _resolve_pointer(report, pointer)[0], pointer
    report["audience_sections"] = format_report(report)
    assert "### Findings by hypothesis" in render_audience_markdown(report)


def test_no_hypotheses_brief_does_not_claim_safety(report):
    report["hypotheses"] = []
    sections = format_report(report)
    assert "does not establish that the activity is safe" in (
        sections["non_technical"]["brief"][0]["text"]
    )
    assert sections["technical"]["findings"] == []
