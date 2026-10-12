# SOC AI Analyst — incident case intake

Runnable FastAPI backend for Aligo Defensores Informáticos. It receives, validates
and identifies incident cases. Accepted input is retained locally for a future
investigation pipeline. No investigation is executed.

The authoritative input contract is
[`SOC AI Analyst – Incident Case Input Specification v1.0`](docs/Incident_Case_Input_Specification_v1.0.docx).
Its original JSON Schema is included unchanged in
[`docs/incident-case-input-v1.0.schema.json`](docs/incident-case-input-v1.0.schema.json).
Implementation choices and remaining assumptions are listed below.

## Run locally

Python 3.12 is the tested runtime. From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
pytest
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

On Windows, activate with `.venv\Scripts\Activate.ps1` in PowerShell. Application
dependencies alone can be installed with `requirements.txt`.

Open `http://127.0.0.1:8000/docs` for Swagger UI or `/openapi.json` for the effective
API schema. One worker is sufficient for this prototype.
For a future container, the same entry point can bind to `0.0.0.0`; configuration
comes from environment variables. Keep the SQLite file on a persistent volume if
cases must survive container replacement. This delivery does not deploy a container.

## Submit a case

`POST /api/v1/cases` accepts `Content-Type: application/json`.

```bash
curl -i http://127.0.0.1:8000/api/v1/cases \
  -H 'Content-Type: application/json' \
  --data-binary @examples/elastic.json
```

Minimal valid request for the included synthetic Elastic identifier profile:

```json
{
  "schema_version": "1.0",
  "case_id": "INC-DEMO-001",
  "submitted_at": "2026-09-29T20:30:00Z",
  "alerts": [
    {
      "alert_id": "native-event-001",
      "source_system": "elastic",
      "raw_alert": {
        "event": {"id": "native-event-001"},
        "customer_custom_field": {"action": "blocked"}
      }
    }
  ]
}
```

Example response, **201 Created**; the UUID varies on every acceptance:

```json
{
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "submitted_case_id": "INC-DEMO-001",
  "status": "accepted"
}
```

The request `case_id` remains mandatory under the existing specification. **Design
decision:** it is preserved as the submitted identifier; the response `case_id` is
the newly generated application UUID4. `submitted_case_id` makes that distinction
explicit. The original request envelope is retained without rewriting its ID.

Invalid request with `case_id` missing:

```json
{
  "schema_version": "1.0",
  "submitted_at": "2026-09-29T20:30:00Z",
  "alerts": [
    {
      "alert_id": "wazuh-event-001",
      "source_system": "wazuh",
      "raw_alert": {"id": "wazuh-event-001"}
    }
  ]
}
```

Response, **422 Unprocessable Entity**:

```json
{
  "detail": [
    {
      "rule": "VR-03",
      "loc": ["body", "case_id"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

Validation errors include the rule, JSON field path, reason and error type. No UUID
is generated or returned for a rejected submission. The error handler omits the
submitted payload from error responses. `JSON` identifies malformed JSON;
`CONTRACT` identifies structural constraints without a dedicated VR number.

| HTTP status | Behavior |
| --- | --- |
| 201 | Entire case accepted; generated UUID4 returned. |
| 422 | Invalid JSON, structural validation or semantic case validation failure. |
| 409 | Submitted `case_id` already exists in the case store (VR-04). |

There is no partial acceptance, silent truncation, update or idempotent retry
behavior. A retry using an already accepted submitted ID returns 409. Using one
native alert in two different cases is permitted by the specification.

## Architecture and files

One FastAPI application, divided by responsibility. The route accepts a Pydantic
model and calls the case service. The service checks semantic rules, then asks the
store to check submitted-ID uniqueness and allocate the UUID atomically. SQLite
uses Python's standard library and runs in the same application process; no database
server or ORM is required. A future store can replace it without changing the route.

All files below were **created** in this backend directory. No pre-existing backend
repository was found in the supplied project files, and no existing project files
were modified. The DOCX is a reference copy; its contents were not edited.

| Path | Responsibility |
| --- | --- |
| `app/main.py` | App factory, service wiring and error-handler registration. |
| `app/api/routes/cases.py` | Thin `POST /api/v1/cases` route. |
| `app/api/errors.py` | Consistent, payload-free 422/409 responses. |
| `app/schemas/case.py` | Input, alert, correlation, enrichment and response models. |
| `app/schemas/errors.py` | Validation issue and error-response types. |
| `app/services/case_service.py` | Alert-ID provenance/uniqueness, version and reference checks. |
| `app/storage/case_store.py` | Atomic submitted-ID uniqueness and local SQLite accepted-case storage. |
| `app/core/config.py` | Initial alert limit, native-ID pointers and version support profile. |
| `app/core/ids.py` | Isolated `uuid.uuid4()` generator, injectable in tests. |
| `tests/conftest.py`, `tests/helpers.py` | Isolated app, mock generator and synthetic fixtures. |
| `tests/test_cases.py` | Intake API acceptance, rejection and preservation tests. |
| `tests/test_service.py` | Concurrent duplicate acceptance, restart persistence and injected ID factory tests. |
| `tests/test_configuration.py` | Startup configuration and synchronized OpenAPI limit tests. |
| `tests/test_contract.py` | Shipped examples against the authoritative schema and API. |
| `examples/elastic.json`, `examples/wazuh.json`, `examples/mixed.json` | Synthetic valid examples from the specification. |
| `examples/invalid_missing_case_id.json` | Reproducible invalid request. |
| `docs/Incident_Case_Input_Specification_v1.0.docx` | Authoritative specification reference copy. |
| `docs/incident-case-input-v1.0.schema.json` | Original Draft 2020-12 schema, initial 50-alert profile. |
| `docs/VERIFICATION.md` | Actual test and startup results. |
| `requirements.txt`, `requirements-dev.txt` | Pinned direct application/test dependencies. |
| `pyproject.toml`, `.gitignore`, `README.md` | Test/lint configuration, exclusions and usage. |

Package markers `__init__.py` are also included in `app/`, `app/api/`,
`app/api/routes/`, `app/schemas/`, `app/services/`, `app/storage/`, `app/core/` and
`tests/`. Virtual environments and generated caches are excluded from delivery.

## Validation contract

**Structural validation — Pydantic:**

- Required case fields: `schema_version`, `case_id`, `submitted_at`, `alerts`.
- Required alert fields: `alert_id`, `source_system`, `raw_alert`.
- Schema version `1.0`; nonblank identifiers; RFC 3339 submission timestamp with
  timezone; a nonempty alerts array up to the configured maximum (initially 50).
- Origins are exactly `elastic` or `wazuh`; mixed cases are accepted. Wazuh data
  stored in Elasticsearch remains Wazuh-originated.
- `raw_alert` is a nonempty object with arbitrary JSON fields, including custom
  nested fields. `raw_result`, when supplied, is an arbitrary object and may be empty.
- Application-owned envelopes, wrappers, correlation, enrichment and observable
  objects forbid unknown fields, as specified. Customer fields belong inside the
  extensible native objects. JSON values are not coerced into other types.
- Optional fields may be absent; explicit `null` is rejected where the contract
  declares a non-null type. Nested null values in raw objects are retained.
- `source_version` and `ecs_version` follow the specification's syntax patterns.
- Correlation requires nonempty, distinct, nonblank `fields`. Enrichments require
  `provider` and an observable with `type` and `value`. Supplied alert-reference
  lists must be nonempty, distinct and contain nonblank strings.

**Semantic validation — service/store:**

- Submitted case IDs are unique in the SQLite store, including after restart (VR-04).
- Wrapper `alert_id` equals the native string ID at the configured source pointer
  (VR-10). IDs are compared exactly, without trimming, prefixing or replacement.
- Alert IDs are unique within a case, including across different origins (VR-11).
- Optional versions match the support profile: Elastic 8.19 or 9.4, Wazuh 4.14,
  including numeric patch suffixes; ECS major 8 (VR-19/20). Unknown versions are
  not inferred. Elasticsearch 9.4 does not imply ECS 9.x.
- Enrichment references resolve to alerts in the same case (VR-23).

IP addresses, ports, users, payloads, MITRE fields, event actions and native event
timestamps are not universally mandatory. Correlation labels and provider names
use an open vocabulary. The API accepts supplied enrichment data; it performs no
provider lookups and does not normalize native alerts.

## Configuration and assumptions

| Setting | Default | Meaning |
| --- | --- | --- |
| `MAX_ALERTS_PER_CASE` | `50` | Positive integer; sets both Pydantic validation and OpenAPI `maxItems`. |
| `CASE_DATABASE_PATH` | `data/cases.sqlite3` | Local SQLite file; parent directory is created at startup. |
| `ELASTIC_ALERT_ID_POINTER` | `/event/id` | Native string identifier location for the included synthetic Elastic profile. |
| `WAZUH_ALERT_ID_POINTER` | `/id` | Native string identifier location for the included synthetic Wazuh profile. |

Set variables before starting the application; restart after changing them. For
example, `MAX_ALERTS_PER_CASE=75 uvicorn app.main:app --workers 1` raises the
admission limit. This does not certify investigation throughput at that limit.
The bundled reference schema records the original 50-alert profile; clients using
it offline must update `maxItems` to the same configured limit. `/openapi.json`
already reflects the active limit.

**Design decision — native ID profiles:** defaults match only the synthetic
specification examples. They do not assert Aligo's actual export layout. Configure
the authoritative location after inspecting the customer's exports. For example,
`/kibana.alert.uuid` addresses a flat key and `/_id` addresses export metadata
retained within `raw_alert`. A Wazuh export could require `/_source/id`. Pointers
use JSON Pointer escaping (`~1` for `/`, `~0` for `~`). Missing or mismatching native
IDs return 422; a rule ID must never substitute for an event/alert ID.

Only one pointer per origin is configured in this prototype. Multiple simultaneous
export shapes will need a verified source-profile selection mechanism in future
parser work. The current implementation does not guess the native ID field.

**Design decision — local persistence:** VR-04 explicitly requires a persistent
uniqueness constraint, which meets this task's exception allowing a database when
required by the existing design. A single SQLite file provides that constraint and
preserves accepted input; there is no external database service. A short transaction
checks the submitted ID before UUID allocation, then inserts the accepted case with
database uniqueness constraints. Restarting with the same file retains case history.
The file is created at application startup, not at import, and is excluded from the
delivery archive and version control. Tests use temporary isolated databases.

**Design decision — response IDs and HTTP status:** the input contract does not
define an HTTP response or reconcile its required submitted `case_id` with a new
server UUID. This implementation returns both identifiers as described above and
uses 409 for an existing submitted ID. UUID generation occurs only after structural,
semantic and duplicate-submission checks succeed; it is isolated in `core/ids.py`.

**Pending customer validation:** anonymized samples are not available. Native
identifier locations, possible cross-source collisions, custom decoder layouts,
source-version fidelity and enrichment shapes still require verification. The
included examples are synthetic, not customer data. Version admission checks do
not claim live Elasticsearch/Wazuh integration or compatibility testing.

## Automated verification

Run `pytest` after activating the virtual environment. The suite covers:

- Elastic, Wazuh and mixed acceptance; 201/status/UUID4; distinct generated IDs.
- Native/custom JSON preservation, optional investigation-field absence and
  independent copies of accepted evidence.
- Every mandatory case/alert field; invalid types, versions, origins and timestamps;
  empty, 50-alert and 51-alert cases; malformed JSON and non-JSON numeric constants.
- Duplicate alert IDs, native-ID mismatch/missing ID, alternate configured export
  shapes, duplicate submitted IDs, concurrent submissions and restart persistence.
- Unknown application fields; invalid correlation/enrichment metadata; explicit
  nulls; duplicate, empty and dangling enrichment references.
- No ID generation for structural or semantic rejection; unsuccessful submissions
  do not reserve their submitted ID.
- Configurable limits below and above 50, matching OpenAPI, invalid startup settings,
  and examples validated against the unchanged authoritative JSON Schema.

`ruff check app tests` checks style/imports. Exact execution results and the real
Uvicorn startup check are recorded in [`docs/VERIFICATION.md`](docs/VERIFICATION.md).

## Remaining scope

Customer-sample validation, source-aware parsers and normalized events remain future
work. This delivery contains no LLM/agent integration, reasoning,
timelines, frontend, authentication, live SIEM access, intelligence lookup adapters,
N8N integration, brokers, background queues or separate services.
