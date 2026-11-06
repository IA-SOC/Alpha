# Automatic investigation and Gemini conversation

Accepting a valid case (`POST /api/v1/cases`) persists its evidence and a queued
analysis job in the same SQLite transaction. The backend worker starts the existing
LangGraph/MCP investigation and requests a Gemini second opinion. No frontend visit
is needed. Gemini receives case alerts even when there are no deterministic attack
hypotheses. It still acts as a second-opinion reviewer, rather than inventing a
confirmed attack when the deterministic engine found none.

## Configuration and startup

Install `requirements-dev.txt` for development. Set environment variables before
starting the process. A `.env` file is not loaded automatically by the application.

```powershell
$env:GEMINI_API_KEY = "your-key"
$env:GEMINI_MODEL = "your-available-gemini-model"
$env:SOC_AUTO_INVESTIGATE = "true"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Use one backend process per SQLite database. The worker and per-case locks operate
inside that process; a shared multi-worker deployment needs a separate job queue
and distributed locking. Pending jobs survive restart. Interrupted `running` jobs
return to `queued` at startup. Recovery is at least once: a crash after an external
API call can cause that call to be repeated. Completed jobs are not automatically
repeated. Cases stored before this update can be investigated explicitly.

`SOC_AUTO_INVESTIGATE=false` is an explicit manual/offline development mode. The
legacy tests select it before creating their session fixtures. Production defaults
to `true`; automatic investigations require Gemini regardless of `LLM_PROVIDER`.
`LLM_PROVIDER` still controls direct legacy graph calls in manual mode.

Missing credentials or failed Gemini calls produce an analysis error, even if a
usable deterministic report was saved. They never appear as successful Gemini
analysis. Error responses contain safe categories, not provider secrets.

## Endpoints

| Method and path (under `/api/v1/cases`) | Behavior |
| --- | --- |
| `POST /` (existing path without trailing slash) | Accept case and queue investigation; existing acceptance response is preserved. |
| `GET /{id}/analysis-status` | `queued`, `running`, `completed`, or `error`, with `error` category and `updated_at`. Older cases without a job return `not_started`. |
| `POST /{id}/investigate` | Wait for the active automatic run or reuse its completed result. |
| `POST /{id}/investigate?force=true` | Explicit rerun/retry. The frontend sends this only for deliberate retry/rerun actions. |
| `GET /{id}/chat-evidence` | Current case evidence catalog, including saved MCP investigation outputs. |
| `POST /{id}/messages` | Send an analyst message to Gemini; validate and persist the user/assistant pair atomically. |
| `GET /{id}/messages` | Ordered persisted conversation history for this case. |

Example message body (requires matching `X-Analyst-Id: isabella`):

```json
{
  "analyst_id": "isabella",
  "message": "What evidence supports the previous answer?",
  "evidence_refs": ["alert:ecs-auth-001"]
}
```

`evidence_refs` is optional. Select valid references from `chat-evidence`. MCP
references include the investigation run ID and expire after a rerun. Responses
contain `case_id` and a `message` with `role`, `content`, `evidence_refs`, and
`created_at`. Source pointers remain available in the evidence catalog.

The context includes case metadata, report summary/limitations/review state, the
last 20 stored messages, requested evidence, and up to 30 default evidence items.
Up to 20 references cited in recent turns are also kept when still valid. The full history remains queryable. Individual evidence strings are bounded and
untrusted instruction patterns are redacted. Oversized contexts are rejected
explicitly. MCP evidence comes from the saved case investigation; chat does not
query arbitrary cases or add external enrichment.

Input references are checked before calling Gemini. Output references must exist
in the exact context sent to the model. This validates reference membership, not
the semantic truth of a statement. A human analyst still evaluates conclusions.
Concurrent turns in one case are serialized with investigation/rerun operations.
A failed model call or invalid response does not leave a partial conversation turn.

Errors: missing case `404`; no investigation `409`; invalid input/reference `422`;
analyst header mismatch `403`; missing Gemini configuration `503`; model failure or
invalid model references `502`; timeout `504`. The existing analyst header is an
identity consistency check, not authentication or authorization. Access control
must be supplied by the deployment if cases belong to different users.

## Verification

```powershell
python -m pytest -q
python -m pytest tests/test_automatic_investigation.py tests/test_chat.py -q
```

Run the full suite from your Git checkout: the existing benchmark records `git HEAD` and requires Git metadata.

These tests use the real graph and MCP subprocesses for the automatic workflow,
with an in-memory Gemini double to avoid API cost and nondeterministic answers.
Chat tests cover multi-turn history, cross-case isolation, invalid input/output
references, persistence across restart, concurrent turns, configuration errors,
provider failure, and SDK request construction.

To verify actual connectivity, set a valid key and available model and run:

```powershell
python scripts/smoke_gemini.py
```

This opt-in script makes real API calls for one synthetic case without hypotheses
and two chat turns. It uses a temporary database and never submits client data.
It is not part of the automated suite and was not run without credentials.

Frontend conversation UI and labelled-case evaluation are outside this change.
