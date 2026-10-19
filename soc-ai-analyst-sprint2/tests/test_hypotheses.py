"""S3-US6-T05 (#41): hypothesis evidence, alternatives, unknowns and sequences.

Criteria used here until #37 lands, taken from the skill protocol
(references/protocolo.md, phase 2 and "Rúbrica ordinal de confianza"):

- every hypothesis cites the alerts that support it and keeps the evidence
  against it, benign alternatives and open questions;
- confidence is an ordinal label with its basis, and legitimate activity
  lowers it;
- no hypothesis is raised without mapped evidence;
- a hypothesis stays inside one correlation group, and no attack sequence is
  asserted across groups that are not related.

Checks that need #38 are strict xfails, so they fail loudly once it is fixed.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from agent.graph import build_graph
from agent.investigation import LEVELS
from app.main import create_app
from tests.helpers import investigate, tagged

SEQUENCE_MARKERS = ("→", "Secuencia de ataque sugerida")


def unrelated_techniques():
    return [
        tagged(
            "phish",
            ["phishing"],
            ip="198.51.100.10",
            host="mail-01",
            user="alice",
            time="2026-10-09T08:00:00Z",
        ),
        tagged(
            "guess",
            ["brute_force"],
            ip="198.51.100.20",
            host="web-01",
            user="bob",
            time="2026-10-09T10:00:00Z",
        ),
        tagged(
            "share",
            ["smb_admin_share"],
            ip="198.51.100.30",
            host="db-01",
            user="carol",
            time="2026-10-09T12:00:00Z",
        ),
    ]


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    path = tmp_path_factory.mktemp("hypotheses") / "cases.sqlite3"
    with TestClient(create_app(database_path=path)) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def attack_only(client):
    return investigate(
        client,
        tagged("fail-1", ["brute_force"]),
        tagged("fail-2", ["failed_login"]),
    )


@pytest.fixture(scope="module")
def attack_with_backup(client):
    return investigate(
        client,
        tagged("fail-1", ["brute_force"]),
        tagged("fail-2", ["failed_login"]),
        tagged("nightly", ["backup"]),
    )


def test_every_hypothesis_is_complete(attack_with_backup):
    report = attack_with_backup["report"]
    alert_ids = {"fail-1", "fail-2", "nightly"}
    assert report["hypotheses"]
    for rank, hypothesis in enumerate(report["hypotheses"], start=1):
        assert hypothesis["rank"] == rank
        assert hypothesis["evidence_for"]
        assert {e["alert_id"] for e in hypothesis["evidence_for"]} <= alert_ids
        assert hypothesis["alternatives"]
        assert hypothesis["unknowns"]
        assert hypothesis["confidence"] in LEVELS
        assert hypothesis["confidence_basis"]


def test_legitimate_activity_is_kept_as_evidence_against(
    attack_only, attack_with_backup
):
    plain = attack_only["report"]["hypotheses"][0]
    mixed = attack_with_backup["report"]["hypotheses"][0]
    assert plain["evidence_against"] == []
    assert [e["alert_id"] for e in mixed["evidence_against"]] == ["nightly"]
    assert all(e["role"] == "contradicting" for e in mixed["evidence_against"])
    assert LEVELS.index(mixed["confidence"]) < LEVELS.index(plain["confidence"])
    assert "a la baja" in mixed["confidence_basis"]


def test_no_hypothesis_without_mapped_evidence(client):
    result = investigate(
        client,
        tagged("job-1", ["backup"]),
        tagged("job-2", ["scheduled_task"]),
    )
    assert result["report"]["hypotheses"] == []
    assert result["report"]["recommended_actions"] == []


def test_hypotheses_stay_inside_their_correlation_group(client):
    result = investigate(client, *unrelated_techniques())
    hypotheses = result["report"]["hypotheses"]
    assert len(hypotheses) == 3
    for hypothesis in hypotheses:
        group = set(hypothesis["correlation_group_alert_ids"])
        assert {e["alert_id"] for e in hypothesis["evidence_for"]} <= group


def test_api_summary_asserts_no_sequence_across_unrelated_groups(client):
    summary = investigate(client, *unrelated_techniques())["report"][
        "executive_summary"
    ]
    assert not any(marker in summary for marker in SEQUENCE_MARKERS)


def direct_agent_summary():
    """Run the graph the way agent/run_synthetic.py and the demo page do."""
    case = {
        "case_id": "DIRECT-SEQUENCE",
        "alerts": [
            {
                "id": "phish",
                "timestamp": "2026-10-09T08:00:00Z",
                "rule_name": "phishing",
                "host": "mail-01",
                "user": "alice",
            },
            {
                "id": "guess",
                "timestamp": "2026-10-09T10:00:00Z",
                "rule_name": "brute_force",
                "host": "web-01",
                "user": "bob",
            },
            {
                "id": "share",
                "timestamp": "2026-10-09T12:00:00Z",
                "rule_name": "smb_admin_share",
                "host": "db-01",
                "user": "carol",
            },
        ],
    }

    async def run():
        app = build_graph()
        config = {"configurable": {"thread_id": "direct-sequence"}}
        await app.ainvoke({"case": case, "audit_log": []}, config)
        return app.get_state(config).values["report"]["executive_summary"]

    return asyncio.run(run())


@pytest.mark.xfail(
    strict=True,
    reason="#38: the direct agent path chains techniques from unrelated alerts",
)
def test_direct_agent_summary_asserts_no_sequence_across_unrelated_alerts():
    summary = direct_agent_summary()
    assert not any(marker in summary for marker in SEQUENCE_MARKERS)
