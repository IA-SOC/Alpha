from copy import deepcopy
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers import make_case


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
    messages = service.store.get_messages(case_id)
    assert [(message.role, message.revision) for message in messages] == [
        ("user", 2),
        ("assistant", 2),
    ]
    assert messages[0].content == "Focus on the affected server"
    revisions = service.store.get_revisions(case_id)
    assert [revision.revision for revision in revisions] == [1, 2]


def test_messages_and_revisions_are_available_after_restart(tmp_path):
    path = tmp_path / "cases.sqlite3"
    app = create_app(database_path=path)
    with TestClient(app) as client:
        case_id = client.post(
            "/api/v1/cases", json=make_case(case_id="chat-case")
        ).json()["case_id"]
    case_uuid = UUID(case_id)
    service = app.state.investigation_service
    service.store.initialize()
    service.store.save_investigation(case_uuid, _saved_result(case_uuid))
    service.store.save_instruction_revision(
        case_uuid,
        1,
        {
            **_saved_result(case_uuid),
            "revision": 2,
            "run_id": "follow-up-run",
        },
        ("Review the evidence", "The evidence supports the saved findings."),
    )
    with TestClient(create_app(database_path=path)) as client:
        messages = client.get(f"/api/v1/cases/{case_id}/messages")
        revisions = client.get(f"/api/v1/cases/{case_id}/revisions")

    assert messages.status_code == 200
    assert revisions.status_code == 200
    assert [item["role"] for item in messages.json()] == ["user", "assistant"]
    assert [item["revision"] for item in messages.json()] == [2, 2]
    assert [item["revision"] for item in revisions.json()] == [1, 2]
