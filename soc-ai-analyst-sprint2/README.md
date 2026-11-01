# SOC AI Analyst — integrated Sprint 2

Runnable FastAPI, SQLite and LangGraph/MCP increment for US1, US2 and US3.
It accepts the unchanged Incident Case Input Specification v1.0, stores original
cases, correlates alerts, associates supplied IoC intelligence and runs the
existing investigation agent through report validation and human review.

The historical Sprint 2 record verified 18 of 19 tasks. For Sprint 4, Aligo has
supplied SIEM samples and confirmed that their format is the reference for
enrichment. The explicit [US3 Wazuh VT/MISP adapter](docs/sprint4/US3-SIEM-enrichment.md)
maps selected records to input v1.0; it does not establish n8n provenance or live
Elastic/Wazuh connectivity. See its separate verification record for current results.

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

## Segunda opinión opcional del modelo

Por defecto `LLM_PROVIDER=none`: el reporte permanece solo determinista.
Copie `.env.example` a `.env`, defina `LLM_PROVIDER=gemini` y configure
`GEMINI_API_KEY` únicamente en el entorno; nunca la guarde en el repositorio.
`GEMINI_MODEL` usa `gemini-3.8-flash` y `LLM_TIMEOUT_SECONDS` usa 30 por defecto.
La revisión no altera hipótesis, confianza, técnicas ni acciones; se añade como
`model_review`. El MCP local `guard` reduce, sanea y valida los datos y citas
antes y después de la llamada al proveedor.

## Contexto almacenado de solo lectura (US18)

El MCP `context` (`servers/context_server.py`) consulta IoC pre-enriquecidos y
casos anonimizados ya almacenados; nunca escribe ni consulta proveedores de
enriquecimiento. Abre la base SQLite con `mode=ro`, así que tampoco la crea.
Ruta: `CONTEXT_DB_PATH` o `data/context/context.sqlite3`. El esquema esperado
es `SCHEMA` en `core/context_store.py` (tablas `iocs`, `cases`, `case_iocs`).

| Tool | Argumentos | Devuelve |
|---|---|---|
| `lookup_iocs` | `value`, `observable_type` opcional | `{status, iocs}` |
| `lookup_case` | `case_id` | `{status, case, iocs}` |

`status` es `ok`, `not_found` (caso inexistente) o `unavailable` (base ausente
o con otro esquema, con `error`). Cada IoC conserva `provider`, `raw_verdict`,
`raw_result` y `enriched_at` tal como se almacenaron, más `source` con base,
tabla, `record_id` y `source_ref`. Se devuelven como máximo 100 registros,
ordenados por `record_id`; la búsqueda por observable es por valor exacto.

The prototype database is created by the write-side importer, not by the MCP:

```bash
python scripts/import_context.py \
  --iocs data/context/fixtures/iocs.json \
  --cases data/context/fixtures/cases.json
```

The importer validates all records and relationships before writing, preserves
provider verdicts and raw results (including provider errors), and records
deterministic source references. It uses the exact `SCHEMA` from
`core/context_store.py`; rerunning an import with existing IDs is rejected
instead of merging or overwriting records. The default output is
`data/context/context.sqlite3`, which is ignored as a generated local artifact.

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

## Reports for technical and non-technical readers

New agent investigations include `report.audience_sections` and a two-part
`report_markdown`. The rule-based formatter uses English headings and narrative,
preserves original-language evidence and refreshes both sections after human
review. Existing report fields and older report rendering remain supported.
The blast-radius output deduplicates observed hosts, users and source/destination
IP entities under `report.blast_radius.observed_entities`; each entity retains
the alert IDs that support it.
See [issue #66's contract and integration](docs/sprint4/US19-issue-66-report-formatter.md).

## Analyst follow-up interface

```json
{"type":"mark_legitimate","alert_ids":["alert-id"],"analyst":"name","note":"optional text"}
```

Use `agent.follow_up.run_follow_up(case, previous_report, instruction, thread_id, app=None)`.
It runs one bounded deterministic follow-up; the original case and report are never modified.

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
| `GET /api/v1/cases/{case_id}/report` | Saved report, dual-audience sections and rendered Markdown |
| `POST /api/v1/cases/{case_id}/instructions` | Run one audited analyst-guided follow-up using the expected revision |
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

Analyst-guided follow-ups require the current `revision` and matching
`X-Analyst-Id` header. The response increments the revision and stores the
instruction in `instruction_history`; stale revisions are rejected with 409.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/cases/RETURNED_UUID/instructions \
  -H 'Content-Type: application/json' \
  -H 'X-Analyst-Id: demo-analyst' \
  -d '{"analyst_id":"demo-analyst","instruction":"Focus on the affected host", "revision":1}'
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
