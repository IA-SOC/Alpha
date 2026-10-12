from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.schemas.case import IncidentCase
from app.schemas.errors import CaseValidationError
from app.services.case_service import CaseService
from app.storage.case_store import CaseStore
from tests.helpers import make_case


def test_concurrent_duplicate_submissions_only_allocate_one_id(tmp_path):
    factory = Mock(wraps=uuid4)
    store = CaseStore(tmp_path / "cases.sqlite3")
    store.initialize()
    service = CaseService(Settings(), store, factory)
    case = IncidentCase.model_validate(make_case())

    def submit():
        try:
            return service.accept(case).case_id
        except CaseValidationError as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: submit(), range(8)))
    assert results.count(409) == 7
    factory.assert_called_once()


def test_identifier_factory_runs_only_after_validation(tmp_path):
    value = uuid4()
    factory = Mock(return_value=value)
    store = CaseStore(tmp_path / "cases.sqlite3")
    store.initialize()
    service = CaseService(Settings(), store, factory)
    accepted = service.accept(IncidentCase.model_validate(make_case()))
    assert accepted.case_id == value
    assert accepted.submitted_case.case_id == "INC-TEST-001"
    factory.assert_called_once_with()


def test_restart_preserves_evidence_and_submitted_id_uniqueness(tmp_path):
    path = tmp_path / "cases.sqlite3"
    payload = make_case()
    payload["alerts"][0]["raw_alert"]["custom"] = {"items": [None, True, 7]}
    with TestClient(create_app(database_path=path)) as first:
        accepted = first.post("/api/v1/cases", json=payload)
        assert accepted.status_code == 201

    restarted = create_app(database_path=path)
    factory = Mock(wraps=uuid4)
    restarted.state.case_service.id_factory = factory
    with TestClient(restarted) as second:
        duplicate = second.post("/api/v1/cases", json=payload)
        assert duplicate.status_code == 409
        assert "case_id" not in duplicate.json()
        assert duplicate.json()["detail"][0]["rule"] == "VR-04"
        factory.assert_not_called()
        saved = restarted.state.case_service.store.get(payload["case_id"])
        assert str(saved.case_id) == accepted.json()["case_id"]
        assert saved.submitted_case.model_dump(exclude_unset=True) == payload
