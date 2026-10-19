"""S3-US5-T05 (#36): MITRE mapping results, unsupported behavior and separation.

Criteria used here until #32 lands, taken from the skill protocol
(references/protocolo.md, "Evidencia y ATT&CK"):

- every catalog pattern maps to its technique and tactic, as a candidate only;
- each mapping cites the alerts behind it and the catalog version used;
- behavior outside the catalog is not mapped and the report says so;
- a shared technique never makes alerts related, and correlation never
  depends on technique labels.

Checks that need #33 are strict xfails, so they fail loudly once it is fixed.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from core.logic import RULES
from tests.helpers import investigate, tagged

PATTERNS = [
    (pattern, rule["technique_id"], rule["tactic"])
    for rule in RULES
    for pattern in rule["match_any"]
]


def isolated(index, aid, tags):
    """An alert that shares no IP, host, user or time window with the others."""
    return tagged(
        aid,
        tags,
        ip=f"198.51.100.{index + 1}",
        host=f"host-{index}",
        user=f"user-{index}",
        time=f"2026-10-09T{index:02d}:00:00Z",
    )


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    path = tmp_path_factory.mktemp("mitre") / "cases.sqlite3"
    with TestClient(create_app(database_path=path)) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def catalog_result(client):
    alerts = [
        isolated(index, f"alert-{pattern}", [pattern])
        for index, (pattern, _, _) in enumerate(PATTERNS)
    ]
    return investigate(client, *alerts)


def mappings_for(result, alert_id):
    return [
        m
        for m in result["report"]["attack_mapping"]
        if alert_id in {e["alert_id"] for e in m["evidence"]}
    ]


@pytest.mark.parametrize("pattern, technique_id, tactic", PATTERNS)
def test_each_catalog_pattern_maps_to_its_technique(
    catalog_result, pattern, technique_id, tactic
):
    mappings = mappings_for(catalog_result, f"alert-{pattern}")
    assert [(m["technique_id"], m["tactic"]) for m in mappings] == [
        (technique_id, tactic)
    ]


def test_mappings_are_candidates_that_cite_their_alerts_and_catalog(catalog_result):
    mappings = catalog_result["report"]["attack_mapping"]
    assert len(mappings) == len(PATTERNS)
    for mapping in mappings:
        assert mapping["status"] == "candidate"
        assert mapping["source_version"]
        assert mapping["evidence"]
        assert all(e["role"] == "supporting" for e in mapping["evidence"])


def test_behavior_outside_the_catalog_is_not_mapped(client):
    result = investigate(
        client,
        tagged("kerb-1", ["kerberoasting"]),
        tagged("kerb-2", ["service_ticket_request"]),
    )
    report = result["report"]
    assert report["attack_mapping"] == []
    assert report["hypotheses"] == []
    assert report["recommended_actions"] == []
    assert any("fuera del catálogo" in line for line in report["limitations"])


def test_a_shared_technique_does_not_relate_alerts(client):
    with_label = investigate(
        client,
        isolated(1, "a", ["brute_force"]),
        isolated(2, "b", ["brute_force"]),
    )
    without_label = investigate(
        client,
        isolated(1, "a", []),
        isolated(2, "b", []),
    )
    groups = with_label["correlation"]["related_groups"]
    assert groups == without_label["correlation"]["related_groups"] == []
    mappings = with_label["report"]["attack_mapping"]
    assert [m["technique_id"] for m in mappings] == ["T1110", "T1110"]
    assert all(len(m["evidence"]) == 1 for m in mappings)


def test_related_alerts_keep_one_group_across_techniques(client):
    result = investigate(
        client,
        tagged("login", ["brute_force"]),
        tagged("share", ["smb_admin_share"]),
    )
    assert result["correlation"]["related_groups"] == [["login", "share"]]
    mappings = result["report"]["attack_mapping"]
    assert {m["technique_id"] for m in mappings} == {"T1110", "T1021"}
    for mapping in mappings:
        assert mapping["correlation_group_alert_ids"] == ["login", "share"]


@pytest.mark.xfail(
    strict=True,
    reason="#33: shadow-copy deletion is still mapped to T1486 with file encryption",
)
def test_shadow_copy_deletion_maps_to_inhibit_system_recovery(client):
    result = investigate(client, tagged("vss", ["shadow_copy_deleted"]))
    techniques = {m["technique_id"] for m in result["report"]["attack_mapping"]}
    assert techniques == {"T1490"}
