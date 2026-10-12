# Sprint 2 technical implementation

## Preserved implementation and architecture

The backend already supplied strict Pydantic envelope validation, semantic VR
checks, original-ID verification, SQLite persistence, UUID allocation, synthetic
examples and 111 passing tests. It had no investigation endpoint or correlation
algorithm. Its noise tests checked fixture preservation only.

The agent already supplied normalization, a six-phase LangGraph workflow, local
MCP tools, MITRE candidate mapping, hypotheses, timeline, scope assessment,
report validation, Markdown output and a human-review interrupt. Its 34 tests
ran real MCP subprocesses. It expected direct alert fields and singular
`enrichment`, unlike the backend's wrappers and `enrichments`.

The integrated directory has one copy of each component: `app/` remains the
backend; `agent/`, `core/`, `orchestrator/`, `servers/` and `skills/` retain the
agent's original relative layout. The input DOCX, JSON Schema, Pydantic intake
models and semantic case service are unchanged. The report schema and skill
validator are also unchanged.

## Execution and provenance

1. Original `POST /api/v1/cases` validation accepts and stores the case.
2. `POST /api/v1/cases/{uuid}/investigate` reads that accepted SQLite record.
3. `extract_events` collects supported attributes and original JSON Pointers.
4. `correlate` classifies every unordered alert pair.
5. `integrate_iocs` associates only supplied intelligence.
6. `adapt_case` creates the agent input and investigation context.
7. The existing graph runs its original six phases: receive, hypotheses,
   timeline/scope, IoC consumption, report validation, human review.
8. The original report validator and new evidence-pointer check validate output.
9. The result is saved in SQLite; the graph pauses for review.

The UUID and submitted ID stay distinct. Evidence pointers are rooted at
`investigation_context.original_case`, e.g. `/alerts/1/raw_alert/data/srcip` or
`/enrichments/0`. That object retains the entire accepted payload, including
custom nested fields, export metadata, original times and full provider results.

The adapter unwraps a standard `_source` object in its working view and sets
`alert_id` to the already-validated wrapper ID. A conflicting custom native
`alert_id` remains intact in `original_case`. The adapter does not duplicate
intake validation or infer a native identifier. Internal context is constructed
by the service, never accepted as an additional v1.0 envelope field.

The original distinction remains: unknown application-envelope fields are
rejected; custom fields inside `raw_alert` and `raw_result` are preserved.

## Correlation rules

Default window: **300 seconds**, inclusive. Complexity: O(n²) pairs. Fifty alerts
produce 1,225 pair records. The pure function and service constructor accept a
positive alternative window without changing the input contract.

| Family | Supported examples | Comparison |
| --- | --- | --- |
| Network | `source.ip`, `destination.ip`, `data.srcip`, `data.dstip`, `host.ip`, `agent.ip`, legacy IP fields | Parsed IPv4/IPv6; original endpoint direction retained in evidence |
| User | `user.name`, `data.srcuser`, `data.dstuser`, `user.id` | Exact names/IDs, kept as distinct kinds |
| Host | `host.name`, `host.hostname`, `agent.name`, `host.id`, `agent.id` | Exact names; Wazuh agent ID has a separate namespace |
| Process | `process.entity_id` | Entity ID; PID alone is not used |
| Session | `session.id` | Exact ID; source scoping requires customer validation |
| Artifact | File/process MD5, SHA-1, SHA-256 | Valid hexadecimal length; case-insensitive |
| Time | `@timestamp`, `timestamp` | Timezone-aware event time, compared as UTC instants |

Nested keys, flat dotted keys and the standard `_source` envelope are supported.
Pointers retain original array indices and values. Malformed, absent, timezone-free
or conflicting event times provide no temporal evidence. `submitted_at` is never
substituted. Multiple IPs or user aliases still count as one family.

| Rule | Classification | Decision |
| --- | --- | --- |
| R1 | `related` | At least two matching entity families and valid times within the window |
| R2 | `uncertain` | Entity matches exist, but independent corroboration or temporal proximity is insufficient |
| R3 | `unrelated` | No shared values across at least two comparable entity families |
| R4 | `uncertain` | No shared values and fewer than two comparable families |

Time alone, a rule name, a shared MITRE technique or submitted correlation labels
never establish a relationship. A hash alone is uncertain. R3 means unrelated
under this limited profile, not proof that a relationship is impossible.

Each pair includes its ID, original alert IDs, classification, rule, explanation,
time delta and evidence paths/values. Typed models are in
`app/schemas/investigation.py`. An alert is `related` if any pair is related,
otherwise `uncertain` if any pair is uncertain or it has no peers, otherwise
`unrelated`. Only the latter are noise candidates. All alerts remain available.

Related-pair connected components define analysis groups. They do not imply
that every pair in a group is directly related. Original MITRE mappings are
partitioned by these groups before the original hypothesis builder runs.
Uncertain and unrelated singletons are independently investigated. Thus, an
unrelated alert cannot inflate another group's confidence merely by matching
the same technique. The report does not combine techniques into a global
causal attack sequence solely from their classification.

## IoC integration

The v1.0 enrichment wrapper remains provider-independent:

```json
{
  "provider": "synthetic_feed",
  "observable": {"type": "ip", "value": "192.0.2.50"},
  "related_alert_ids": ["ecs-auth-001"],
  "raw_result": {"reference": "https://example.test/synthetic-ioc"}
}
```

Only `provider` and `observable` are mandatory. Each internal item adds a
case-local ID (`ioc-0001`, etc.) and source pointer, retaining every supplied
wrapper field and the opaque provider payload.

- `explicit_reference` records an existing `related_alert_ids` entry. This is a
  declared association, not a claim that the observable appears in alert fields.
- `observable_match` records a value found in a supported typed security field,
  including its original pointer and value. Arbitrary messages, custom text,
  alert IDs and substrings are not used to infer associations.

Automatic matches support IP/IPv4/IPv6, domain/hostname, URL, email, MD5, SHA-1,
SHA-256 and generic hash. IPs and hashes use canonical representations; domains
ignore case/trailing dot; URLs and emails are exact. Unknown types retain their
data and explicit links. Unmatched IoCs stay visible. Different providers remain
separate. Missing results and verdicts are not fabricated.

The original IoC graph phase consumes these associations. A hypothesis referring
to an associated alert gets `ioc_evidence` containing its enrichment ID, source
pointer, provider, observable and association method. The role is contextual:
provider-specific results are not automatically interpreted as proof or used
to raise confidence. Full results and reference URLs remain available through
`enrichment.items` and the investigation context. No URLs are fetched.

Actual N8N-to-v1.0 mappings require customer samples. There is no implemented N8N
webhook or provider lookup. The demo's feed names and payloads are synthetic;
they do not certify provider-specific response formats.

## Persistence, endpoints and failures

See the root README for requests. Intake remains 201/422/409. Missing retrieval
records return 404, and invalid UUID paths return 422. Investigation returns 200
with status, run UUID, context, correlation, report, Markdown, validation and audit.
An additive SQLite table stores the last successful result for each case.

A 300-second cancellation timeout returns 504. Agent/MCP/report validation
failures return 502 without removing accepted evidence. A successful retry starts
a fresh graph. An application-level async lock serializes work on the same case.
Review resumes the original LangGraph interrupt, requiring status, analyst and
notes. After restart or completed review, a missing/nonpending checkpoint returns
409; saved reports remain readable. `corrected` retains the supplied agent's
annotation behavior and does not edit individual findings. Reruns replace the
last report and checkpoint; report history is outside this sprint.

Existing environment settings remain: `MAX_ALERTS_PER_CASE` (50),
`CASE_DATABASE_PATH` (`data/cases.sqlite3`), `ELASTIC_ALERT_ID_POINTER`
(`/event/id`), `WAZUH_ALERT_ID_POINTER` (`/id`). Configure actual export paths
before startup, e.g. `/_id` or `/_source/id` when appropriate. One ID profile per
source remains supported; no native ID field is silently guessed.

The reference JSON Schema remains the original 50-alert profile. OpenAPI follows
the configured admission limit. Higher limits are not performance-certified.
Run one Uvicorn worker because review checkpoints and locks are process-local.
Direct dependencies are pinned to the versions tested; the full environment is
recorded in `docs/verification/environment.txt`.

## Remaining limits

- Customer N8N output, decoders, identifier layouts and tenant/domain scoping
  remain unverified. Field names/IDs can have different scopes across tenants.
- The supplied agent remains a deterministic five-rule prototype with its
  original MITRE/catalog limitations (see `AGENT_ORIGINAL.md`). No LLM was added.
- Synthetic tests establish behavior, not real-world precision/recall. Related
  entities can still describe benign activity; correlation is not causation.
- Accepted cases/last reports persist, but review checkpoints and locks remain
  in memory. No distributed queue, authentication or production hardening was added.
- The four-alert real-HTTP demo was measured. Full 50-alert investigation
  performance and production load were not benchmarked.
- Historical agent report/HTML snapshots remain unchanged. `demo/verify_local.py`
  and `demo/output/` provide the integrated Sprint 2 demonstration.
