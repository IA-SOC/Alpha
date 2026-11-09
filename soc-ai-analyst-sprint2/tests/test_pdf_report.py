from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.pdf_report import build_investigation_pdf


def _result(case_id):
    return {
        "case_id": str(case_id),
        "report": {
            "generated_at": "2026-11-09T14:00:00Z",
            "hypotheses": [
                {
                    "rank": 1,
                    "statement": "Suspicious authentication activity",
                    "confidence": "media",
                    "evidence_for": [{"alert_id": "alert-1"}],
                    "evidence_against": [{"alert_id": "alert-2"}],
                    "unknowns": ["Source user is not confirmed"],
                }
            ],
            "attack_mapping": [
                {
                    "tactic": "Credential Access",
                    "technique_id": "T1110",
                    "technique_name": "Brute Force",
                    "status": "candidate",
                    "evidence": [{"alert_id": "alert-1"}],
                }
            ],
            "review": {
                "status": "corrected",
                "analyst": "analyst-a",
                "notes": "Reviewed evidence",
                "findings": [
                    {
                        "finding_key": "hypothesis-1",
                        "status": "validated",
                        "notes": "Evidence is sufficient",
                    }
                ],
            },
        },
    }


def test_pdf_contains_report_sections():
    pdf = build_investigation_pdf(_result(uuid4()))

    assert pdf.startswith(b"%PDF-")
    assert b"%%EOF" in pdf
    assert len(pdf) > 1000


def test_pdf_export_returns_downloadable_pdf(tmp_path):
    case_id = uuid4()
    app = create_app(database_path=tmp_path / "cases.sqlite3")
    with TestClient(app) as client:
        app.state.investigation_service.store.save_investigation(
            case_id, _result(case_id)
        )
        response = client.get(f"/api/v1/cases/{case_id}/export/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        f'attachment; filename="investigation-{case_id}.pdf"'
    )
    assert response.content.startswith(b"%PDF-")


def test_pdf_export_requires_saved_investigation(client):
    response = client.get(f"/api/v1/cases/{uuid4()}/export/pdf")

    assert response.status_code == 404
