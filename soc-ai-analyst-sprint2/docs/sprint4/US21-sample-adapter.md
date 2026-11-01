# US21 / #90 — Local Elastic/Wazuh adapter prototype v1

Issues: [#90](https://github.com/IA-SOC/Alpha/issues/90), parent
[#102](https://github.com/IA-SOC/Alpha/issues/102). Source: workspace
`SOC_AI_Sprint_Backlog.xlsx`, `SPRINT 4 BACKLOG`, task row 36.
Base: `c051e443b2a39ac17e63b299cdd12c4ee9fe6f6a`; branch
`feat/90-sample-siem-adapter`. This is a local sample-file spike, not live
connectivity. No production SIEM, confidential customer data, credentials,
enrichment service or model API was accessed for implementation/verification.

## Prototype and mapping

[siem_samples.py](../../app/services/siem_samples.py) builds the unchanged
[input v1.0](../incident-case-input-v1.0.schema.json) from explicitly separated
Elastic and Wazuh arrays. It reuses `IncidentCase`, shared settings and native-ID
pointer reader, plus the existing whole-batch `build_wazuh_case` mapper. It adds
no endpoint, network client, dependency, schema field or duplicate analysis engine.
Existing backend validation remains authoritative at submission.

| Source field | Mapping / preservation |
| --- | --- |
| Elastic `event.id` | `alerts[].alert_id` via active `ELASTIC_ALERT_ID_POINTER` (default `/event/id`) |
| Wazuh `id` | `alerts[].alert_id`; existing Wazuh mapper requires `/id` and the active backend pointer must resolve to that same value |
| Explicit file source | `source_system` is `elastic` or `wazuh`; never guessed from names, tags or overlapping fields |
| Entire original object | Deep-copied unchanged into `raw_alert`, including custom keys/values, nulls, offsets, `_source`, `_index` and `_id` when supplied |
| ECS `@timestamp`, Wazuh `timestamp` | Retained in raw JSON; existing evidence/agent code derives UTC only from usable explicit zones. Missing time stays missing |
| ECS `host`, `user`, `source`/`destination`, `rule`/`tags`; Wazuh `agent`, `data`, `rule`/groups | Retained in raw JSON; existing extraction/correlation/normalization interprets supported paths, not this adapter |
| Embedded Wazuh VT/MISP results | Existing [US3 profile](US3-SIEM-enrichment.md) produces optional `enrichments`; provider payloads stay unchanged; no lookups or score-derived confidence |
| Case ID and submission time | Explicit required caller metadata; submission time never substitutes for event time. Source/ECS versions are not inferred; optional envelope version fields remain omitted |

Elastic records precede Wazuh records; each source's input order is retained.
This combination order implies no causal/time relationship. Empty selections,
nonstring/missing IDs, duplicate IDs within/across sources and combined sizes over
the configured limit (initially 50) fail rather than truncate or synthesize IDs.
Numeric IDs are not coerced. Native collisions are not silently prefixed.

CLI files must be JSON **arrays of objects**. Whole search responses, NDJSON,
archives and arbitrary source detection are not supported here. The existing
Wazuh importer remains responsible for its NDJSON/gzip/ZIP selection workflow.
Duplicate object keys, malformed JSON and non-finite JSON numbers are rejected.
An array of full Elastic search hits can be preserved only with an explicitly
matching ID profile (e.g. `/_source/event/id`) in both CLI and backend startup.
Default `/event/id` rejects that layout; it never falls back to `_id` or injects
an ID into the original. Flat ECS keys likewise need their exact pointer profile.
Only one ID profile per source is active; incompatible layouts need separate
admission profiles/cases, not silent conversion.

The `.mapping.json` sidecar links each source filename and sample-array pointer
to its final `raw_alert` pointer. Reused Wazuh enrichment/warning paths are rebased
to mixed-case indexes; alert IDs that resemble pointers are left unchanged.
Parent associations resolve within the selected Wazuh batch, as before; missing
parents remain raw with diagnostics. The backend stores the resulting case,
not this sidecar: retain both output files for audit. Preservation is semantic
JSON, not original whitespace/key order. A malformed input produces no output;
existing outputs/sidecars are never overwritten, and failed paired file creation
cleans up files created by that invocation. Raw sample values are not echoed in
CLI validation errors.

## Local reproduction

From `soc-ai-analyst-sprint2/`, with the existing venv and output directory:

```powershell
.\.venv\Scripts\python.exe -m app.services.siem_samples --elastic examples/sprint4/siem_samples/elastic.json --wazuh examples/sprint4/siem_samples/wazuh.json --case-id SYNTHETIC-US21-DEMO --submitted-at 2026-10-31T12:00:00Z --output demo/output/issue90-case.json
.\.venv\Scripts\python.exe -m pytest tests/test_siem_samples.py tests/test_wazuh_enrichment.py tests/test_wazuh_enrichment_pipeline.py tests/test_contract.py tests/test_pipeline.py -q
$env:LLM_PROVIDER='none'; .\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m ruff check app tests demo/run_pipeline.py demo/verify_local.py --exclude tests/test_agent_graph.py
```

Use a new output filename for each run; the directory must already exist. Review
the sidecar before submitting the case to the existing `POST /api/v1/cases`.
The [Elastic](../../examples/sprint4/siem_samples/elastic.json) and
[Wazuh](../../examples/sprint4/siem_samples/wazuh.json) fixtures are independently
synthetic. The API/agent tests reuse the existing synthetic VT provider fixture.

## Requirements before any future live connection

These are **proposed implementation prerequisites**, not implemented integrations
or client approvals. Official references checked on 2026-10-31:

| Area | Required agreement / future implementation |
| --- | --- |
| Elastic search and permissions | Identify permitted indices/data streams/aliases and tenant/space scope. Grant a dedicated identity index `read` for selected targets; add only required metadata privileges for approved mapping discovery. No write/admin/deletion role is needed for collection. See [search authorization](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-search) and [privileges](https://www.elastic.co/docs/reference/elasticsearch/security-privileges). Restricted Security indices require a separately approved access route, not blanket privileges. |
| Elastic authentication | Client provisions/rotates a scoped API key or approved service identity. Elasticsearch supports API-key, bearer and Basic authentication; use authorization headers over verified TLS. Provisioning keys is an operator task, not a collector privilege. See [authentication](https://www.elastic.co/docs/api/doc/elasticsearch/authentication). |
| Wazuh alert retrieval | Agree an indexer endpoint and allowed alert indices (deployment-specific). The indexer API commonly uses port 9200 and supports authenticated search. Give a dedicated identity only scoped search/read actions via the deployed RBAC configuration; do not reuse an admin account. Basic or configured JWT authentication depends on that deployment. See [indexer API](https://documentation.wazuh.com/current/user-manual/indexer-api/getting-started.html) and [RBAC](https://documentation.wazuh.com/current/user-manual/user-administration/rbac.html). |
| Wazuh manager is separate | The manager API commonly uses 55000 with authentication/token and its own permissions; it is not the historical indexed-alert search endpoint. Request it only if approved operational metadata is needed. Indexer and manager tokens/roles are not interchangeable. See [server API authentication](https://documentation.wazuh.com/current/user-manual/api/getting-started.html). |
| Paging/completeness | Agree time ranges, time zones, source filters, stable sort/tie-breaker and late-event policy. Elasticsearch PIT plus `search_after` avoids inconsistent deep paging; release PIT resources. See [pagination](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/paginate-search-results). Check timeouts, shard failures and result completeness. Validate a Wazuh-indexer-version-specific paging strategy separately. Never treat one page as a complete case or silently truncate at 50. |
| Transport and credentials | Allowlist approved hosts/ports and CA chain; verify certificates/hostname, use finite timeouts and restrict redirects/egress. Store secrets outside cases/reports/repos in an approved secret manager/environment; sanitize diagnostics. Never copy `-k`/TLS-disable examples into deployment. No such transport or credentials exist in this prototype. |
| Mapping and compatibility | Obtain approved anonymized samples, exact Elastic/Wazuh/ECS/export versions, authoritative IDs and field mappings. Decide `_id` vs event/alert ID, cross-index/tenant collisions, `_source` handling, conflicting/missing timestamps, optional version metadata and supported decoders. Startup admission versions are policy, not live certification. Preserve original payloads/paths; any namespace/contract change requires explicit design review. |
| Reliable intake | Agree poll cadence, bounded page/body sizes, overlap/watermarks and deduplication. Handle 429/backoff and transient failures with bounded retries; stop on authorization failures. Advance checkpoints only after verified intake acceptance. Distinguish case-ID conflicts from retries; do not batch unrelated alerts into one incident automatically. Single-worker backend and 50-alert cap remain. |
| Data/client authorization | Agree tenant boundaries, minimization/redaction before collection, retention, audited access and approved test environment. Do not put credentials into raw alerts; preserving raw input is not an export-redaction guarantee. Existing SIEM-format confirmation does not establish n8n provenance or permission for live access. No production write, containment, enrichment lookup or model transmission is in scope. |

Open client decisions for [#102](https://github.com/IA-SOC/Alpha/issues/102): which
API/indices/versions and credentials are approved; authoritative IDs and collision
policy; full-hit vs raw-document profile; case-selection/window and data-retention
policy; anonymized compatibility dataset and live-test authorization. These do
not block this sample spike, but they block claiming a working live connector.

## Executed verification and acceptance

2026-10-31, Windows/Python 3.12.2, existing venv; no dependency installation.
The initial focused suite passed **58 tests, 1 skipped in 29.38 seconds**. The skip
is the opt-in private customer ZIP test and is not a pass. The CLI command above
executed successfully: two alerts plus provenance sidecar under ignored
`demo/output/`; original fixtures and older demo outputs were unchanged.

[23 new tests](../../tests/test_siem_samples.py) cover individual/mixed sources,
frozen schema, intake/storage, deep-copy preservation, custom and null values,
existing Wazuh enrichment reuse/rebased paths, pointer-like IDs, explicit full-hit
profile admission, invalid/duplicate/missing IDs, combined limits, missing event
times through the real API/agent/report path, bad JSON and CLI no-overwrite/error
handling. Final full suite: **362 passed, 2 skipped in 242.53 seconds**. Both skips
require opt-in local customer data (`ALIGO_PREPARED_DIR` and the customer ZIP);
neither was executed or counted as passed. Exact CI lint, local-link and staged
whitespace checks pass; no unrelated application modules or source contracts
were changed. Local evidence left by earlier chats was preserved and excluded
from this change.

Technical spike/demo evidence is ready for owner review. Keep #90 open until the
assigned owner reviews/tests the accepted output and records actual human effort
and AI use as required by its delivery criteria. Codex assisted inspection,
implementation, tests and this connectivity assessment. No human review, live
compatibility, client sign-off or production connectivity is fabricated.
