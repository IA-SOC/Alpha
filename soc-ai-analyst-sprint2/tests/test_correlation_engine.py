"""US2 behavior: evidence, uncertainty and noise, not fixture presence."""

from copy import deepcopy
from uuid import uuid4

import pytest

from app.schemas.case import IncidentCase
from app.services.agent_adapter import adapt_case
from app.services.case_service import native_identifier
from app.services.correlation import correlate
from app.services.evidence import extract_events
from app.storage.case_store import AcceptedCase


def event(
    aid,
    *,
    ip="192.0.2.1",
    host="web-01",
    user="analyst",
    time="2026-10-09T12:00:00Z",
    source="elastic",
):
    if source == "elastic":
        raw = {
            "event": {"id": aid},
            "@timestamp": time,
            "source": {"ip": ip},
            "host": {"name": host},
            "user": {"name": user},
        }
    else:
        raw = {
            "id": aid,
            "timestamp": time,
            "data": {"srcip": ip, "dstuser": user},
            "agent": {"name": host},
            "rule": {"level": 5},
        }
    return {"alert_id": aid, "source_system": source, "raw_alert": raw}


def case_for(*alerts, enrichments=None):
    payload = {
        "schema_version": "1.0",
        "case_id": "TEST-CORRELATION",
        "submitted_at": "2026-10-09T12:30:00Z",
        "alerts": list(alerts),
    }
    if enrichments is not None:
        payload["enrichments"] = enrichments
    return IncidentCase.model_validate(payload)


def analysis(*alerts):
    return correlate(extract_events(case_for(*alerts)))


@pytest.mark.parametrize("second_source", ["elastic", "wazuh"])
def test_two_related_alerts_across_sources(second_source):
    result = analysis(event("a"), event("b", source=second_source))
    rel = result.relationships[0]
    assert rel.classification == "related" and rel.rule == "R1"
    assert rel.alert_ids == ["a", "b"]
    assert {e.kind for e in rel.evidence if e.assessment == "shared"} >= {
        "ip",
        "host_name",
        "user_name",
    }


def test_noise_is_relative_and_all_alerts_are_retained():
    result = analysis(
        event("a"),
        event("b"),
        event("noise", ip="198.51.100.9", host="dns-02", user="backup"),
    )
    assert result.noise_alert_ids == ["noise"]
    assert result.related_groups == [["a", "b"]]
    assert [r.classification for r in result.relationships] == [
        "related",
        "unrelated",
        "unrelated",
    ]
    assert len(result.alerts) == 3


@pytest.mark.parametrize(
    "timestamp,classification",
    [
        ("2026-10-09T12:05:00Z", "related"),
        ("2026-10-09T12:05:00.001Z", "uncertain"),
        ("2026-10-09T07:00:00-05:00", "related"),
        ("2026-10-09T12:00:00", "uncertain"),
        ("2026-10-10T12:00:00Z", "uncertain"),
        (None, "uncertain"),
        ("invalid", "uncertain"),
        ("9999-12-31T23:59:59-23:59", "uncertain"),
    ],
)
def test_time_window_timezone_and_missing_time(timestamp, classification):
    assert (
        analysis(event("a"), event("b", time=timestamp)).relationships[0].classification
        == classification
    )


def test_one_ip_or_time_alone_is_not_enough():
    assert (
        analysis(event("a"), event("b", host="other", user="other"))
        .relationships[0]
        .classification
        == "uncertain"
    )
    minimal = {"alert_id": "b", "source_system": "wazuh", "raw_alert": {"id": "b"}}
    result = analysis(event("a"), minimal)
    assert result.relationships[0].classification == "uncertain"
    assert result.noise_alert_ids == []
    assert analysis(minimal).alerts[0].classification == "uncertain"


def test_mitre_or_submitter_correlation_labels_are_not_evidence():
    a, b = event("a"), event("b", ip="198.51.100.4", host="other", user="other")
    for alert in (a, b):
        alert["raw_alert"]["tags"] = ["brute_force"]
        alert["raw_alert"]["threat.technique.id"] = "T1110"
    assert analysis(a, b).relationships[0].classification == "unrelated"


def test_each_evidence_pointer_resolves_to_original_value():
    case = case_for(event("a"), event("b", source="wazuh"))
    result = correlate(extract_events(case))
    payload = case.model_dump(exclude_unset=True)
    for rel in result.relationships:
        for item in rel.evidence:
            for field in item.fields:
                assert native_identifier(payload, field.path) == field.value


def test_flat_and_source_envelopes_preserve_metadata_and_colliding_fields():
    a = event("a")
    a["raw_alert"] = {
        "_id": "a",
        "_index": "native-index",
        "alert_id": "custom-value",
        "_source": {
            "event.id": "a",
            "source.ip": "192.0.2.1",
            "host.name": "web-01",
            "user.name": "analyst",
            "@timestamp": "2026-10-09T12:00:00Z",
            "customer/field~": [None, {"k": True}],
        },
    }
    case = case_for(a, event("b"))
    before = deepcopy(case.model_dump(exclude_unset=True))
    adapted = adapt_case(AcceptedCase(uuid4(), case))
    assert adapted["alerts"][0]["alert_id"] == "a"
    assert adapted["investigation_context"]["original_case"] == before
    assert case.model_dump(exclude_unset=True) == before
    assert (
        adapted["investigation_context"]["correlation"]["relationships"][0][
            "classification"
        ]
        == "related"
    )


def test_conflicting_event_timestamps_are_uncertain():
    b = event("b")
    b["raw_alert"]["timestamp"] = "2026-10-09T13:00:00Z"
    assert analysis(event("a"), b).relationships[0].classification == "uncertain"


def test_invalid_and_multiple_ips_do_not_create_independent_signals():
    a, b = event("a", host=None, user=None), event("b", host=None, user=None)
    for alert in (a, b):
        alert["raw_alert"]["destination"] = {"ip": "192.0.2.3"}
        alert["raw_alert"]["host"]["ip"] = ["not-an-ip", "192.0.2.4"]
    result = analysis(a, b)
    assert result.relationships[0].classification == "uncertain"
    assert not any(
        a.value == "not-an-ip"
        for e in extract_events(case_for(a, b))
        for a in e.attributes
    )


def test_configurable_window_and_fifty_alerts():
    events = extract_events(case_for(*[event(str(i)) for i in range(50)]))
    assert len(correlate(events).relationships) == 1225
    events = extract_events(
        case_for(event("a"), event("b", time="2026-10-09T12:06:00Z"))
    )
    assert correlate(events, 600).relationships[0].classification == "related"
    with pytest.raises(ValueError):
        correlate(events, 0)
