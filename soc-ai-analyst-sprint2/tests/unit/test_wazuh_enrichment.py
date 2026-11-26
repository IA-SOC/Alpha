"""US3: independently synthetic provider shapes, never customer records."""

import gzip
import json
import zipfile
from copy import deepcopy

import pytest

from app.services.evidence import extract_events
from app.services.ioc_integration import integrate_iocs
from app.services.traceability import _resolve_pointer
from app.services.wazuh_enrichment import build_wazuh_case
from app.services.wazuh_import import main, select_alerts


def provider_alert(provider="virustotal", aid="provider-1"):
    result = {"source": {"alert_id": "original", "sha1": "a" * 40}}
    if provider == "virustotal":
        result.update(found="1", malicious="0", positives="0", total="60")
    else:
        result.update(found="1", type="sha256", value="b" * 64)
    return {
        "id": aid,
        "timestamp": "2026-08-10T00:00:00.938-0500",
        "data": {"integration": provider, provider: result},
        "rule": {"id": "test-rule", "level": 3},
    }


def map_alerts(*alerts):
    return build_wazuh_case(
        list(alerts), case_id="US3-SYNTHETIC", submitted_at="2026-10-26T12:00:00Z"
    )


@pytest.mark.parametrize("provider", ["virustotal", "misp_file_hashes"])
def test_mapping_preserves_originals_and_resolvable_source_paths(provider):
    raw = provider_alert(provider)
    raw["data"][provider]["custom"] = {"unknown": [None, True, 42]}
    parent = {"id": "original", "syscheck": {"sha1_after": "a" * 40}}
    before = deepcopy([parent, raw])
    mapped = map_alerts(parent, raw)
    case = mapped.case.model_dump(exclude_unset=True)
    assert [a["raw_alert"] for a in case["alerts"]] == before
    assert [parent, raw] == before
    assert not mapped.warnings
    enrichment = case["enrichments"][0]
    assert enrichment["related_alert_ids"] == ["provider-1", "original"]
    assert enrichment["raw_result"] == raw["data"][provider]
    for source in mapped.sources:
        assert _resolve_pointer(case, source["raw_result_path"]) == (
            True,
            enrichment["raw_result"],
        )
        assert _resolve_pointer(case, source["observable_value_path"]) == (
            True,
            enrichment["observable"]["value"],
        )
    items = integrate_iocs(mapped.case, extract_events(mapped.case))
    assert items[0]["raw_result"] == enrichment["raw_result"]
    assert "verdict" not in items[0]


def test_missing_source_alert_is_preserved_but_not_a_dangling_reference():
    mapped = map_alerts(provider_alert())
    enrichment = mapped.case.enrichments[0]
    assert enrichment.related_alert_ids == ["provider-1"]
    assert enrichment.raw_result["source"]["alert_id"] == "original"
    assert mapped.warnings[0]["code"] == "source_alert_not_in_case"


@pytest.mark.parametrize(
    "result",
    [
        {"error": "204", "description": "rate limit"},
        {"source": {"sha1": "invalid"}},
        None,
        [],
    ],
)
def test_unusable_results_remain_in_raw_alert_without_invented_iocs(result):
    raw = provider_alert()
    raw["data"]["virustotal"] = result
    mapped = map_alerts(raw)
    assert mapped.case.alerts[0].raw_alert == raw
    assert mapped.case.enrichments == []
    assert len(mapped.warnings) == 1


def test_no_record_and_zero_scores_are_not_interpreted_as_clean():
    raw = provider_alert()
    raw["data"]["virustotal"].update(found="0", malicious="0")
    item = map_alerts(raw).case.enrichments[0].model_dump(exclude_unset=True)
    assert item["raw_result"]["found"] == "0"
    assert "verdict" not in item and "confidence" not in item


def test_hash_precedence_preserves_original_case_and_provider_separation():
    vt, misp = provider_alert(), provider_alert("misp_file_hashes", "provider-2")
    vt["data"]["virustotal"]["source"]["sha256"] = "B" * 64
    mapped = map_alerts(vt, misp)
    assert [e.provider for e in mapped.case.enrichments] == ["virustotal", "misp"]
    assert mapped.case.enrichments[0].observable.value == "B" * 64


@pytest.mark.parametrize("raw", [{}, {"id": 1}, {"id": " "}])
def test_invalid_native_ids_are_rejected(raw):
    with pytest.raises(ValueError):
        map_alerts(raw)


def test_duplicates_and_case_limit_are_rejected():
    with pytest.raises(ValueError):
        map_alerts(provider_alert(), provider_alert())
    with pytest.raises(ValueError):
        map_alerts(*[{"id": str(i)} for i in range(51)])


def test_unknown_integration_and_free_text_are_not_provider_results():
    mapped = map_alerts(
        {
            "id": "x",
            "data": {"integration": "unknown"},
            "message": "virustotal malicious 100",
        }
    )
    assert mapped.case.enrichments == []


def test_selects_explicit_ids_from_gzip_zip_and_detects_missing_duplicates(tmp_path):
    raw = provider_alert()
    compressed = gzip.compress((json.dumps(raw) + "\n").encode())
    archive = tmp_path / "sample.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("nested/sample.json.gz", compressed)
    records, locations = select_alerts(archive, ["provider-1"])
    assert records == [raw]
    assert locations == [{"member": "nested/sample.json.gz", "line": 1}]
    with pytest.raises(ValueError, match="not found"):
        select_alerts(archive, ["missing"])
    with zipfile.ZipFile(archive, "a") as z:
        z.writestr("second.json.gz", compressed)
    with pytest.raises(ValueError, match="more than once"):
        select_alerts(archive, ["provider-1"])


def test_cli_writes_contract_and_source_map_without_overwriting(tmp_path, monkeypatch):
    source = tmp_path / "alerts.ndjson"
    source.write_text(json.dumps(provider_alert()) + "\n", encoding="utf-8")
    output = tmp_path / "case.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "wazuh_import",
            str(source),
            "--alert-id",
            "provider-1",
            "--case-id",
            "CLI-US3",
            "--submitted-at",
            "2026-10-26T12:00:00Z",
            "--output",
            str(output),
        ],
    )
    main()
    payload = json.loads(output.read_text(encoding="utf-8"))
    audit = json.loads(output.with_suffix(".json.mapping.json").read_text())
    assert payload["case_id"] == "CLI-US3"
    assert audit["records"] == [{"member": "alerts.ndjson", "line": 1}]
    assert len(audit["sources"]) == 1
    with pytest.raises(SystemExit):
        main()
    assert json.loads(output.read_text(encoding="utf-8")) == payload
