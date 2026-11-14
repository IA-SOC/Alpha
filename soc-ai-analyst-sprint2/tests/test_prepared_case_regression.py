"""#149: synthetic CI and opt-in prepared-case contract regression."""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.traceability import verify_traceability
from tests.test_wazuh_cases import alert, prepare, write_source

URL = "/api/v1/cases"


def load_cases(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    entries = manifest["cases"]
    if not entries:
        raise ValueError("Prepared manifest contains no cases")
    seen = set()
    for entry in entries:
        path = (directory / entry["file"]).resolve()
        if not path.is_relative_to(directory) or path in seen:
            raise ValueError("Unsafe or duplicate prepared case path")
        seen.add(path)
        yield json.loads(path.read_text(encoding="utf-8"))


def check_case(payload, database, expected_techniques=None):
    assert 1 <= len(payload["alerts"]) <= 50
    with TestClient(create_app(database_path=database)) as client:
        accepted = client.post(URL, json=payload)
        assert accepted.status_code == 201
        cid = accepted.json()["case_id"]
        assert client.get(f"{URL}/{cid}").json()["submitted_case"] == payload
        assert client.post(URL, json=payload).status_code == 409
        response = client.post(f"{URL}/{cid}/investigate")
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "pending_review"
        assert result["validation"]["ok"]
        assert result["validation"]["traceability_ok"]
        verify_traceability(result["investigation_context"], result["report"])
        assert result["report"]["review"]["status"] == "pending"
        if expected_techniques is not None:
            mappings = result["report"]["attack_mapping"]
            assert {m["technique_id"] for m in mappings} == expected_techniques
            assert all(m["status"] == "candidate" for m in mappings)
            assert all(m["mapping_source"] == "wazuh_rule_mitre" for m in mappings)
    with TestClient(create_app(database_path=database)) as client:
        assert client.get(f"{URL}/{cid}").json()["submitted_case"] == payload
        response = client.get(f"{URL}/{cid}/investigation")
        assert response.status_code == 200
        assert response.json() == result
        saved = response.json()
        verify_traceability(saved["investigation_context"], saved["report"])


def test_prepared_synthetic_cases(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "none")
    source = write_source(tmp_path, [alert(i, rule=str(i)) for i in range(51)])
    directory = tmp_path / "prepared"
    prepare(source, directory)
    cases = list(load_cases(directory))
    assert [len(case["alerts"]) for case in cases] == [50, 1]
    for index, payload in enumerate(cases):
        check_case(payload, tmp_path / f"case-{index}.sqlite3")


def test_private_prepared_cases(tmp_path, monkeypatch):
    configured = os.getenv("WAZUH_REGRESSION_DIR")
    if not configured:
        pytest.skip("Set WAZUH_REGRESSION_DIR to an external prepared dataset")
    directory = Path(configured).resolve()
    repository = Path(__file__).resolve().parents[2]
    if directory.is_relative_to(repository):
        pytest.fail("Private prepared cases must be outside the repository")
    monkeypatch.setenv("LLM_PROVIDER", "none")
    for index, payload in enumerate(load_cases(directory)):
        check_case(payload, tmp_path / f"case-{index}.sqlite3")


@pytest.mark.parametrize("techniques", [[], ["T1059.001"], ["T1059.001", "T1547.001"]])
def test_prepared_cases_with_explicit_synthetic_expectations(
    tmp_path, monkeypatch, techniques
):
    """Expectations come from authored input, never from an agent output snapshot."""
    monkeypatch.setenv("LLM_PROVIDER", "none")
    row = alert(1)
    if techniques:
        row["rule"]["mitre"] = {
            "id": techniques,
            "technique": ["PowerShell", "Registry Run Keys"][: len(techniques)],
            "tactic": ["Execution"]
            if len(techniques) == 1
            else ["Execution", "Persistence", "Privilege Escalation"],
        }
    source = write_source(tmp_path, [row])
    directory = tmp_path / "prepared"
    prepare(source, directory)
    [payload] = list(load_cases(directory))
    check_case(payload, tmp_path / "expected.sqlite3", set(techniques))


@pytest.mark.parametrize("files", [[], ["../outside.json"], ["case.json", "case.json"]])
def test_invalid_manifest_fails(tmp_path, files):
    (tmp_path / "manifest.json").write_text(
        json.dumps({"cases": [{"file": name} for name in files]}), encoding="utf-8"
    )
    (tmp_path / "case.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        list(load_cases(tmp_path))
