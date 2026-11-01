"""#90/#102: local adapters preserve raw samples and reuse existing v1.0 paths."""

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from app.services import siem_samples as adapter
from app.services.traceability import _resolve_pointer, verify_traceability
from tests.test_wazuh_enrichment import provider_alert

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "examples/sprint4/siem_samples"


@pytest.fixture
def samples():
    return {
        name: adapter.load_samples(SAMPLES / f"{name}.json")
        for name in ("elastic", "wazuh")
    }


def build(elastic=None, wazuh=None):
    return adapter.build_sample_case(
        case_id="SYNTHETIC-US21",
        submitted_at="2026-10-31T12:00:00Z",
        elastic_alerts=elastic,
        wazuh_alerts=wazuh,
    )


@pytest.mark.parametrize("source", ["elastic", "wazuh", "mixed"])
def test_adapter_output_matches_frozen_schema_and_intake(source, samples, client):
    elastic = samples["elastic"] if source != "wazuh" else []
    wazuh = samples["wazuh"] if source != "elastic" else []
    before = deepcopy(elastic + wazuh)
    mapped = build(elastic, wazuh)
    payload = mapped.case.model_dump(exclude_unset=True)
    schema = json.loads(
        (ROOT / "docs/incident-case-input-v1.0.schema.json").read_text()
    )
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)
    assert [alert["raw_alert"] for alert in payload["alerts"]] == before
    assert elastic + wazuh == before
    for record in mapped.records:
        _, original = _resolve_pointer(
            samples[record["source_system"]], record["sample_path"]
        )
        exists, preserved = _resolve_pointer(payload, record["case_path"])
        assert exists and preserved == original
    response = client.post("/api/v1/cases", json=payload)
    assert response.status_code == 201, response.text
    cid = response.json()["case_id"]
    assert client.get(f"/api/v1/cases/{cid}").json()["submitted_case"] == payload
    mapped.case.alerts[0].raw_alert["new"] = "not in original"
    assert elastic + wazuh == before


def test_mixed_wazuh_provider_reuses_mapping_and_rebases_sidecar(samples):
    provider = provider_alert()
    mapped = build(samples["elastic"], samples["wazuh"] + [provider])
    payload = mapped.case.model_dump(exclude_unset=True)
    assert payload["enrichments"][0]["related_alert_ids"] == ["provider-1", "original"]
    assert payload["enrichments"][0]["raw_result"] == provider["data"]["virustotal"]
    assert len(mapped.sources) == 1 and not mapped.warnings
    source = mapped.sources[0]
    assert source["raw_result_path"].startswith("/alerts/2/raw_alert/")
    assert (
        _resolve_pointer(payload, source["raw_result_path"])[1]
        == (payload["enrichments"][0]["raw_result"])
    )
    assert (
        _resolve_pointer(payload, source["observable_value_path"])[1]
        == (payload["enrichments"][0]["observable"]["value"])
    )


def test_provider_warning_paths_are_rebased_without_inventing_iocs(samples):
    raw = provider_alert()
    raw["data"]["virustotal"] = {"error": "synthetic rate-limit"}
    mapped = build(samples["elastic"], [raw])
    assert mapped.case.enrichments == []
    assert mapped.warnings[0]["path"] == "/alerts/1/raw_alert/data/virustotal"
    assert mapped.case.alerts[1].raw_alert == raw


@pytest.mark.parametrize(
    "raw",
    [
        {},
        {"event": {"id": 1}},
        {"event": {"id": " "}},
        {"_id": "document-id-only"},
        None,
        [],
    ],
)
def test_elastic_missing_or_nonstring_native_ids_are_rejected(raw):
    with pytest.raises(ValueError):
        build([raw])


def test_duplicates_across_sources_are_not_renamed(samples):
    samples["wazuh"][0]["id"] = samples["elastic"][0]["event"]["id"]
    with pytest.raises(ValueError, match="Duplicate"):
        build(samples["elastic"], samples["wazuh"])
    with pytest.raises(ValueError):
        build(samples["elastic"] * 2)


def test_combined_limit_empty_arrays_and_bad_metadata_fail(samples):
    with pytest.raises(ValueError, match="Combined"):
        build([{"event": {"id": str(i)}} for i in range(50)], samples["wazuh"])
    with pytest.raises(ValueError):
        build([], [])
    with pytest.raises(ValueError):
        adapter.build_sample_case(
            case_id="x", submitted_at="no-zone", elastic_alerts=samples["elastic"]
        )
    with pytest.raises(ValueError):
        build({"not": "an array"})


def test_full_search_hit_requires_explicit_matching_profile(
    samples, monkeypatch, client
):
    hit = {
        "_id": "different-index-document-id",
        "_index": "synthetic-index",
        "_source": samples["elastic"][0],
        "custom": {"keep": True},
    }
    with pytest.raises(ValueError):
        build([hit])
    monkeypatch.setattr(
        adapter,
        "settings",
        replace(adapter.settings, elastic_alert_id_pointer="/_source/event/id"),
    )
    mapped = build([hit])
    assert mapped.case.alerts[0].alert_id == samples["elastic"][0]["event"]["id"]
    assert mapped.case.alerts[0].raw_alert == hit
    assert mapped.records[0]["id_pointer"] == "/_source/event/id"
    client.app.state.case_service.settings = adapter.settings
    payload = mapped.case.model_dump(exclude_unset=True)
    response = client.post("/api/v1/cases", json=payload)
    assert response.status_code == 201, response.text
    assert (
        client.get(f"/api/v1/cases/{response.json()['case_id']}").json()[
            "submitted_case"
        ]
        == payload
    )


def test_warning_native_id_that_looks_like_a_path_is_not_rewritten(samples):
    aid = "/alerts/0/not-a-pointer"
    raw = provider_alert(aid=aid)
    raw["data"]["virustotal"] = {"error": "synthetic rate limit"}
    mapped = build(samples["elastic"], [raw])
    assert mapped.warnings[0]["alert_id"] == aid
    assert mapped.warnings[0]["path"] == "/alerts/1/raw_alert/data/virustotal"
    assert mapped.case.alerts[1].alert_id == aid


def test_missing_event_time_remains_missing_through_agent(samples, client):
    del samples["elastic"][0]["@timestamp"]
    payload = build(samples["elastic"], samples["wazuh"] + [provider_alert()])
    payload = payload.case.model_dump(exclude_unset=True)
    accepted = client.post("/api/v1/cases", json=payload)
    assert accepted.status_code == 201, accepted.text
    prefix = f"/api/v1/cases/{accepted.json()['case_id']}"
    investigated = client.post(prefix + "/investigate")
    assert investigated.status_code == 200, investigated.text
    result = investigated.json()
    assert result["validation"]["ok"] and result["validation"]["traceability_ok"]
    assert result["investigation_context"]["original_case"] == payload
    verify_traceability(result["investigation_context"], result["report"])
    entry = next(
        t for t in result["report"]["timeline"] if t["alert_ids"] == ["ecs-sample-001"]
    )
    assert entry["timestamp_original"] is None and entry["timestamp_utc"] is None
    assert (
        result["report"]["enrichment"]["items"][0]["raw_result"]
        == (payload["enrichments"][0]["raw_result"])
    )


@pytest.mark.parametrize(
    "text", ["{}", "[1]", '[{"id":"a","id":"b"}]', '[{"id":"a","custom":NaN}]', "["]
)
def test_malformed_samples_fail_without_silent_loss(tmp_path, text):
    path = tmp_path / "bad.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        adapter.load_samples(path)


def test_cli_writes_pair_and_preserves_source_files(tmp_path, monkeypatch):
    output = tmp_path / "case.json"
    before = (SAMPLES / "elastic.json").read_bytes()
    monkeypatch.setattr(
        "sys.argv",
        [
            "siem_samples",
            "--elastic",
            str(SAMPLES / "elastic.json"),
            "--wazuh",
            str(SAMPLES / "wazuh.json"),
            "--case-id",
            "CLI-SYNTHETIC",
            "--submitted-at",
            "2026-10-31T12:00:00Z",
            "--output",
            str(output),
        ],
    )
    adapter.main()
    payload = json.loads(output.read_text(encoding="utf-8"))
    audit = json.loads(output.with_suffix(".json.mapping.json").read_text())
    assert len(payload["alerts"]) == len(audit["records"]) == 2
    assert (SAMPLES / "elastic.json").read_bytes() == before
    with pytest.raises(SystemExit):
        adapter.main()
    assert json.loads(output.read_text(encoding="utf-8")) == payload


def test_invalid_cli_never_writes_case_or_echoes_raw_values(
    tmp_path, monkeypatch, capsys
):
    source, output = tmp_path / "bad.json", tmp_path / "case.json"
    source.write_text('[{"event":{"id":42},"custom":"synthetic-private-marker"}]')
    monkeypatch.setattr(
        "sys.argv",
        [
            "siem_samples",
            "--elastic",
            str(source),
            "--case-id",
            "x",
            "--submitted-at",
            "2026-10-31T12:00:00Z",
            "--output",
            str(output),
        ],
    )
    with pytest.raises(SystemExit):
        adapter.main()
    assert not output.exists() and not output.with_suffix(".json.mapping.json").exists()
    assert "synthetic-private-marker" not in capsys.readouterr().err
