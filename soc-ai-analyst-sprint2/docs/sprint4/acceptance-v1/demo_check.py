"""#69: isolated real-HTTP demo plus review/export and negative intake checks.

Reuses demo/run_pipeline.py; raw synthetic outputs stay in this folder's ignored
run/ directory. Commit only the compact result record after an executed run.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[3]


def main():
    sys.path.insert(0, str(ROOT))
    from app.services.finding_review import finding_keys
    from demo.run_pipeline import request

    output = Path(__file__).resolve().parent / "run"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp, socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        base = f"http://127.0.0.1:{port}"
        with (output / "server.log").open("w", encoding="utf-8") as log:
            server = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--workers",
                    "1",
                ],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                env={
                    **os.environ,
                    "LLM_PROVIDER": "none",
                    "CASE_DATABASE_PATH": str(Path(tmp) / "cases.sqlite3"),
                },
            )
            try:
                for _ in range(100):
                    if server.poll() is not None:
                        raise RuntimeError("Server stopped; see run/server.log")
                    try:
                        with urlopen(base + "/openapi.json", timeout=1):
                            break
                    except (URLError, TimeoutError):
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Server did not become ready")
                subprocess.run(
                    [
                        sys.executable,
                        "demo/run_pipeline.py",
                        "--base-url",
                        base,
                        "--output-dir",
                        str(output),
                    ],
                    cwd=ROOT,
                    check=True,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                )
                summary = json.loads((output / "summary.json").read_text())
                prefix = f"/api/v1/cases/{summary['case_id']}"
                _, result = request(base, prefix + "/investigation")
                submitted = json.loads((output / "submitted_case.json").read_text())
                codes = {}
                for label, payload, expected in (
                    ("duplicate", submitted, 409),
                    ("invalid", {"case_id": "invalid"}, 422),
                ):
                    try:
                        request(base, "/api/v1/cases", payload)
                        raise AssertionError(f"{label} accepted unexpectedly")
                    except HTTPError as exc:
                        assert exc.code == expected
                        codes[label] = exc.code
                decision = {
                    "run_id": result["run_id"],
                    "status": "corrected",
                    "analyst": "Acceptance automation",
                    "notes": "Synthetic demo only; no client sign-off implied.",
                    "findings": [
                        {
                            "finding_key": key,
                            "status": "rejected",
                            "notes": "Candidate evidence is not attack confirmation.",
                        }
                        for key in finding_keys(result["report"])
                    ],
                }
                status, reviewed = request(base, prefix + "/review", decision)
                assert status == 200 and reviewed["status"] == "corrected"
                assert reviewed["report"]["review"]["findings"] == decision["findings"]
                assert (
                    reviewed["report"]["hypotheses"] == result["report"]["hypotheses"]
                )
                _, exported = request(base, prefix + "/export")
                assert exported == reviewed
                assert [a["phase"] for a in reviewed["audit_log"]] == [1, 2, 3, 4, 5, 6]
                # Reproduce #89's unresolved exclusion requirement using fake data.
                # This is an observed gap, never a successful redaction assertion.
                submitted["case_id"] += "-credential-probe"
                marker = "ACCEPTANCE-SYNTHETIC-SECRET"
                submitted["alerts"][0]["raw_alert"]["password"] = marker
                _, probe = request(base, "/api/v1/cases", submitted)
                probe_path = f"/api/v1/cases/{probe['case_id']}"
                request(base, probe_path + "/investigate", {})
                _, probe_export = request(base, probe_path + "/export")
                credential_present = (
                    probe_export["investigation_context"]["original_case"]["alerts"][0][
                        "raw_alert"
                    ].get("password")
                    == marker
                )
                record = {
                    **summary,
                    "negative_intake_http": codes,
                    "review_http": status,
                    "review_status": reviewed["status"],
                    "finding_decisions": len(decision["findings"]),
                    "export_matches_saved_review": True,
                    "audit_phases": [a["phase"] for a in reviewed["audit_log"]],
                    "hypotheses_unchanged_by_review": True,
                    "model_provider": "none",
                    "browser_verified": False,
                    "known_gaps": {
                        "export_includes_synthetic_password": credential_present
                    },
                }
                (output / "acceptance-summary.json").write_text(
                    json.dumps(record, indent=2) + "\n", encoding="utf-8"
                )
                print(json.dumps(record, indent=2))
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


if __name__ == "__main__":
    main()
