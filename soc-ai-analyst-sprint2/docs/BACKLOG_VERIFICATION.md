# Sprint 2 backlog verification

The workbook's sheet names, owners, task wording, estimates, formulas, AI fields,
formatting and other sheets are preserved. Only `F5:F23` on
`SPRINT 2  BACKLOG` changed. Actual effort is left blank because no verified human
time records were supplied. Completion refers to implementation demonstrated
by this delivery, not a claim about work performed by each named owner.

| Row | Story/task | Status | Verification |
| --- | --- | --- | --- |
| 5 | US1: supported case JSON | DONE | Original authoritative DOCX and schema retained unchanged |
| 6 | Mandatory fields and validation rules | DONE | Original Pydantic and semantic VR checks retained; intake tests pass |
| 7 | Valid and invalid samples | DONE | Original `examples/` plus `sprint2_demo.json`; schema/API tests |
| 8 | Parser and validator | DONE | Original `case_parser.py`, `schemas/case.py`, `case_service.py`; parser tests |
| 9 | Submission endpoint | DONE | Original POST route; real HTTP demonstration returns 201 |
| 10 | Unique case identifier | DONE | UUID tests, duplicate rejection and restart persistence |
| 11 | Intake automated tests | DONE | Original 111 backend tests all pass |
| 12 | US2: relationship evidence | DONE | `evidence.py`, documented families/time rules, pointer tests |
| 13 | Internal relationships/evidence | DONE | Typed output models in `schemas/investigation.py` |
| 14 | Related/uncertain/unrelated representation | DONE | Typed classifications and documented pair/alert dispositions |
| 15 | Correlation mechanism | DONE | `correlation.py`; actual pair decisions in unit/API/demo runs |
| 16 | Unrelated and uncertain alerts | DONE | Noise candidates retained; uncertain singletons not silently discarded |
| 17 | Related/noise samples | DONE | Original fixture plus mixed-source demo with uncertain activity |
| 18 | Test and document expected relationships | DONE | `test_correlation_engine.py`, `test_pipeline.py`, demo assertions and technical guide |
| 19 | US3: structure based on N8N output | IN PROGRESS | Contract-based wrapper implemented; actual customer N8N output was not supplied |
| 20 | Parse/validate pre-enriched IoCs | DONE | Original input validation plus typed association integration |
| 21 | IoC data in investigation context | DONE | `ioc_integration.py`, `agent_adapter.py` and real LangGraph IoC phase |
| 22 | Findings reference IoC evidence | DONE | Hypothesis `ioc_evidence`, source pointers and broken-reference rejection test |
| 23 | Tests with/without enrichment | DONE | Original enrichment tests and new matching/end-to-end cases |

18 DONE, 1 IN PROGRESS. To complete row 19, obtain representative anonymized N8N
outputs, verify provider/observable/result/reference mapping into v1.0, and add
fixture-based compatibility tests. Do not mark it done from synthetic wrappers
alone. Rows 20–23 verify the documented input contract, not a production N8N
integration. No external enrichment lookups were implemented.
