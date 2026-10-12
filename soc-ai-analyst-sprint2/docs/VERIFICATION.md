# Test execution report — 9 October 2026

## Environment

Linux, Python 3.12.14, FastAPI 0.142.1, Pydantic 2.13.5, Uvicorn 0.54.0,
MCP 1.30.0, LangGraph 1.2.14, pytest 9.1.1. Full installed package versions
are recorded in `verification/environment.txt`. No dependency-installation
blocker remained. Tests used isolated temporary SQLite databases.

## Executed commands and results

| Check | Command (from the indicated project root) | Result |
| --- | --- | --- |
| Original backend baseline | `python -m pytest -q` | 111 passed, 1.65 s |
| Original agent baseline | `python -m pytest tests -q` | 34 passed, 8.86 s |
| Integrated original tests | `python -m pytest -q` before adding new tests | 145 passed, 12.50 s |
| Integrated suite, first expanded run | `python -m pytest -q` | 183 passed, 21.57 s |
| Final suite, including extreme timestamp boundary | `python -m pytest -q --junitxml=docs/verification/pytest.xml` | **184 passed, 20.43 s** |
| Backend/new-test/demo lint | `ruff check app tests demo/run_pipeline.py demo/verify_local.py --exclude tests/test_agent_graph.py` | Passed |
| Installed dependency consistency | `python -m pip check` | No broken requirements |
| Real HTTP demonstration | `python demo/verify_local.py` | Passed; intake through investigation completed in 1.569 s for 4 alerts |

The final suite contains all 145 original tests and 39 new parametrized test
cases. Agent tests and integration tests execute the real LangGraph and local
MCP subprocesses; no mocked happy-path agent is used. One intentional injected
MCP failure tests retained input and successful retry. Lint scope excludes the
original agent test file and legacy agent style; a whole-repository clean lint
result is not claimed. The inherited GitHub CI matrix was not executed remotely.

Logs and machine-readable results: `verification/pytest.log`,
`verification/pytest.xml`, `verification/baseline-backend.log`,
`verification/baseline-agent.log`, `verification/lint.log`,
`verification/dependencies.log` and `verification/demo.log`.

## Coverage demonstrated

- Original intake: Elastic/Wazuh/mixed cases, all mandatory fields, types,
  version profiles, custom-field preservation, duplicates, native IDs, limits,
  configuration, enrichment references, concurrent submission and restart.
- Correlation: related pairs across sources, disjoint noise, weak shared IP,
  missing entities, time-window boundaries, timezone equivalence, missing/invalid/
  conflicting/extreme times, typed IP values, exact evidence pointers, dotted
  keys, `_source` exports, original metadata and reserved-key collision preservation.
- MITRE separation: unrelated alerts matching the same technique generate
  independent hypotheses without pooled confidence.
- IoCs: optional/absent results, exact typed matches, explicit-only links,
  combined association methods, different providers, unsupported/unmatched
  observables, source paths, provider reference preservation, and no matching
  on alert IDs, arbitrary message strings or substrings.
- Full flow: POST acceptance, stored input retrieval, correlation/context,
  real graph invocation, original report JSON Schema validation, evidence
  verification, hypothesis IoC links, human-review pause/resume and saved results.
- Failure behavior: missing cases, malformed UUIDs, invalid review decision,
  injected agent failure, retained input, retry, restart report retrieval,
  temporary review-checkpoint limitation and duplicate-review rejection.

## Real HTTP demonstration

The demonstration starts Uvicorn, submits `examples/sprint2_demo.json` via HTTP,
and runs the agent. The submitted ID is randomized only to avoid duplicate
case rejection; the original alert identifiers are unchanged.

| Pair | Actual classification |
| --- | --- |
| ecs-auth-001 / wazuh-auth-002 | related |
| ecs-auth-001 / ecs-noise-003 | unrelated |
| ecs-auth-001 / ecs-uncertain-004 | uncertain |
| wazuh-auth-002 / ecs-noise-003 | unrelated |
| wazuh-auth-002 / ecs-uncertain-004 | uncertain |
| ecs-noise-003 / ecs-uncertain-004 | unrelated |

`ecs-noise-003` is retained as an unrelated noise candidate. IoC 1 matches both
authentication alerts. IoC 2 is linked by a supplied reference only. IoC 3 stays
unmatched. All three are retained. The report validates successfully and stops
at `pending_review`; no automated analyst approval is simulated in the demo.
The separate review test resumes the graph and verifies persistence.

`demo/output/summary.json`, `investigation.json`, `submitted_case.json`,
`accepted.json`, `report.md` and `server.log` contain the actual execution.
The measured 1.569 seconds covers the four-alert intake/investigation request
sequence after server readiness, excluding installation and server startup.
This is one environment's synthetic observation, not a throughput guarantee.

An initial demo attempt started the server and client in separate isolated
execution sessions and received connection refused. Running both in the same
local execution environment through `verify_local.py` resolved that environment
issue. No failed automated tests remain. Ordinary style corrections were made
before the final lint run.

## Preservation and limits

The original intake model, semantic service, input JSON Schema and specification
DOCX were compared byte-for-byte and remain unchanged. Their SHA-256 values are
listed in `verification/contract-sha256.txt`.

The backlog has 18 DONE tasks and 1 IN PROGRESS (row 19: actual N8N output).
Only status cells F5:F23 changed. Every other XLSX package entry was retained
byte-for-byte; cell values, formulas, styles, merges, row heights and sheet names
were independently compared. Native validation extensions were retained.

Not verified: production N8N/provider mappings, live customer SIEM data,
classification accuracy on analyst-labeled cases, full 50-alert investigation
latency, concurrent multiworker deployment or other Python/OS versions.
Fifty-alert pair enumeration is unit-tested; it is not a full-investigation
performance benchmark. Human-review checkpoints remain process-local memory.
