# Issue #67: audience sections grounded in source evidence

Issue: [#67](https://github.com/IA-SOC/Alpha/issues/67), current product mapping
US19. Verified on 2026-10-31, Windows/Python 3.12.2, existing project `.venv`.
Branch `test/67-report-audience-evidence` starts from `27cbac0` (#84/#87,
[PR #126](https://github.com/IA-SOC/Alpha/pull/126)); its PR targets that branch
while #126 awaits merge. Only acceptance tests and this record change.

## Acceptance coverage

[test_report_audience_evidence.py](../../tests/sprint3/test_report_audience_evidence.py)
adds 21 acceptance cases using the existing Sprint 3 API/MCP fixture, source
examples, expectation data and `tests.helpers` API submission helper:

- Both sections contain their required information. Summary claims resolve
  through canonical report pointers to original alert IDs and raw source values;
  raw pointers must belong to the cited alert. Technical findings retain original
  support and contradictions. Tests prevent empty evidence arrays from making
  these source checks pass vacuously.
- Mixed Elastic/Wazuh evidence, nested source fields, contradictory activity,
  missing telemetry and conflicting provider results are exercised. Supplied
  intelligence IDs resolve to the original enrichment records; provider verdicts
  remain quoted evidence and do not become summary facts or higher confidence.
- A real API investigation with one alert lacking a timezone produces
  `insuficiente` confidence. Both sections explicitly say insufficient, preserve
  justification/unknowns and retain the alert ID; no response action is proposed.
- Removing required audience content is rejected. Injecting factual compromise,
  infection or completed-response claims into either audience is rejected even
  when the accompanying canonical report pointers still resolve.
- Real reports pass the #84/#87 serializer unchanged. Existing formatter unit
  tests and canonical traceability tests remain responsible for their original
  scopes; their fixtures and assertions are reused rather than copied.

These tests check deterministic presentation and evidence traceability, not the
semantic truth of arbitrary security inferences or calibrated probabilities.
No formatter, schema, backend, dependency or original fixture changes are needed.

## Executed checks

Run from `soc-ai-analyst-sprint2/`, outside the Windows socket-restricted sandbox:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/sprint3/test_report_audience_evidence.py tests/test_report_formatter.py tests/test_report_contract.py tests/sprint3/test_us7_cases.py tests/sprint3/test_us6_cases.py tests/test_pipeline.py -q
.\.venv\Scripts\python.exe -m pytest tests/sprint3 tests/test_report_formatter.py tests/test_report_contract.py tests/test_pipeline.py -q
.\.venv\Scripts\python.exe -m ruff check app tests demo/run_pipeline.py demo/verify_local.py --exclude tests/test_agent_graph.py
git diff --check
```

The first invocation passed 122 tests, including all 21 new cases, but had 13
setup errors discovering the existing `sprint3_result` fixture in interleaved
explicit test paths. The corrected invocation groups Sprint 3 by directory;
it passed **151 tests in 72.63 seconds**, with no skips or failures. The CI lint
scope and staged whitespace check passed. The full suite was not rerun for this
test-only change; #84/#87 contract and pipeline regressions are included above.

Codex assisted inspection, test authoring and execution. Assigned-owner
review/demo and actual human effort/AI-use logging remain pending; no human
review or duration is invented. The issue remains open for that acceptance step.
