from copy import deepcopy
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


def _saved_result(case_id):
    return {
        "case_id": str(case_id),
        "run_id": "initial-run",
        "revision": 1,
        "report": {"review": {"status": "pending"}},
        "report_markdown": "initial",
        "audit_log": [],
    }


def test_instruction_endpoint_requires_matching_analyst_header(tmp_path):
    app = create_app(database_path=tmp_path / "cases.sqlite3")
    case_id = uuid4()
    app.state.investigation_service.store.get_by_id = lambda _: object()
    with TestClient(app) as client:
        app.state.investigation_service.store.save_investigation(
            case_id, _saved_result(case_id)
        )
        response = client.post(
            f"/api/v1/cases/{case_id}/instructions",
            headers={"X-Analyst-Id": "analyst-a"},
            json={
                "analyst_id": "analyst-b",
                "instruction": "Focus on the affected server",
                "revision": 1,
            },
        )
    assert response.status_code == 403


def test_instruction_persists_follow_up_and_rejects_stale_revision(tmp_path):
    app = create_app(database_path=tmp_path / "cases.sqlite3")
    case_id = uuid4()
    service = app.state.investigation_service
    initial = _saved_result(case_id)
    service.store.get_by_id = lambda _: object()

    async def fake_run(case, guidance):
        result = deepcopy(initial)
        result["run_id"] = "follow-up-run"
        result["report"]["analyst_guidance"] = guidance
        return result

    service._run_unlocked = fake_run
    with TestClient(app) as client:
        service.store.save_investigation(case_id, initial)
        response = client.post(
            f"/api/v1/cases/{case_id}/instructions",
            headers={"X-Analyst-Id": "analyst-a"},
            json={
                "analyst_id": "analyst-a",
                "instruction": "Focus on the affected server",
                "context": "The server hosts the finance application",
                "feedback": "The previous scope was too broad",
                "revision": 1,
            },
        )
        assert response.status_code == 200, response.text
        updated = response.json()
        assert updated["revision"] == 2
        assert updated["instruction_history"][0]["analyst_id"] == "analyst-a"
        assert updated["report"]["analyst_guidance"]["instruction"].startswith(
            "Focus"
        )

        stale = client.post(
            f"/api/v1/cases/{case_id}/instructions",
            headers={"X-Analyst-Id": "analyst-a"},
            json={
                "analyst_id": "analyst-a",
                "instruction": "Retry with stale state",
                "revision": 1,
            },
        )
        assert stale.status_code == 409

    assert service.store.get_investigation(case_id)["revision"] == 2
