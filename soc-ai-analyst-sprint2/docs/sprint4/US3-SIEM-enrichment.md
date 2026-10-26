# US3 — Supplied SIEM enrichment compatibility

## Scope and customer clarification

On 2026-10-26 the project user relayed Aligo's clarification: “el formato que se
usa es que el que se encuentra en los datos del SIEM”. The supplied local archive
is `wazuh-alerts-2026-08-10_16.zip`. Its README describes a pseudonymized Wazuh 4.14
NDJSON export. This establishes the sample format; it does not establish that
n8n produced the records or verify a live n8n deployment.

Sprint source: workspace `SOC_AI_Sprint_Backlog.xlsx`, `SPRINT 4 BACKLOG!B35:O36`:
Ethan obtains samples/confirms mapping; Santiago adapts mapping/tests compatibility.
This branch implements both technical parts at the user's request. Backlog status
and formal acceptance remain separate from implementation evidence.

## Explicit conversion boundary

`app.services.wazuh_enrichment.build_wazuh_case` converts a deliberately selected
set of native Wazuh alerts into input v1.0. `app.services.wazuh_import` provides a
local CLI for NDJSON, gzip or this ZIP layout. The API still accepts its existing
contract; uploading a ZIP directly to the API is not implemented. The direct-agent
CLI is not this importer. No SIEM connection, LLM, provider lookup or n8n call occurs.

Original alerts, native IDs, timestamps (including `-0500`), provider values and
unknown fields are retained. Submission time is explicit RFC 3339 metadata, not
an inferred event time. Default case limit remains 50; duplicate/missing selected
IDs fail explicitly. ZIP members are streamed without extracting archive paths.

| SIEM field | v1.0 mapping |
| --- | --- |
| `id` | `alerts[].alert_id`; full source remains in `raw_alert` |
| `data.integration = virustotal` | `enrichments[].provider = virustotal` |
| `data.virustotal.source.sha256/sha1/md5` | Prefer first valid hash in that order for `observable`; preserve original casing |
| `data.integration = misp_file_hashes` | `enrichments[].provider = misp` |
| `data.misp_file_hashes.type/value` | Typed hash observable (SHA256/SHA1/MD5 only for this profile) |
| Complete provider object | `raw_result`, unchanged, including source IDs, scores, dates, URLs and unknown fields |
| Containing alert ID | Explicit `related_alert_ids` association to the record carrying the result |
| Provider `source.alert_id` | Additional explicit association only when that alert is in the selected case |

One enrichment is emitted per usable provider record. Different providers/queries
stay separate. Hash selection is a mapping policy, not a claim that the selected
hash is malicious. No provider scores, `found`, `malicious`, `positives`, rule
severity or MISP match raise hypothesis confidence or become invented verdicts.

Unknown integrations remain raw alerts. A recognized integration with an invalid
provider object or no valid observable remains raw and generates a mapping warning.
Thus rate-limit-only events are retained but do not fabricate IoCs. A `found=0`
result with a valid source hash is retained as supplied; it is not a clean verdict.
Missing parent IDs stay in `raw_result.source.alert_id` with a diagnostic, never a
dangling v1.0 reference. Containment/declared references remain distinct from typed
observable matches performed by the existing correlation/evidence pipeline.

The `.mapping.json` sidecar records ZIP member/line locations and JSON pointers
from each emitted enrichment to its raw provider object and observable. The API
retains the full raw alert and canonical enrichment, but does not store the sidecar;
keep it with the converted case. Report pointers resolve against accepted v1.0
input. The existing traceability validator verifies report preservation.

## Local use

Run from the application root with its configured virtual environment. Select
IDs intentionally (including the original alert IDs when available); a large
collection of alerts is not automatically one incident.

```powershell
.\.venv\Scripts\python.exe -m app.services.wazuh_import `
  D:/Repositorios/wazuh-alerts-2026-08-10_16.zip `
  --alert-id '<native source alert ID>' --alert-id '<provider alert ID>' `
  --case-id 'US3-local-case-001' --submitted-at '2026-10-26T12:00:00Z' `
  --output D:/Repositorios/us3-local-case-001.json
```

The output directory must exist. Existing output/sidecar files are not overwritten.
Review warnings before submitting the JSON through `POST /api/v1/cases`.
Keep customer inputs, outputs and temporary databases local, outside tracked
fixtures. Tests in Git contain independently synthetic records only. The supplied
README says public IPs were pseudonymized; external reputation lookups on them
would not describe the original IPs. This adapter performs none.

## Verification

Synthetic unit tests cover provider preservation, source pointers, missing parent
references, no-result/error cases, hash precedence, duplicate IDs, limits, ZIP
selection and CLI output. Pipeline tests exercise the real FastAPI → LangGraph →
local MCP → report path and retrieval after database reopen.

Opt-in customer test selects the first VT found, VT not-found, VT error and MISP
records plus available parent alerts. It does not label them as attacks. It reads
the private ZIP in place and prints only aggregate counts and source locations.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_wazuh_enrichment.py tests/test_wazuh_enrichment_pipeline.py tests/test_ioc_integration.py tests/test_pipeline.py -q
$env:ALIGO_WAZUH_ZIP='D:/Repositorios/wazuh-alerts-2026-08-10_16.zip'
.\.venv\Scripts\python.exe -m pytest tests/test_wazuh_enrichment_pipeline.py::test_customer_sample_compatibility -q -s --basetemp D:/Repositorios/.us3-private-tests
Remove-Item Env:ALIGO_WAZUH_ZIP
.\.venv\Scripts\python.exe -m ruff check app tests demo/run_pipeline.py demo/verify_local.py --exclude tests/test_agent_graph.py
```

Use a dedicated new `--basetemp` directory: pytest clears that directory on reruns.
These are reproducible commands, not by themselves evidence of passing execution.
Execution results are recorded separately in `US3-verification.md`.

## Acceptance boundary

This is sample-based compatibility for the observed Wazuh VT/MISP profile, not
coverage of every alert/provider or proof of n8n provenance, Elastic compatibility,
live connectivity, maliciousness or production readiness. The complete ZIP is
not an incident ground-truth dataset. Human review and one worker remain required.
