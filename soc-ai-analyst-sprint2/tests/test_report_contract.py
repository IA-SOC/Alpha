"""Sprint 4 #84/#87: confidence and versioned report boundary regressions."""

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agent.graph import run_skill_validator
from agent.investigation import ordinal_confidence
from core.report_contract import SCHEMA, SCHEMA_ID, serialize_report, validate_report

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = (
    "timeline",
    "attack_mapping",
    "hypotheses",
    "blast_radius",
    "recommended_actions",
    "enrichment",
    "review",
    "input",
    "limitations",
)


@pytest.fixture
def report():
    return json.loads(
        (ROOT / "data/reportes_sinteticos/bruteforce_wazuh.json").read_text(
            encoding="utf-8"
        )
    )


def test_schema_is_valid():
    Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize("level", ["insuficiente", "baja", "media", "alta"])
def test_all_ordinal_levels_round_trip_with_evidence_and_basis(report, level):
    report["hypotheses"][0]["confidence"] = level
    before = deepcopy(report)
    assert json.loads(serialize_report(report)) == before
    assert report == before


@pytest.mark.parametrize("value", [0.99, 99, "99%", "0.99", None, True, [], {}])
def test_unsupported_confidence_is_rejected(report, value):
    report["hypotheses"][0]["confidence"] = value
    with pytest.raises(ValueError, match="confidence"):
        serialize_report(report)
    assert not run_skill_validator({}, report)["ok"]


@pytest.mark.parametrize(
    "key",
    [
        "confidence_percentage",
        "confidence_percent",
        "confidence_score",
        "confidence_probability",
        "probability",
    ],
)
def test_percentage_side_channels_are_rejected(report, key):
    report["hypotheses"][0][key] = 99
    with pytest.raises(ValueError):
        validate_report(report)


@pytest.mark.parametrize("basis", [None, "", "   ", 99])
def test_confidence_requires_justification(report, basis):
    report["hypotheses"][0]["confidence_basis"] = basis
    with pytest.raises(ValueError, match="confidence_basis"):
        validate_report(report)


@pytest.mark.parametrize("level", ["baja", "media", "alta"])
def test_contradiction_alone_cannot_support_confidence(report, level):
    hypothesis = report["hypotheses"][0]
    evidence = deepcopy(hypothesis["evidence_for"][0])
    evidence["role"] = "contradicting"
    hypothesis.update(confidence=level, evidence_for=[], evidence_against=[evidence])
    with pytest.raises(ValueError, match="evidence_for"):
        validate_report(report)
    hypothesis["confidence"] = "insuficiente"
    validate_report(report)


@pytest.mark.parametrize("role", ["context", "contradicting"])
def test_support_must_have_supporting_role(report, role):
    report["hypotheses"][0]["evidence_for"][0]["role"] = role
    with pytest.raises(ValueError, match="role"):
        validate_report(report)


def test_insufficient_still_requires_evidence(report):
    report["hypotheses"][0].update(
        confidence="insuficiente", evidence_for=[], evidence_against=[]
    )
    with pytest.raises(ValueError):
        validate_report(report)


@pytest.mark.parametrize("section", SECTIONS)
def test_required_sections_cannot_be_missing(report, section):
    del report[section]
    with pytest.raises(ValueError, match=section):
        serialize_report(report)


@pytest.mark.parametrize("section", SECTIONS)
def test_required_sections_cannot_be_null(report, section):
    report[section] = None
    with pytest.raises(ValueError, match=section):
        validate_report(report)


@pytest.mark.parametrize(
    "section,key",
    [
        ("timeline", "description"),
        ("attack_mapping", "technique_name"),
        ("hypotheses", "unknowns"),
        ("recommended_actions", "rationale"),
    ],
)
def test_section_entries_require_their_fields(report, section, key):
    del report[section][0][key]
    with pytest.raises(ValueError, match=key):
        validate_report(report)


def test_declared_schema_version_is_checked_and_legacy_reports_remain_readable(report):
    report.pop("methodology", None)
    validate_report(report)
    report["methodology"] = {"report_schema": SCHEMA_ID}
    validate_report(report)
    report["methodology"]["report_schema"] = "urn:soc-investigation-report:schema:99"
    with pytest.raises(ValueError, match="report_schema"):
        serialize_report(report)


def test_unknown_extensions_and_original_values_survive_serialization(report):
    report["customer_extension"] = {"text": "investigación", "values": [None, 1, True]}
    assert json.loads(serialize_report(report)) == report
    report["customer_extension"]["score"] = float("nan")
    with pytest.raises(ValueError):
        serialize_report(report)


@pytest.mark.parametrize(
    "name", [
        "benign_noise", "bruteforce_wazuh", "exfiltration", "phishing_ecs",
        "pre_ransomware", "sample_case_bruteforce",
    ]
)
def test_existing_synthetic_reports_remain_compatible(name):
    path = ROOT / f"data/reportes_sinteticos/{name}.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    assert json.loads(serialize_report(report)) == report


def test_outdated_holdout_report_is_rejected_without_inventing_action_approvals():
    # This stored artifact predates the existing action approval/rank contract.
    path = ROOT / "data/reportes_sinteticos/holdout_kerberoast.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="approval_status"):
        serialize_report(report)


def test_standalone_validator_rejects_malformed_section_without_traceback(
    report, tmp_path
):
    report["enrichment"] = []
    case_path, report_path = tmp_path / "case.json", tmp_path / "report.json"
    case_path.write_text("{}", encoding="utf-8")
    report_path.write_text(json.dumps(report), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "skills/soc-case-investigator/scripts/validate_report.py"),
            "--case",
            str(case_path),
            "--report",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 1
    assert "enrichment" in proc.stdout
    assert "Traceback" not in proc.stderr


@pytest.mark.parametrize(
    "count,synthetic,against,bad_time,expected",
    [
        (0, False, False, False, "insuficiente"),
        (1, False, False, False, "baja"),
        (2, False, False, False, "media"),
        (3, False, False, False, "alta"),
        (3, True, False, False, "media"),
        (2, False, True, False, "baja"),
        (1, False, False, True, "insuficiente"),
    ],
)
def test_existing_confidence_rubric_and_caps(
    count, synthetic, against, bad_time, expected
):
    support = [
        {"rule_name": f"rule-{i}", "timestamp_problem": bad_time} for i in range(count)
    ]
    result = ordinal_confidence(support, [{}] if against else [], synthetic)
    assert result["confidence"] == expected
    assert result["confidence_basis"].strip()
