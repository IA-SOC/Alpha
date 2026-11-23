"""#210 / HY-08: benign counter-evidence needs pairwise temporal relevance."""

from copy import deepcopy

import pytest

from agent.investigation import build_attack_analysis, correlated_attack_analysis
from agent.normalize import normalize_case
from app.services.agent_adapter import correlate_direct
from core.logic import map_alerts_to_mitre
from tests.helpers import investigate, tagged
from tests.test_hypotheses import direct_report


def alert(aid, time, *, host="web-01", tags=None):
    return {
        "id": aid,
        "timestamp": time,
        "host": host,
        "user": "analyst",
        "rule_name": "failed login" if aid.startswith("attack") else "job",
        "tags": tags or [],
    }


@pytest.mark.parametrize(
    "time,host,expected",
    [
        ("2026-10-09T12:00:00Z", "web-01", True),
        ("2026-10-09T11:55:00Z", "web-01", True),
        ("2026-10-09T12:05:00Z", "web-01", True),
        ("2026-10-09T12:05:01Z", "web-01", False),
        ("2026-10-09T11:54:59Z", "web-01", False),
        ("2026-10-02T12:00:00Z", "web-01", False),
        ("2026-10-09T07:05:00-05:00", "web-01", True),
        ("2026-10-09T12:00:00Z", "db-01", False),
        (None, "web-01", False),
        ("not-a-time", "web-01", False),
        ("2026-10-09T12:00:00", "web-01", False),
    ],
)
def test_benign_evidence_requires_same_host_and_reliable_close_time(
    time, host, expected
):
    raw = [
        alert("attack-1", "2026-10-09T12:00:00Z"),
        alert("backup", time, host=host, tags=["backup"]),
    ]
    original = deepcopy(raw)
    alerts, _ = normalize_case({"alerts": raw})
    [hypothesis] = build_attack_analysis(
        alerts, map_alerts_to_mitre(alerts), synthetic=False
    )["hypotheses"]
    assert [e["alert_id"] for e in hypothesis["evidence_against"]] == (
        ["backup"] if expected else []
    )
    assert hypothesis["confidence"] == ("insuficiente" if expected else "baja")
    if expected:
        assert hypothesis["evidence_against"][0]["source_fields"]
    assert raw == original


@pytest.mark.parametrize(
    "support_time,host",
    [(None, "web-01"), ("2026-10-09T12:00:00", "web-01"),
     ("not-a-time", "web-01"), ("2026-10-09T12:00:00Z", None)],
)
def test_missing_support_time_or_host_cannot_establish_counter_evidence(
    support_time, host
):
    alerts, _ = normalize_case({"alerts": [
        alert("attack-1", support_time, host=host),
        alert("backup", "2026-10-09T12:00:00Z", host=host, tags=["backup"]),
    ]})
    [hypothesis] = build_attack_analysis(
        alerts, map_alerts_to_mitre(alerts), synthetic=False
    )["hypotheses"]
    assert hypothesis["evidence_against"] == []


@pytest.mark.parametrize("window,expected", [(60, []), (300, ["backup"])])
def test_transitive_group_uses_configured_window_against_support(window, expected):
    case = {"alerts": [
        alert("attack-1", "2026-10-09T12:00:00Z"),
        alert("bridge", "2026-10-09T12:00:50Z"),
        alert("backup", "2026-10-09T12:01:40Z", tags=["backup"]),
    ]}
    alerts, _ = normalize_case(case)
    correlation = correlate_direct(case, alerts, window_seconds=window)
    assert correlation["related_groups"] == [["attack-1", "backup", "bridge"]]
    [hypothesis] = correlated_attack_analysis(
        alerts, map_alerts_to_mitre(alerts), False, {"correlation": correlation}
    )["hypotheses"]
    assert [e["alert_id"] for e in hypothesis["evidence_against"]] == expected


def transitive_alerts():
    return [
        tagged("attack-1", ["brute_force"], time="2026-10-09T12:00:00Z"),
        tagged("attack-2", ["failed_login"], time="2026-10-09T12:00:30Z"),
        tagged("bridge", [], time="2026-10-09T12:04:30Z"),
        tagged("backup", ["backup"], time="2026-10-09T12:09:00Z"),
    ]


def assert_transitive_report(report):
    assert report["correlation"]["related_groups"] == [
        ["attack-1", "attack-2", "backup", "bridge"]
    ]
    [hypothesis] = report["hypotheses"]
    assert {e["alert_id"] for e in hypothesis["evidence_for"]} == {
        "attack-1", "attack-2"
    }
    assert hypothesis["confidence"] == "media"
    assert hypothesis["evidence_against"] == []
    assert report["input"]["processed_alert_count"] == 4
    assert report["review"]["status"] == "pending"


def test_api_distant_backup_in_transitive_group_preserves_confidence(client):
    result = investigate(client, *transitive_alerts())
    assert result["status"] == "pending_review"
    assert result["validation"]["ok"]
    assert result["validation"]["traceability_ok"]
    assert_transitive_report(result["report"])


def test_direct_agent_distant_backup_in_transitive_group_preserves_confidence():
    report = direct_report({
        "case_id": "HY08-TRANSITIVE",
        "alerts": [a["raw_alert"] for a in transitive_alerts()],
    })
    assert_transitive_report(report)


def test_analyst_legitimate_mark_remains_explicit_counter_evidence():
    alerts, _ = normalize_case({"alerts": [
        alert("attack-1", None, tags=["analyst_legitimate"]),
    ]})
    [hypothesis] = build_attack_analysis(
        alerts, map_alerts_to_mitre(alerts), synthetic=False
    )["hypotheses"]
    assert hypothesis["confidence"] == "insuficiente"
    assert hypothesis["evidence_for"] == []
    assert [e["alert_id"] for e in hypothesis["evidence_against"]] == ["attack-1"]
