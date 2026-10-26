# SOC AI Analyst — integrated Sprint 2

Runnable FastAPI, SQLite and LangGraph/MCP increment for US1, US2 and US3.
It accepts the unchanged Incident Case Input Specification v1.0, stores original
cases, correlates alerts, associates supplied IoC intelligence and runs the
existing investigation agent through report validation and human review.

**18 of 19 Sprint 2 tasks are verified.** The N8N-specific input task remains
IN PROGRESS because actual customer output samples were not supplied. No
production N8N compatibility or live Elastic/Wazuh integration is claimed.

## Install and run

Use Python 3.12. From this directory:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Windows PowerShell activation: `.venv\Scripts\Activate.ps1`.
Application-only dependencies are in `requirements.txt`. No API key, external
database, SIEM access, intelligence subscription or LLM download is needed.
MCP servers start as local stdio subprocesses with the same Python interpreter.
Open `http://127.0.0.1:8000/docs` for the API.

## Complete demonstration

```bash
python demo/verify_local.py
```

This starts a temporary local Uvicorn server and SQLite database, submits the
synthetic mixed-source case over real HTTP and asserts the results. Evidence is
saved in `demo/output/`: submitted JSON, acceptance response, investigation JSON,
Markdown report, summary and server log. The temporary server/database are
removed on exit. Included output is a verified run, not a hand-authored example.
Every execution uses a new submitted ID to respect duplicate-submission checks.

For a server already running:

```bash
python demo/run_pipeline.py --base-url http://127.0.0.1:8000
```

Expected: 4 alerts, 6 pairs (1 related, 2 uncertain, 3 unrelated), one noise
candidate (`ecs-noise-003`), 3 IoC items, valid report and `pending_review`.
The report's conclusions remain candidates.

## API

All `{case_id}` paths use the **application UUID returned by intake**, not the
submitted external ID.

| Method and path | Result |
| --- | --- |
| `POST /api/v1/cases` | Unchanged v1.0 validation, SQLite acceptance, UUID; 201 |
| `GET /api/v1/cases/{case_id}` | Original accepted input |
| `GET /api/v1/cases/{case_id}/context` | Correlation and IoC evidence; no agent subprocess |
| `POST /api/v1/cases/{case_id}/investigate` | Run the existing agent and save its result |
| `GET /api/v1/cases/{case_id}/investigation` | Last saved investigation, including its timeline, ATT&CK metadata/evidence, hypotheses and IoC context after restart |
| `POST /api/v1/cases/{case_id}/review` | Resume the live human-review checkpoint |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/cases \
  -H 'Content-Type: application/json' --data-binary @examples/sprint2_demo.json
```

Copy its returned UUID into these requests:

```bash
curl http://127.0.0.1:8000/api/v1/cases/RETURNED_UUID/context
curl -X POST http://127.0.0.1:8000/api/v1/cases/RETURNED_UUID/investigate
curl -X POST http://127.0.0.1:8000/api/v1/cases/RETURNED_UUID/review \
  -H 'Content-Type: application/json' \
  -d '{"status":"validated","analyst":"demo-analyst","notes":"Evidence reviewed."}'
```

Use `curl.exe` on Windows if PowerShell maps `curl` to another command.
Review also accepts `corrected` and `rejected`. As in the supplied agent,
`corrected` records status and notes; it does not rewrite individual findings.
No case closure or response action is executed.

Investigation failures do not remove an accepted case; the submitted input
remains available and the investigation can be retried. Before saving a report,
the backend checks alert references and evidence pointers against the original
accepted case.

## Documentation

- [Technical implementation and limitations](docs/SPRINT2_IMPLEMENTATION.md)
- [Executed tests and demonstration](docs/VERIFICATION.md)
- [Backlog row-by-row evidence](docs/BACKLOG_VERIFICATION.md)
- [Added and modified files](docs/CHANGES.md)
- [Authoritative DOCX](docs/Incident_Case_Input_Specification_v1.0.docx)
- [Unchanged JSON Schema](docs/incident-case-input-v1.0.schema.json)

Original READMEs are retained in `docs/INTAKE_ORIGINAL.md` and
`docs/AGENT_ORIGINAL.md`. This README supersedes their integration-status text.
Existing agent samples, CLI, MITRE rules, MCP servers and report validator remain
available in their original relative paths.

## Prototype limits

SQLite retains accepted inputs and the last successful report. Review checkpoints
remain in memory: after restart, old reports can be read, but review returns 409
until a new investigation runs. Rerunning replaces the last report and checkpoint.
Use one worker. Unknown custom fields are preserved; interpreting unknown decoders
requires verified mappings. No provider verdict is invented and no external
intelligence query is performed. The supplied agent remains deterministic with
its original catalog limitations. This is a local synthetic prototype without
authentication or production deployment configuration.
