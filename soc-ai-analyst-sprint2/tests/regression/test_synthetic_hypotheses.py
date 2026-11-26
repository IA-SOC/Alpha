import pytest

from agent.investigation import LEVELS
from tests.regression.synthetic_cases import EXPECTATIONS


@pytest.mark.parametrize("name", ["us6_attack", "us6_benign", "us6_ambiguous"])
def test_hypothesis_matches_support_and_contradictions(name, synthetic_case_result):
    report = synthetic_case_result(name)["report"]
    expected = EXPECTATIONS[name]
    if not expected["support_ids"]:
        assert report["hypotheses"] == []
        assert report["recommended_actions"] == []
        return
    assert len(report["hypotheses"]) == 1
    hypothesis = report["hypotheses"][0]
    assert {e["alert_id"] for e in hypothesis["evidence_for"]} == set(
        expected["support_ids"]
    )
    assert {e["alert_id"] for e in hypothesis["evidence_against"]} == set(
        expected["against_ids"]
    )
    assert hypothesis["confidence"] == expected["confidence"]
    assert hypothesis["confidence_basis"]
    assert hypothesis["alternatives"] and hypothesis["unknowns"]
    assert hypothesis["rank"] == 1
    assert all(e["role"] == "supporting" for e in hypothesis["evidence_for"])
    assert all(e["role"] == "contradicting" for e in hypothesis["evidence_against"])


def test_approved_activity_reduces_confidence_without_erasing_evidence(
    synthetic_case_result,
):
    attack = synthetic_case_result("us6_attack")["report"]["hypotheses"][0]
    ambiguous = synthetic_case_result("us6_ambiguous")["report"]["hypotheses"][0]
    assert LEVELS.index(ambiguous["confidence"]) < LEVELS.index(attack["confidence"])
    assert ambiguous["evidence_for"] == attack["evidence_for"]
