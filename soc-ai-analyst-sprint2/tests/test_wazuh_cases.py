import gzip
import hashlib
import json
import sys
import zipfile

import pytest

from app.services.traceability import _resolve_pointer
from app.services.wazuh_cases import main, prepare_cases
from app.services.wazuh_import import iter_wazuh_records
from tests.test_wazuh_enrichment import provider_alert

SUBMITTED = "2026-11-10T00:00:00Z"


def alert(index, rule="one", timestamp="2026-08-10T23:59:00-0500"):
    return {
        "id": str(index),
        "timestamp": timestamp,
        "decoder": {"name": "windows_eventchannel"},
        "rule": {"id": rule, "level": 3},
        "data": {"win": {"system": {"channel": "Security", "eventID": "1"}}},
    }


def write_source(tmp_path, rows, suffix=".ndjson"):
    path = tmp_path / ("source" + suffix)
    content = "\n".join(json.dumps(row) for row in rows).encode()
    if suffix == ".zip":
        compressed = gzip.compress(content, mtime=0)
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("dataset/day.json.gz", compressed)
            archive.writestr(
                "dataset/SHA256SUMS",
                hashlib.sha256(compressed).hexdigest() + "  day.json.gz\n",
            )
    else:
        path.write_bytes(
            gzip.compress(content, mtime=0) if suffix == ".gz" else content
        )
    return path


def prepare(source, output, **kwargs):
    return prepare_cases(source, output, submitted_at=SUBMITTED, **kwargs)


@pytest.mark.parametrize("suffix", [".ndjson", ".gz", ".zip"])
def test_complete_scan_rare_types_reproducibility_and_provenance(tmp_path, suffix):
    rows = [alert(i) for i in range(100)] + [alert(100, rule="rare")]
    source = write_source(tmp_path, rows, suffix)
    first, second = tmp_path / "first", tmp_path / "second"
    manifest = prepare(source, first)
    assert prepare(source, second) == manifest
    assert manifest["scanned"] == 101
    assert manifest["selected"] == 3
    assert sorted(s["population"] for s in manifest["strata"]) == [1, 100]
    assert manifest["cases"][0]["day"] == "2026-08-10"
    original = {
        (loc["member"], loc["line"]): row for row, loc in iter_wazuh_records(source)
    }
    for entry in manifest["cases"]:
        case = json.loads((first / entry["file"]).read_text())
        mapping = json.loads((first / entry["mapping"]).read_text())
        assert len(case["alerts"]) <= 50
        assert "100" in [a["alert_id"] for a in case["alerts"]]
        for loc in mapping["records"]:
            assert _resolve_pointer(case, loc["case_pointer"]) == (
                True,
                original[loc["member"], loc["line"]],
            )
    for path in first.iterdir():
        assert path.read_bytes() == (second / path.name).read_bytes()


def test_split_at_fifty_without_dropping_strata(tmp_path):
    source = write_source(tmp_path, [alert(i, rule=str(i)) for i in range(103)])
    manifest = prepare(source, tmp_path / "out")
    assert [c["alert_count"] for c in manifest["cases"]] == [50, 50, 3]
    assert manifest["selected"] == 103


@pytest.mark.parametrize(
    "options",
    [
        {"max_alerts": 0},
        {"max_alerts": 51},
        {"samples_per_stratum": 0},
    ],
)
def test_invalid_limits_do_not_publish(tmp_path, options):
    source = write_source(tmp_path, [alert(1)])
    with pytest.raises(ValueError):
        prepare(source, tmp_path / "out", **options)
    assert not (tmp_path / "out").exists()


def test_missing_timestamps_and_distinct_days_are_explicit(tmp_path):
    rows = [
        alert(1),
        alert(2, timestamp="2026-08-11T00:00:00-0500"),
        alert(3, timestamp="invalid"),
        alert(4, timestamp="2026-08-11T00:00:00"),
    ]
    manifest = prepare(write_source(tmp_path, rows), tmp_path / "out")
    assert [(c["day"], c["alert_count"]) for c in manifest["cases"]] == [
        ("2026-08-10", 1),
        ("2026-08-11", 1),
        ("undated", 2),
    ]


def test_provider_results_and_source_pointers_are_preserved(tmp_path):
    rows = [provider_alert("virustotal"), provider_alert("misp_file_hashes", "misp")]
    output = tmp_path / "out"
    manifest = prepare(write_source(tmp_path, rows), output)
    entry = manifest["cases"][0]
    case = json.loads((output / entry["file"]).read_text())
    mapping = json.loads((output / entry["mapping"]).read_text())
    assert entry["enrichment_count"] == 2
    assert entry["warning_count"] == 2
    for source in mapping["sources"]:
        found, enrichment = _resolve_pointer(case, source["enrichment_path"])
        assert found
        assert _resolve_pointer(case, source["raw_result_path"]) == (
            True,
            enrichment["raw_result"],
        )


@pytest.mark.parametrize("rows", [[], [alert(1), alert(1)], [{"id": None}]])
def test_invalid_sources_never_publish_partial_output(tmp_path, rows):
    source = write_source(tmp_path, rows)
    with pytest.raises(ValueError):
        prepare(source, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_mapping_failure_cleans_staging_and_retry_succeeds(tmp_path):
    source = write_source(tmp_path, [alert(1)])
    with pytest.raises(ValueError):
        prepare_cases(source, tmp_path / "out", submitted_at="bad date")
    assert not (tmp_path / "out").exists()
    assert not list(tmp_path.glob(".wazuh-cases-*"))
    prepare(source, tmp_path / "out")
    before = (tmp_path / "out" / "manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        prepare(source, tmp_path / "out")
    assert (tmp_path / "out" / "manifest.json").read_bytes() == before


def test_bad_member_checksum_fails_before_output(tmp_path):
    source = tmp_path / "bad.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("dataset/day.json.gz", gzip.compress(b'{"id":"1"}'))
        archive.writestr("dataset/SHA256SUMS", "0" * 64 + "  day.json.gz")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        prepare(source, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_late_malformed_record_aborts_without_publishing(tmp_path):
    source = write_source(tmp_path, [alert(1)])
    with source.open("a") as stream:
        stream.write("\nnot json\n")
    with pytest.raises(ValueError, match="line 2"):
        prepare(source, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_cli_cases_are_accepted_by_api(tmp_path, monkeypatch, client):
    source = write_source(tmp_path, [alert(i, rule=str(i)) for i in range(5)])
    output = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "wazuh_cases",
            str(source),
            "--output",
            str(output),
            "--submitted-at",
            SUBMITTED,
            "--max-alerts",
            "2",
        ],
    )
    main()
    manifest = json.loads((output / "manifest.json").read_text())
    assert [c["alert_count"] for c in manifest["cases"]] == [2, 2, 1]
    for entry in manifest["cases"]:
        payload = json.loads((output / entry["file"]).read_text())
        response = client.post("/api/v1/cases", json=payload)
        assert response.status_code == 201, response.text
