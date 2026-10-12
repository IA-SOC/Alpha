from copy import deepcopy

import pytest

from app.services.evidence import extract_events
from app.services.ioc_integration import integrate_iocs
from tests.test_correlation_engine import case_for, event


def ioc(value="192.0.2.1", kind="ip", **extra):
    return {
        "provider": "unverified-n8n-provider",
        "observable": {"type": kind, "value": value},
        **extra,
    }


def integrate(alerts, enrichments):
    case = case_for(*alerts, enrichments=enrichments)
    return integrate_iocs(case, extract_events(case))


def test_typed_match_preserves_provider_payload_and_references():
    supplied = ioc(
        raw_result={
            "custom": [None, {"score": 10}],
            "references": ["https://example.test/report"],
        }
    )
    before = deepcopy(supplied)
    item = integrate([event("a"), event("b", source="wazuh")], [supplied])[0]
    assert item["provider"] == supplied["provider"]
    assert item["raw_result"] == before["raw_result"]
    assert item["observable"] == before["observable"]
    assert item["associated_alert_ids"] == ["a", "b"]
    assert item["matched_fields"][0]["field"] == "/alerts/0/raw_alert/source/ip"
    assert item["source_path"] == "/enrichments/0"
    assert "verdict" not in item
    assert supplied == before


def test_explicit_link_is_distinct_from_observed_match():
    item = integrate([event("a")], [ioc("198.51.100.5", related_alert_ids=["a"])])[0]
    assert item["associated_alert_ids"] == ["a"]
    assert item["matched_alert_ids"] == []
    association = item["associations"][0]
    assert association["methods"] == ["explicit_reference"]
    assert association["fields"] == []
    assert association["reference_path"] == "/enrichments/0/related_alert_ids/0"


def test_both_link_types_and_multiple_providers_remain_separate():
    items = integrate(
        [event("a")],
        [ioc(related_alert_ids=["a"]), {**ioc(), "provider": "other-provider"}],
    )
    assert len(items) == 2
    assert items[0]["associations"][0]["methods"] == [
        "explicit_reference",
        "observable_match",
    ]
    assert items[0]["evidence_id"] != items[1]["evidence_id"]


def test_unmatched_and_unsupported_type_do_not_link_every_alert():
    items = integrate([event("a")], [ioc("198.51.100.4"), ioc(kind="unknown")])
    assert all(item["associated_alert_ids"] == [] for item in items)


def test_no_false_match_on_alert_id_message_or_substring():
    a = event("192.0.2.1", ip="192.0.2.10")
    a["raw_alert"]["message"] = "192.0.2.1"
    assert integrate([a], [ioc()])[0]["matched_alert_ids"] == []


@pytest.mark.parametrize("enrichments", [None, []])
def test_no_enrichment_is_supported(enrichments):
    assert integrate([event("a")], enrichments) == []


@pytest.mark.parametrize(
    "kind,value,raw",
    [
        ("domain", "MALICIOUS.EXAMPLE.", {"dns.question.name": "malicious.example"}),
        ("url", "https://example.test/a", {"url": {"full": "https://example.test/a"}}),
        ("sha256", "A" * 64, {"file": {"hash": {"sha256": "a" * 64}}}),
        ("ip", "2001:db8::1", {"destination.ip": "2001:db8:0:0:0:0:0:1"}),
    ],
)
def test_supported_observable_types(kind, value, raw):
    alert = event("a")
    alert["raw_alert"].update(raw)
    assert integrate([alert], [ioc(value, kind)])[0]["matched_alert_ids"] == ["a"]
