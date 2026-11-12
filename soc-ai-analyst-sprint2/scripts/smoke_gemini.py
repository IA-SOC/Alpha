
import os
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import create_app


def main():
    if not os.getenv("GEMINI_API_KEY") or not os.getenv("GEMINI_MODEL"):
        raise SystemExit(
            "Set GEMINI_API_KEY and GEMINI_MODEL in your environment first"
        )
    os.environ["SOC_AUTO_INVESTIGATE"] = "true"
    payload = {
        "schema_version": "1.0",
        "case_id": f"live-smoke-{uuid4()}",
        "submitted_at": "2026-11-06T12:00:00Z",
        "alerts": [
            {
                "alert_id": "smoke-a",
                "source_system": "elastic",
                "raw_alert": {
                    "event": {"id": "smoke-a"},
                    "@timestamp": "2026-11-06T12:00:00Z",
                    "host": {"name": "synthetic-host"},
                },
            }
        ],
    }
    with tempfile.TemporaryDirectory() as directory:
        with TestClient(
            create_app(database_path=Path(directory) / "smoke.sqlite3")
        ) as client:
            accepted = client.post("/api/v1/cases", json=payload)
            assert accepted.status_code == 201, "Synthetic case was rejected"
            base = f"/api/v1/cases/{accepted.json()['case_id']}"
            deadline = time.monotonic() + 330
            while time.monotonic() < deadline:
                status = client.get(base + "/analysis-status").json()
                if status["status"] in {"completed", "error"}:
                    break
                time.sleep(0.25)
            assert status["status"] == "completed", (
                f"Investigation: {status['status']} ({status.get('error')})"
            )
            for message in (
                "Summarize the available evidence",
                "What is missing to confirm your previous answer?",
            ):
                response = client.post(
                    base + "/messages",
                    headers={"X-Analyst-Id": "smoke"},
                    json={"analyst_id": "smoke", "message": message},
                )
                assert response.status_code == 200, (
                    f"Chat failed: HTTP {response.status_code}"
                )
            assert len(client.get(base + "/messages").json()["messages"]) == 4
            print("PASS: automatic Gemini investigation and two real chat turns")


if __name__ == "__main__":
    main()
