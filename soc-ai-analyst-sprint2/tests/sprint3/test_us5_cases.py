import pytest

from tests.sprint3.cases import EXPECTATIONS, load_case


@pytest.mark.parametrize(
    "alert_id, expected",
    EXPECTATIONS["us5_positive"]["mapping_by_alert"].items(),
)
def test_positive_mapping_has_independent_expected_id_and_tactic(
    alert_id, expected, sprint3_result
):
    mappings = sprint3_result("us5_positive")["report"]["attack_mapping"]
    selected = [
        m for m in mappings if alert_id in {e["alert_id"] for e in m["evidence"]}
    ]
    assert [[m["technique_id"], m["tactic"]] for m in selected] == [expected]
    assert all(m["status"] == "candidate" and m["source_version"] for m in selected)


@pytest.mark.parametrize("name", ["us5_negative", "us5_unknown"])
def test_benign_and_unsupported_samples_do_not_invent_mappings(name, sprint3_result):
    report = sprint3_result(name)["report"]
    assert report["attack_mapping"] == []
    assert report["hypotheses"] == []
    assert report["recommended_actions"] == []
    submitted = {a["alert_id"] for a in load_case(name)["alerts"]}
    assert {aid for t in report["timeline"] for aid in t["alert_ids"]} == submitted
    if name == "us5_unknown":
        assert any("fuera del catálogo" in line for line in report["limitations"])
