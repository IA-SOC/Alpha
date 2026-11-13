"""S3-US5-T05 (#36): MITRE mapping results, unsupported behavior and separation.

Criteria used here until #32 lands, taken from the skill protocol
(references/protocolo.md, "Evidencia y ATT&CK"):

- every catalog pattern maps to its technique and tactic, as a candidate only;
- each mapping cites the alerts behind it and the catalog version used;
- behavior outside the catalog is not mapped and the report says so;
- a shared technique never makes alerts related, and correlation never
  depends on technique labels.

"""

import pytest
from fastapi.testclient import TestClient

from agent.investigation import build_attack_analysis
from app.main import create_app
from core.logic import RULES, map_alerts_to_mitre
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


def test_shadow_copy_deletion_maps_to_inhibit_system_recovery(client):
    result = investigate(client, tagged("vss", ["shadow_copy_deleted"]))
    techniques = {m["technique_id"] for m in result["report"]["attack_mapping"]}
    assert techniques == {"T1490"}


@pytest.mark.parametrize(
    "rule_name, technique_id",
    [
        ("Volume Shadow Copy Deletion via VssAdmin", "T1490"),
        ("Volume Shadow Copy Deleted or Resized via VssAdmin", "T1490"),
        ("Deleting Backup Catalogs with Wbadmin", "T1490"),
        ("Shadow copies deletion via vssadmin.exe", "T1490"),
        ("PsExec Network Connection", "T1569.002"),
        ("PsExec service installed (PSEXESVC)", "T1569.002"),
        ("Ransomware - Detected - Elastic Defend", "T1486"),
        ("Tactic: Lateral Movement", "T1021"),
    ],
)
def test_vendor_rule_names_match_despite_punctuation(rule_name, technique_id):
    """#33: real Elastic/Wazuh rule names, not only underscore keywords."""
    alert = {"id": "a", "rule_name": rule_name, "tags": []}
    assert [m["technique_id"] for m in map_alerts_to_mitre([alert])] == [technique_id]


# --- S5-US5-T01 (#146): Wazuh rule.mitre first, local catalog as fallback -----

WAZUH_RULE = {
    "level": 12,
    "description": "Windows Defender disabled",
    "mitre": {
        "id": ["T1562.001"],
        "tactic": ["Defense Evasion"],
        "technique": ["Disable or Modify Tools"],
    },
}


def wazuh_alert(aid, rule=WAZUH_RULE, tags=()):
    from agent.normalize import normalize_alert

    return normalize_alert({"id": aid, "rule": rule, "tags": list(tags)}, 1)


def test_native_wazuh_mitre_is_used_and_recorded():
    [mapping] = map_alerts_to_mitre([wazuh_alert("w1")])
    assert mapping["technique_id"] == "T1562.001"
    assert mapping["tactic"] == "Defense Evasion"
    assert mapping["technique_name"] == "Disable or Modify Tools"
    assert mapping["mapping_source"] == "wazuh_rule_mitre"


def test_native_wazuh_mitre_wins_over_the_catalog_for_the_same_alert():
    # The tags match T1110 in the catalog; Wazuh's own mapping still wins.
    mappings = map_alerts_to_mitre([wazuh_alert("w1", tags=["brute_force"])])
    assert [m["technique_id"] for m in mappings] == ["T1562.001"]


def test_alerts_without_wazuh_mitre_fall_back_to_the_catalog():
    plain = {"id": "c1", "rule_name": "x", "tags": ["brute_force"]}
    mappings = map_alerts_to_mitre([wazuh_alert("w1"), plain])
    by_id = {m["technique_id"]: m for m in mappings}
    assert by_id["T1110"]["mapping_source"] == "local_catalog"
    assert by_id["T1562.001"]["mapping_source"] == "wazuh_rule_mitre"
    assert by_id["T1110"]["supporting_alert_ids"] == ["c1"]


def test_invalid_wazuh_technique_ids_are_dropped():
    mitre = {
        "id": ["bogus", "T1078"],
        "tactic": ["Persistence", "Initial Access"],
        "technique": ["x", "Valid Accounts"],
    }
    rule = {"level": 5, "mitre": mitre}
    [mapping] = map_alerts_to_mitre([wazuh_alert("w1", rule)])
    # Dos tácticas aplanadas: no se asignan por posición.
    assert (mapping["technique_id"], mapping["tactic"]) == (
        "T1078", "Persistence | Initial Access")
    assert mapping["ambiguous"]


def test_equal_length_lists_are_not_paired_by_position():
    # PowerShell es Execution; emparejar por posición lo dejaría en Persistence.
    rule = {"level": 12, "mitre": {
        "id": ["T1059.001", "T1547.001"],
        "technique": ["PowerShell", "Registry Run Keys"],
        "tactic": ["Persistence", "Execution"],
    }}
    mappings = map_alerts_to_mitre([wazuh_alert("w1", rule)])
    assert {m["tactic"] for m in mappings} == {"Persistence | Execution"}
    assert all(m["ambiguous"] for m in mappings)


def test_single_tactic_applies_to_every_technique():
    rule = {"level": 5, "mitre": {
        "id": ["T1562.001", "T1562.004"], "tactic": ["Defense Evasion"],
        "technique": ["Disable or Modify Tools", "Disable or Modify System Firewall"],
    }}
    mappings = map_alerts_to_mitre([wazuh_alert("w1", rule)])
    assert {m["tactic"] for m in mappings} == {"Defense Evasion"}
    assert not any(m["ambiguous"] for m in mappings)


def test_native_mitre_is_read_from_an_elastic_source_wrapper():
    from agent.normalize import wazuh_mitre

    hit = {"_id": "x", "_source": {"rule": WAZUH_RULE}}
    assert [t["technique_id"] for t in wazuh_mitre(hit)] == ["T1562.001"]


def test_group_split_keeps_only_that_groups_provenance():
    from agent.investigation import correlated_attack_analysis

    wazuh = wazuh_alert("w1", {"level": 12, "mitre": {
        "id": ["T1110"], "technique": ["Brute Force"],
        "tactic": ["Credential Access"]}})
    catalog = {"id": "c1", "rule_name": "failed login", "tags": ["brute_force"],
               "source_fields": [], "timestamp_problem": None}
    mappings = map_alerts_to_mitre([wazuh, catalog])
    assert mappings[0]["mapping_source"] == "mixed"
    context = {"correlation": {"related_groups": [["c1"]]}}
    analysis = correlated_attack_analysis([wazuh, catalog], mappings, False, context)
    by_group = {tuple(m["correlation_group_alert_ids"]): m
                for m in analysis["attack_mapping"]}
    assert by_group[("c1",)]["alert_mapping_sources"] == {"c1": "local_catalog"}
    assert by_group[("c1",)]["mapping_source"] == "local_catalog"
    assert by_group[("w1",)]["alert_mapping_sources"] == {"w1": "wazuh_rule_mitre"}
    assert by_group[("w1",)]["mapping_source"] == "wazuh_rule_mitre"


def test_wazuh_mapping_source_reaches_the_report(client):
    alert = tagged("def-1", [])
    alert["raw_alert"]["rule"] = WAZUH_RULE
    result = investigate(client, alert)
    [mapping] = result["report"]["attack_mapping"]
    assert mapping["technique_id"] == "T1562.001"
    assert mapping["mapping_source"] == "wazuh_rule_mitre"
    assert "Wazuh" in mapping["source_version"]
    evidence = mapping["evidence"][0]
    source_fields = {
        field["path"]: field["value"] for field in evidence["source_fields"]
    }
    assert source_fields["/alerts/0/raw_alert/rule/mitre/id"] == ["T1562.001"]


def test_ambiguous_wazuh_tactics_are_not_assigned_by_position():
    rule = {"level": 12, "mitre": {
        "id": ["T1070.004", "T1485", "T1112"],
        "technique": ["File Deletion", "Data Destruction", "Modify Registry"],
        "tactic": ["Defense Evasion", "Impact"],
    }}
    mappings = map_alerts_to_mitre([wazuh_alert("w1", rule)])
    assert {mapping["tactic"] for mapping in mappings} == {"Defense Evasion | Impact"}
    assert all(mapping["ambiguous"] for mapping in mappings)


def test_mixed_sources_are_kept_per_alert_in_the_report():
    wazuh = wazuh_alert("w1", {"level": 12, "mitre": {
        "id": ["T1110"], "technique": ["Brute Force"],
        "tactic": ["Credential Access"],
    }})
    catalog = {"id": "c1", "rule_name": "failed login", "tags": ["brute_force"],
               "source_fields": [], "timestamp_problem": None}
    [mapping] = map_alerts_to_mitre([wazuh, catalog])
    assert mapping["mapping_source"] == "mixed"
    assert mapping["alert_mapping_sources"] == {
        "w1": "wazuh_rule_mitre", "c1": "local_catalog",
    }
    analysis = build_attack_analysis([wazuh, catalog], [mapping], synthetic=False)
    [reported] = analysis["attack_mapping"]
    assert reported["source_version"].startswith("rule.mitre nativo")
    assert {e["alert_id"]: e["mapping_source"] for e in reported["evidence"]} == {
        "w1": "wazuh_rule_mitre", "c1": "local_catalog",
    }


def test_wazuh_mitre_source_fields_reference_original_values():
    alert = wazuh_alert("w1")
    fields = {field["path"]: field["value"] for field in alert["source_fields"]}
    assert fields["/alerts/0/rule/mitre/id"] == ["T1562.001"]
    assert fields["/alerts/0/rule/mitre/technique"] == ["Disable or Modify Tools"]
    assert fields["/alerts/0/rule/mitre/tactic"] == ["Defense Evasion"]
