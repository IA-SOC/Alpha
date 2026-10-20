import pytest

from app.schemas.case import IncidentCase
from app.services.evidence import extract_events
from tests.sprint3.cases import EXPECTATIONS, load_case

CASES = ["us4_elastic", "us4_wazuh", "us4_mixed"]


@pytest.mark.parametrize("name", CASES)
def test_native_sources_and_utc_expectations(name):
    payload = load_case(name)
    sources = {a["source_system"] for a in payload["alerts"]}
    expected_sources = (
        {"elastic", "wazuh"} if name == "us4_mixed" else {name.removeprefix("us4_")}
    )
    assert sources == expected_sources
    events = extract_events(IncidentCase.model_validate(payload))
    assert {e.alert_id: e.timestamp_utc for e in events} == EXPECTATIONS[name][
        "utc_by_id"
    ]


@pytest.mark.parametrize("name", CASES)
def test_api_orders_dated_events_and_keeps_stable_ties(name, sprint3_result):
    timeline = sprint3_result(name)["report"]["timeline"]
    dated = [item["alert_ids"][0] for item in timeline if item["timestamp_utc"]]
    assert dated == EXPECTATIONS[name]["dated_order"]


@pytest.mark.parametrize("name", CASES)
def test_original_times_missing_values_and_alert_ids_survive(name, sprint3_result):
    payload = load_case(name)
    timeline = sprint3_result(name)["report"]["timeline"]
    by_id = {item["alert_ids"][0]: item for item in timeline}
    assert len(timeline) == len(by_id) == len(payload["alerts"])
    assert set(by_id) == {a["alert_id"] for a in payload["alerts"]}
    for alert in payload["alerts"]:
        raw = alert["raw_alert"]
        timestamp = raw.get("@timestamp", raw.get("timestamp"))
        assert by_id[alert["alert_id"]]["timestamp_original"] == timestamp
    assert {aid for aid, item in by_id.items() if not item["timestamp_utc"]} == set(
        EXPECTATIONS[name]["unknown_time_ids"]
    )
    assert by_id["no-zone"]["timezone_unknown"] is True
    assert all(item["certainty"] == "observed" for item in timeline)
