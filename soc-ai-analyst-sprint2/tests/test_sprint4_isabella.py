
import json
import os
from copy import deepcopy
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.finding_review import finding_keys
from app.services.traceability import verify_traceability
from tests.test_correlation_engine import case_for, event

ROOT = Path(__file__).resolve().parents[1]
URL = "/api/v1/cases"
MANIFEST = json.loads((ROOT / "examples/sprint4/manifest.json").read_text())


@pytest.mark.parametrize("name,status", MANIFEST.items())
def test_reusable_intake_cases(client, name, status):
    payload = json.loads((ROOT / "examples/sprint4" / name).read_text())
    response = client.post(URL, json=payload)
    assert response.status_code == status, response.text
    if status == 201:
        cid = response.json()["case_id"]
        assert client.get(f"{URL}/{cid}").json()["submitted_case"] == payload
        assert client.post(URL, json=payload).status_code == 409


@pytest.fixture
def investigated(tmp_path):
    path = tmp_path / "review.sqlite3"
    app = create_app(database_path=path)
    with TestClient(app) as client:
        a = event("a")
        a["raw_alert"]["tags"] = ["brute_force"]
        payload = case_for(a).model_dump(exclude_unset=True)
        accepted = client.post(URL, json=payload)
        cid = accepted.json()["case_id"]
        response = client.post(f"{URL}/{cid}/investigate")
        assert response.status_code == 200, response.text
        yield client, path, cid, response.json()


def decision_for(result):
    return {
        "status": "corrected",
        "analyst": "Isabella",
        "notes": "Reviewed evidence",
        "run_id": result["run_id"],
        "findings": [
            {
                "finding_key": key,
                "status": "rejected",
                "notes": "Insufficient evidence to confirm an attack",
            }
            for key in finding_keys(result["report"])
        ],
    }


def test_structured_review_after_restart_and_json_export(investigated):
    _, path, cid, result = investigated
    decision = decision_for(result)
    assert decision["findings"]
    with TestClient(create_app(database_path=path)) as restarted:
        response = restarted.post(f"{URL}/{cid}/review", json=decision)
        assert response.status_code == 200, response.text
        reviewed = response.json()
        assert reviewed["report"]["review"]["findings"] == decision["findings"]
        assert reviewed["report"]["hypotheses"] == result["report"]["hypotheses"]
        assert restarted.post(f"{URL}/{cid}/review", json=decision).status_code == 409
    with TestClient(create_app(database_path=path)) as restarted:
        saved = restarted.get(f"{URL}/{cid}/investigation").json()
        exported = restarted.get(f"{URL}/{cid}/export")
        assert exported.status_code == 200
        assert exported.headers["content-type"].startswith("application/json")
        assert "attachment" in exported.headers["content-disposition"]
        assert exported.json() == saved == reviewed
        verify_traceability(saved["investigation_context"], saved["report"])


@pytest.mark.parametrize(
    "change,status",
    [
        ("stale", 409),
        ("foreign", 422),
        ("duplicate", 422),
        ("missing", 422),
        ("blank", 422),
        ("missing_run", 409),
    ],
)
def test_reject_invalid_finding_decisions_without_mutation(
    investigated, change, status
):
    client, _, cid, result = investigated
    decision = decision_for(result)
    if change == "stale":
        decision["run_id"] = "old-run"
    elif change == "foreign":
        decision["findings"][0]["finding_key"] = "foreign-finding"
    elif change == "duplicate":
        decision["findings"].append(decision["findings"][0])
    elif change == "missing":
        decision["findings"] = []
    elif change == "blank":
        decision["findings"][0]["notes"] = "  "
    else:
        decision.pop("run_id")
    response = client.post(f"{URL}/{cid}/review", json=decision)
    assert response.status_code == status, response.text
    assert client.get(f"{URL}/{cid}/investigation").json() == result


def test_same_finding_from_another_case_cannot_review_this_run(investigated):
    client, _, cid, result = investigated
    payload = case_for(event("b")).model_dump(exclude_unset=True)
    payload["case_id"] = "other-case"
    other = client.post(URL, json=payload).json()["case_id"]
    response = client.post(f"{URL}/{other}/review", json=decision_for(result))
    assert response.status_code == 409
    assert client.get(f"{URL}/{cid}/investigation").json() == result


def test_atomic_review_rejects_a_rerun_and_duplicate_write(investigated):
    client, path, cid, result = investigated
    store = client.app.state.investigation_service.store
    changed = deepcopy(result)
    changed["run_id"] = "new-run"
    store.save_investigation(UUID(cid), changed)
    with pytest.raises(LookupError):
        store.save_review(UUID(cid), result["run_id"], result)
    assert store.get_investigation(UUID(cid)) == changed


def test_missing_export_and_no_investigation(client):
    from uuid import uuid4

    assert client.get(f"{URL}/{uuid4()}/export").status_code == 404


@pytest.mark.parametrize("field", ["alert_id", "path", "value"])
def test_report_tampering_is_rejected(investigated, field):
    result = investigated[-1]
    report = deepcopy(result["report"])
    source = report["timeline"][0]["source_fields"][0]
    source[field] = {"alert_id": "foreign", "path": "/not-present", "value": "forged"}[
        field
    ]
    with pytest.raises(ValueError):
        verify_traceability(result["investigation_context"], report)


CLIENT_DIR = os.getenv("ALIGO_PREPARED_DIR")
CLIENT_CASES = sorted(Path(CLIENT_DIR).glob("client-day-*.json")) if CLIENT_DIR else []
CLIENT_CASES = [p for p in CLIENT_CASES if not p.name.endswith(".mapping.json")]


@pytest.mark.skipif(
    not CLIENT_CASES, reason="Set ALIGO_PREPARED_DIR to local prepared cases"
)
@pytest.mark.parametrize(
    "path", CLIENT_CASES or [None], ids=lambda p: p.name if p else "no-client-data"
)
def test_real_client_case_compatibility(path, client):
    payload = json.loads(path.read_text())
    response = client.post(URL, json=payload)
    assert response.status_code == 201, response.text
    cid = response.json()["case_id"]
    assert client.get(f"{URL}/{cid}").json()["submitted_case"] == payload
    investigated = client.post(f"{URL}/{cid}/investigate")
    assert investigated.status_code == 200, investigated.text
    result = investigated.json()
    verify_traceability(result["investigation_context"], result["report"])
    assert result["validation"]["ok"]

    assert result["report"]["review"]["status"] == "pending"
    assert client.get(f"{URL}/{cid}/export").json() == result
