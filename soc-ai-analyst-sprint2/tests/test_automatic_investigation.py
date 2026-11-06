
import time
from copy import deepcopy
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from agent import llm
from app.main import create_app
from tests.test_correlation_engine import case_for, event


def wait_status(client, case_id, expected):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        result = client.get(f"/api/v1/cases/{case_id}/analysis-status").json()
        if result["status"] in expected:
            return result
        time.sleep(0.02)
    raise AssertionError(result)


@pytest.fixture
def provider(monkeypatch):
    calls = []

    class GeminiDouble:
        name = "gemini"
        model = "test"

        def review(self, context):
            calls.append(deepcopy(context))
            return llm.MockProvider().review(context)

    monkeypatch.setattr(llm, "get_provider", lambda *args: GeminiDouble())
    return calls


@pytest.mark.parametrize("attack", [False, True])
def test_acceptance_runs_gemini_with_or_without_hypotheses(
    tmp_path, monkeypatch, provider, attack
):
    monkeypatch.setenv("SOC_AUTO_INVESTIGATE", "true")
    app = create_app(database_path=tmp_path / "cases.sqlite3")
    alert = event("a")
    if attack:
        alert["raw_alert"]["tags"] = ["brute_force"]
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/cases", json=case_for(alert).model_dump(exclude_unset=True)
        )
        assert response.status_code == 201
        case_id = response.json()["case_id"]
        assert (
            wait_status(client, case_id, {"completed", "error"})["status"]
            == "completed"
        )
        assert len(provider) == 1
        assert provider[0]["alerts"][0]["id"] == "a"
        assert bool(provider[0]["hypotheses"]) == attack
        assert client.post(f"/api/v1/cases/{case_id}/investigate").status_code == 200
        assert len(provider) == 1
        assert (
            client.post(f"/api/v1/cases/{case_id}/investigate?force=true").status_code
            == 200
        )
        assert len(provider) == 2
        assert (
            client.post(
                "/api/v1/cases", json=case_for(alert).model_dump(exclude_unset=True)
            ).status_code
            == 409
        )
        assert len(provider) == 2


def test_failure_records_safe_error_and_worker_continues(
    tmp_path, monkeypatch, provider
):
    monkeypatch.setenv("SOC_AUTO_INVESTIGATE", "true")
    app = create_app(database_path=tmp_path / "cases.sqlite3")
    service = app.state.investigation_service
    real_context = service.context
    failed = set()

    def context(case_id):
        if not failed:
            failed.add(case_id)
            raise RuntimeError("secret provider key should never be returned")
        return real_context(case_id)

    monkeypatch.setattr(service, "context", context)
    with TestClient(app) as client:
        first = client.post(
            "/api/v1/cases", json=case_for(event("a")).model_dump(exclude_unset=True)
        ).json()["case_id"]
        status = wait_status(client, first, {"error"})
        assert status["error"] == "RuntimeError"
        assert client.get(f"/api/v1/cases/{first}").status_code == 200
        case = case_for(event("b"))
        case.case_id = "next-case"
        second = client.post(
            "/api/v1/cases", json=case.model_dump(exclude_unset=True)
        ).json()["case_id"]
        assert (
            wait_status(client, second, {"completed", "error"})["status"] == "completed"
        )
        assert len(provider) == 1


def test_restart_recovers_pending_and_interrupted_jobs(tmp_path, monkeypatch, provider):
    path = tmp_path / "cases.sqlite3"
    app = create_app(database_path=path)
    with TestClient(app) as client:
        case_id = client.post(
            "/api/v1/cases", json=case_for(event("a")).model_dump(exclude_unset=True)
        ).json()["case_id"]
        app.state.investigation_service.store.set_analysis_status(
            UUID(case_id), "running"
        )
    monkeypatch.setenv("SOC_AUTO_INVESTIGATE", "true")
    with TestClient(create_app(database_path=path)) as client:
        assert (
            wait_status(client, case_id, {"completed", "error"})["status"]
            == "completed"
        )
    with TestClient(create_app(database_path=path)) as client:
        assert (
            client.get(f"/api/v1/cases/{case_id}/analysis-status").json()["status"]
            == "completed"
        )
        assert len(provider) == 1


def test_unconfigured_gemini_records_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("SOC_AUTO_INVESTIGATE", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with TestClient(create_app(database_path=tmp_path / "cases.sqlite3")) as client:
        case_id = client.post(
            "/api/v1/cases", json=case_for(event("a")).model_dump(exclude_unset=True)
        ).json()["case_id"]
        assert wait_status(client, case_id, {"error"})["error"] == "ProviderUnavailable"
        assert (
            client.get(f"/api/v1/cases/{case_id}/investigation").json()["report"][
                "model_review"
            ]["status"]
            == "unavailable"
        )
