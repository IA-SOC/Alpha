---
tags: [agentsoc, backend, architecture]
aliases: [Backend, API, Intake API]
updated: 2026-10-11
---

# The backend

The backend is the **entry point and the coordinator** of the system. It receives cases over HTTP, validates them against the official contract, assigns an identifier and stores them. On request, it correlates the alerts, links IoC, runs the agent in the same process, verifies the output and saves it. It also resumes the agent with the analyst's decision.

> [!info] Where the code is
> `soc-ai-analyst-sprint2/app/`. Technical detail in `docs/SPRINT2_IMPLEMENTATION.md`; test results in `docs/VERIFICATION.md`.

## What it does and does not do

| Does | Does not |
| --- | --- |
| Receive cases at `POST /api/v1/cases` | Query IoC reputation (N8N does that) |
| Validate structure (Pydantic) and the contract's validation rules (VR-01 to VR-23) | Connect to live Elastic or Wazuh |
| Generate a UUID4 per accepted case | Change the stored original case |
| Store the original case unchanged (SQLite) | Run investigations in the background |
| Correlate alerts and link IoC (adapter) | Use an LLM |
| Run the agent and verify traceability | Authenticate users |
| Save the last result and resume review | Keep report history |

> [!warning] Authentication
> The API has **no authentication**. Do not expose it outside `127.0.0.1`.

## Endpoints

All `{case_id}` paths use the application **UUID**.

| Method and path | What it does | Responses |
| --- | --- | --- |
| `POST /api/v1/cases` | Validates and accepts a case. Unchanged from the original intake. | `201` accepted · `422` invalid · `409` duplicate submitted ID |
| `GET /api/v1/cases/{case_id}` | Returns the original accepted input. | `200` · `404` · `422` bad UUID |
| `GET /api/v1/cases/{case_id}/context` | Correlation and IoC evidence. **Does not run the agent.** | `200` · `404` |
| `POST /api/v1/cases/{case_id}/investigate` | Runs the agent and saves the result. Waits until done. | `200` · `404` · `502` failure · `504` timeout |
| `GET /api/v1/cases/{case_id}/investigation` | Last saved result, also after a restart. | `200` · `404` none yet |
| `POST /api/v1/cases/{case_id}/review` | Resumes the paused graph with `validated`, `corrected` or `rejected` plus analyst and notes. | `200` · `404` · `409` nothing to resume · `422` invalid decision |

Swagger UI at `http://127.0.0.1:8000/docs` while the server runs.

## Two identifiers per case

- `submitted_case_id`: the `case_id` the client sent (for example `SPRINT2-DEMO-001`). It must be unique (VR-04).
- `case_id`: the UUID4 the backend generates on acceptance. It is the one used in every other path.

The investigation adds a third: `run_id`, a new UUID per run, used as the graph `thread_id`.

## Pieces

| File | Responsibility |
| --- | --- |
| `app/main.py` | Builds the app, `CaseService` and `InvestigationService`; creates the database on start-up |
| `app/api/routes/cases.py` | `POST /cases` (unchanged) |
| `app/api/routes/investigations.py` | The five investigation routes and their error mapping |
| `app/schemas/case.py` | Contract models (unchanged) |
| `app/schemas/investigation.py` | Output models: evidence, relationships, correlation result, review decision |
| `app/services/case_service.py` | Semantic rules: native IDs, versions, references (unchanged) |
| `app/services/evidence.py` | Reads supported fields with JSON Pointers |
| `app/services/correlation.py` | Pairwise correlation. See [[16 Correlation engine]] |
| `app/services/ioc_integration.py` | IoC associations. See [[17 IoC integration and traceability]] |
| `app/services/agent_adapter.py` | Builds the agent input and `investigation_context` |
| `app/services/traceability.py` | Checks every evidence pointer against the original case |
| `app/services/investigation_service.py` | Runs the graph, keeps checkpoints and locks, saves results |
| `app/storage/case_store.py` | SQLite: `cases` and `investigations` tables |
| `app/core/config.py` | Settings from environment variables |

## Investigation flow inside the service

`InvestigationService.run(case_id)`:

1. Takes a per-case `asyncio.Lock`, so two investigations of the same case never overlap.
2. Builds the adapted case in a worker thread (`asyncio.to_thread`) so SQLite reads do not block the event loop.
3. Builds a fresh graph and `run_id`, and runs `investigate()` with `asyncio.wait_for(..., timeout=300)`.
4. If the skill validator failed, it raises an error, which the route turns into `502`.
5. Runs `verify_traceability`; a broken pointer also gives `502`.
6. Saves the result in SQLite and keeps `(graph, run_id)` in memory for review.

`review(case_id, decision)` checks that the graph is paused at `revision_humana`, resumes it, saves the updated result and then **drops the graph from memory** so reviewed cases do not leak.

## Persistence

| What | Where | After restart |
| --- | --- | --- |
| Accepted cases | `cases` (submitted ID, UUID, payload) | Kept |
| Last investigation result | `investigations` (UUID, result JSON) | Kept, readable via `GET /investigation` |
| Paused graphs (review checkpoints) | Memory | **Lost**: review returns `409` until a new investigation |

Reruns replace the last result and checkpoint. Report history is outside this sprint.

## Why a single worker

Review checkpoints and per-case locks live in one process's memory. With several Uvicorn workers, a review could reach a worker that never ran the investigation. Run `--workers 1`. A persistent checkpointer (see [[12.5 Persistence and performance]]) removes the first problem, not the second.

## Failures never lose the case

If the agent, an MCP server or a validator fails, the accepted case and its evidence stay in SQLite and `POST /investigate` can be retried. A successful retry starts a fresh graph. This is tested by injecting an MCP failure (`test_failure_retains_accepted_evidence_and_allows_retry`).

## Configuration

Read **once** at start-up. Restart the server to change them.

| Variable | Default | For what |
| --- | --- | --- |
| `MAX_ALERTS_PER_CASE` | `50` | Alert limit per case (higher values are not performance-certified) |
| `CASE_DATABASE_PATH` | `data/cases.sqlite3` | SQLite file |
| `ELASTIC_ALERT_ID_POINTER` | `/event/id` | Where the native ID is in Elastic `raw_alert` |
| `WAZUH_ALERT_ID_POINTER` | `/id` | Where the native ID is in Wazuh `raw_alert` |

The correlation window (300 s) is a constructor parameter of `InvestigationService`, not an environment variable. `AGENT_DIR` and `AGENT_PYTHON` from the previous version **no longer exist**.

## Start it

```powershell
cd "C:\Users\Caliche\Documents\UTP\Implentde prueba\SOC_AI_Analyst_Sprint2_Integrated\soc-ai-analyst-sprint2"
.venv\Scripts\Activate.ps1
python -m pytest -q                     # 184 tests
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Next: [[16 Correlation engine]] · Back to [[00 Home]]
