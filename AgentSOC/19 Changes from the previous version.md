---
tags: [agentsoc, changes, architecture]
aliases: [Changelog, Sprint 2 changes, What changed]
updated: 2026-10-11
---

# Changes from the previous version

**Previous version:** `Success/soc-agent-mcp/` (separate backend `Backend/soc-ai-analyst-backend/` and agent `soc-agent-mcp/`, documented in Spanish in `Success/soc-agent-mcp/AgentSOC/`).
**This version:** `Implentde prueba/SOC_AI_Analyst_Sprint2_Integrated/soc-ai-analyst-sprint2/`.

The agent is the same: same skill, same six phases, same MITRE rules, same MCP servers, same report schema and validator. What changed is how it is fed, run and checked.

> [!note] Two branches, one origin
> Sprint 2 was built from the original backend and agent snapshots (111 and 34 tests), not from the previous version's final state (120 and 39 tests). That is why some later additions of the previous version are missing here (see *Dropped or regressed*).

## Optimized

| Area | Before | Sprint 2 | Gain |
| --- | --- | --- | --- |
| Deployment | Two projects, two venvs, `AGENT_DIR` / `AGENT_PYTHON` | One project, one `.venv`, no agent variables | Simpler setup, nothing to point at |
| Agent invocation | Subprocess per case: `python agent/graph.py case.json --json`, temp file, stdout parsing | In-process call to `investigate()` | No Python and LangGraph start per case, no serialization round trip |
| Contract translation | Inside the agent (`normalize_intake_alert`) | In the backend adapter, with the original case kept whole | The agent stays format-agnostic; nothing is lost in translation |
| Hypothesis confidence | Every alert matching a technique pooled together | Pooled only within correlation groups | Unrelated alerts cannot inflate confidence |
| IoC matching | Exact value anywhere in any text field | Exact value in typed security fields; declared links kept separate | Fewer false links; clear provenance |
| Evidence checking | Skill validator only (cited IDs exist) | Plus traceability check (pointer → value) | Every new claim is verifiable against the input |
| Validator subprocess | No timeout | 60 s timeout | A hung validator cannot hang the case |
| Robustness | Non-string host/user or overflowing dates could crash phase 1 | Ignored or marked `invalid` | Custom fields cannot crash the agent |
| Concurrency | — | Per-case `asyncio.Lock`; SQLite work in a thread | No overlapping runs on one case; event loop not blocked |
| Dependencies | Version ranges | Pinned exact versions | Reproducible installs |
| Tests | 120 backend + 39 agent, two suites | 184 in one suite (145 original + 39 new), real graph and MCP | One command checks everything |
| Evidence of execution | Manual | `docs/verification/` logs, `demo/output/` from a real HTTP run | Auditable delivery |

## Added

- **Correlation engine** (US2): pairwise rules R1–R4, dispositions, groups, noise candidates. See [[16 Correlation engine]].
- **IoC integration** (US3): typed matches, declared links, `ioc_evidence` on hypotheses. See [[17 IoC integration and traceability]].
- **Endpoints:** `GET /{id}` (original input), `GET /{id}/context`, `POST /{id}/investigate`, `GET /{id}/investigation`.
- **Report fields:** `correlation`, `submitted_case_id`, `correlation_group_alert_ids`, `source_fields`, `ioc_evidence`.
- **Demo scripts:** `demo/verify_local.py` and `demo/run_pipeline.py`.
- **Docs:** `SPRINT2_IMPLEMENTATION.md`, `VERIFICATION.md`, `BACKLOG_VERIFICATION.md`, `CHANGES.md`.

## Dropped or regressed

Be aware of these when comparing the two versions:

| Item | Before | Sprint 2 | Note |
| --- | --- | --- | --- |
| Parallel MCP start | `mcp_sessions()` started the 3 servers at once (≈ 4.5 s → 3.0 s per case) | Servers start one after another, one subprocess per call | Not carried over. Port guide in [[12.5 Persistence and performance#Option A: start the servers in parallel, once per case · from the previous version]] |
| `--json` CLI flag | `agent/graph.py case.json --json` | Removed | Not needed in-process; the CLI prints Markdown only |
| CLI reads the v1.0 contract | Yes | No | Use the API for contract cases |
| Background investigation | `POST /cases` queued it; states `disabled`/`queued`/`running`/`completed`/`failed` | Explicit `POST /investigate`, synchronous, `502`/`504` on failure | Simpler, but the HTTP request waits |
| Review after restart | Decision stored in SQLite; worked after restart | Needs the in-memory checkpoint; `409` after restart | Reports still readable. See [[12.5 Persistence and performance]] |
| Process isolation | Agent crash could not affect the API | Agent runs inside the API process | Trade-off for speed and simplicity. See [[05 Architecture#Architectural pattern (Yokoyama, 2019)]] |
| Engine rollback | Change `AGENT_DIR` | Revert agent folders in Git | Still possible, no longer a config switch |

## Unchanged on purpose

- Intake contract DOCX, JSON Schema, Pydantic models and semantic case service: compared byte-for-byte (`docs/verification/contract-sha256.txt`).
- Skill, report schema 1.1 and `validate_report.py`.
- The MITRE catalog in `core/logic.py` and the four MCP servers.
- All 145 tests of the original snapshots (111 backend + 34 agent).

Back to [[00 Home]]
