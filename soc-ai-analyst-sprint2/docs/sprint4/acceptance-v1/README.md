# Alpha acceptance checklist v1.0 — Sprint 4 / #69

**2026-10-31, America/Bogota. Release acceptance: pending.** Technical review of
`4fb12ea` on Windows/Python 3.12.2, with `LLM_PROVIDER=none`. This candidate includes
[#126](https://github.com/IA-SOC/Alpha/pull/126) (#84/#87) and
[#127](https://github.com/IA-SOC/Alpha/pull/127) (#67). During publication, #127
merged into #126's branch as `1045e48`, whose code tree is identical to `4fb12ea`.
#126 remains unmerged to `main` (`c2c91cb`); candidate results do not establish
main-branch delivery or client acceptance.
This checklist supersedes older implementation-status claims only for this
revision; original specifications, workbooks and historical records are unchanged.

## Requirements and acceptance evidence

Sources: [original proposal](../../legacy/Agente%20Analista%20de%20IA%20para%20SOC%20%E2%80%94%20Descripci%C3%B3n%20del%20proyecto.docx)
(functional requirements, nonfunctional table, expected results/restrictions),
[input specification v1.0](../../Incident_Case_Input_Specification_v1.0.docx)
(D-01–D-10, VR-01–VR-23), [agent protocol](../../../skills/soc-case-investigator/references/protocolo.md),
[report v1.1](../../../skills/soc-case-investigator/references/report-schema.json),
and [Sprint 4 issues](https://github.com/IA-SOC/Alpha/issues?q=label%3Asprint-4).
Workbook traceability: workspace [product workbook](../../../../../SOC%20AI%20Product_Backlog.xlsx),
`PRODUCT BACKLOG - Initial!B4:K18` and `PRODUCT BACKLOG-Sprint 4!B4:K26`;
[sprint workbook](../../../../../SOC_AI_Sprint_Backlog.xlsx), `SPRINT 4 BACKLOG`, task row 20 (#69).
These planning sources are not runtime verification or client sign-off.

**S = satisfied within the stated tested scope; P = partially satisfied or
implemented but unverified here; N = not implemented in this candidate.**
Test paths below are relative to [tests/](../../../tests/). D = the executed
real-HTTP demo in [results.json](results.json), reproduced with [demo_check.py](demo_check.py).

| Requirement | Status / evidence | Remaining acceptance boundary / issues |
| --- | --- | --- |
| R1/US1 JSON intake and validation | S: D returns 201, invalid 422, duplicate 409; `test_cases`, `test_contract`, `test_case_parser` | Tested input v1.0 profiles, not arbitrary native exports; #70/#71 closed |
| R2/US2 correlation and retained noise | S: D has 1 related, 2 uncertain, 3 unrelated pairs; `test_correlation_engine` | Relationships are not causal attack sequences |
| R3/US3 supplied IoCs | P: D retains 3 items; `test_ioc_integration`, `test_wazuh_enrichment*` | Local adapter exists; live n8n provenance not established; #47/#48 closed, #82 open |
| R4/US4 timeline | P: ordering criteria pass in `test_timeline_order`, `sprint3/test_us4_cases`, D | UTC ordering, stable ties, undated last are verified; attack progression/causality and clock-drift detection are not established |
| R5/US5 MITRE mapping | P: 7 local candidate rules; `test_mitre_mapping`, D | Coverage/false positives and unpinned catalog remain (G3) |
| R6/US6 hypotheses | P: `test_hypotheses`, `sprint3/test_us6_cases`, D | Grouped evidence/alternatives exist; no general attack reasoning or quality metric (G3) |
| R7/US7 original evidence | P: `test_pipeline`, `sprint3/test_us7_cases`, `sprint3/test_report_audience_evidence` | API checks IDs/pointers/values; free-text truth and direct-CLI parity remain (G3) |
| R8/US8 confidence | P: `test_report_contract`, actual insufficient case in #67 tests | Ordinal/basis/support enforced in candidate #126; corroboration/missing-field rubric gaps remain; #84 open |
| R9/US9 blast radius | P: D, `test_agent_graph`, `test_pipeline` | Observed/suspected entities carry alert IDs; confirmed lists deliberately empty; #85 open |
| R10/US10 actions | S: `test_agent_graph`, `test_report_contract`, D | Evidence/rationale/priority and pending approval only; no response execution; #86 closed, story #94 open |
| R11/US11 structured JSON and Markdown | S: D, `test_report_contract`, `test_agent_graph` | v1.1 enforcement in unmerged #126; #87 open; security exclusions are G1 |
| R12/US12 analyst inspection | P: connected UI source exists; D/API and `test_pipeline` pass | Browser not executed (G4); two audience sections not consumed in UI (G2); #50 open |
| R13/US13 individual decisions | S: D records 2 finding decisions; `test_sprint4_isabella` verifies restart, stale-run and note validation | Records overrides alongside unchanged analysis; no case closure; #56/#72/#88 closed |
| R14/US14 JSON export | P: D export equals saved review; `test_sprint4_isabella` | Synthetic credential field leaks into export (G1); #89 closed does not prove exclusion criterion |
| R15/US15 several open cases | N: storage supports IDs; routes have no case-list/workspace | No multi-case management UI; single worker remains required |
| US16 web upload/paste | P: `frontend/src/features/new-case` and tests present | Runtime UI verification blocked locally (G4); #51–#53/#106 closed |
| US17 Gemini evaluation | P: adapter, guarded mock/error fallback in `test_llm` | No executed live smoke/evaluation here; no comparison harness found; #68 open, #75 closed |
| US18 read-only retrieval | N in candidate | [#125](https://github.com/IA-SOC/Alpha/pull/125) unmerged, explicitly excludes agent wiring; #77 closed, #79/#99 open |
| US19 two report audiences | P: #67 tests plus `test_report_formatter`, D JSON/Markdown | #127 joined #126 during review; main merge/acceptance pending; UI gap G2; #66/#78 closed, #67/#81 open |
| US20 analyst-guided revision | N in candidate | No instruction/revision endpoints; [#122](https://github.com/IA-SOC/Alpha/pull/122) unmerged; #76 closed, #80/#101 open |
| US21 future SIEM connectivity assessment | P: fixture-based Wazuh converter/importer exists | No live access implied; general Elastic/Wazuh access/mapping assessment #90/#102 open |
| US22 client compatibility | P: local tests exist; older [US3 verification](../US3-verification.md) is historical evidence | Both private-data tests skipped now; no adjudicated investigation-quality acceptance; #91 closed |
| US23 branding | P: logo/theme and bilingual UI source present | Current usability/responsiveness and client approval not verified here; #83 closed |
| Performance ≤5 minutes, ≤50 alerts | P: D four alerts in 4.231 seconds; 300-second timeout exists | No full 50-alert benchmark; timeout/admission tests are not a performance result |
| Deployment / human authority | P: local single-worker demo succeeds; no automatic response | No containers, real backend authentication or durable job queue found; recorded browser demo/client review pending |

## Executed checks

- **424 passed, 2 skipped, 239.95 seconds**: full backend suite, including real
  local MCP/agent, direct-agent, API/persistence/review and #67/#84/#87 tests.
  Skips require `ALIGO_PREPARED_DIR` and the local customer ZIP opt-in; neither
  client-data test passed in this run.
- Exact backend CI lint scope passed; additional demo-script E/F/I checks passed.
- D: synthetic mixed-source case → validated report → pending human review →
  automated test decisions → export. Six audit phases, 409/422 negative intake,
  unchanged hypotheses after review, matching saved/exported result. This is an
  **API demo, not browser usability, model quality or client approval evidence**.
- `npm test` and `npm run e2e` both exited 1 before collection: missing Vitest /
  Playwright. Node 20.16.0 is below required 22.22; `node_modules` absent. Frontend
  lint/typecheck/build were not run. No dependencies installed or types generated.
- [results.json](results.json) records exact commands, versions, results and
  probe inputs. Raw demo JSON/Markdown/logs remain local under ignored `run/`;
  existing `demo/output/`, application code and original documents are untouched.

## Remaining defects, limitations and dependencies

| ID | Reproduction / evidence | Consequence and next owner decision |
| --- | --- | --- |
| G1 — export credential exclusion unmet | D submits fake `raw_alert.password = ACCEPTANCE-SYNTHETIC-SECRET`; export returns it at `investigation_context.original_case.alerts[0].raw_alert.password`. See `known_gaps` in results and [export route](../../../app/api/routes/investigations.py). | #89 acceptance says exclude credentials. Define an export redaction/allowlist policy preserving internal evidence, then add a focused regression. Do not mark export fully accepted or modify raw stored evidence. |
| G2 — audience presentation not connected in UI | `rg audience_sections frontend/src/features/case/report` has no matches; [SummaryTab](../../../../frontend/src/features/case/report/SummaryTab.tsx) renders `executive_summary` and canonical fields only. | Separate audience JSON/Markdown exists, but no separate UI audience presentation verified. Track with #55/#100/#81; #55 is closed. |
| G3 — bounded methodology and evidence checks | Reproduced benign `vssadmin list shadows` → T1490; 3 distinct rule names with missing host/user → `alta`. [Catalog criteria](../../sprint3/S3-US5-T01-mitre-catalog-review.md), [HY-08/10/15/16/18](../../sprint3/S3-US6-T01-hypothesis-criteria.md), [EV-13/20](../../sprint3/S3-US7-T01-evidence-criteria.md) retain their separate gaps. | Candidate labels mitigate overclaiming but do not prove correctness. Corroboration, missing-field downgrades, fallback contradiction windows, tailored unknowns, narrative entailment and direct-path pointer enforcement need explicit scope decisions; #84/#85 and original #37/#42 criteria. No accuracy percentage justified. |
| G4 — UI execution unavailable here | Commands stop before tests collect; existing [Playwright workflow](../../../../frontend/e2e) contains a review-note locator targeted by unmerged [#124](https://github.com/IA-SOC/Alpha/pull/124). | Use supported Node and locked dependencies, run documented frontend checks and Chrome E2E, then review #124. The locator defect was source-inspected here, not reproduced in a browser. #59 is closed. |
| G5 — operational/history limits | [Service](../../../app/services/investigation_service.py) and [store](../../../app/storage/case_store.py): latest investigation replaces prior result; sessions/locks process-local; request occupies HTTP call. | Structured per-finding review survives restart (tested); legacy review without run ID still needs live checkpoint. No durable history/queue or multiple workers; no case-closure API. #80/#101 and deployment follow-up. |
| G6 — unmerged work / status drift | Open PRs #122/#124/#125/#126 at publication; #127 merged into #126 during review, not main. Some associated issues already closed. README's blanket restart-review limitation predates durable per-finding review. | Merge status, issue closure and workbook planning are not acceptance proof. Reconcile documentation/status after review; do not silently claim follow-up/retrieval exists on main. |

## Scope and client decisions for sprint review

Confirmed in existing records: [US3 mapping](../US3-SIEM-enrichment.md) records
the user's 26 Oct confirmation that supplied SIEM format is the reference, not
n8n/live provenance. [#106](https://github.com/IA-SOC/Alpha/issues/106) records the
Alpha fake-login / Beta real-login scope decision. Browser names are not trusted
authentication; no backend access control is established by that screen.

Pending, not invented approvals: Aligo/supervisors must review the integrated
browser demo and report clarity; confirm acceptable credential exclusions,
supported export/source profiles and n8n provenance; adjudicate representative
case labels/playbooks and catalog/quality tradeoffs; approve any live Gemini
evaluation/data-sharing and cost basis; agree 50-alert performance/deployment
conditions and whether case closure/history/multi-case UI are deferred.
No independent current client feedback or sign-off was produced in this review.

[#69](https://github.com/IA-SOC/Alpha/issues/69) has a versioned checklist and an
executed scoped demo, with unresolved items recorded for review. Keep it open
until owner/supervisor review of these scope decisions and the integrated browser
feedback dependency is resolved or explicitly deferred. AI use: Codex inspected
sources, ran tests/demo, added the verification harness and drafted this record;
actual human effort and accepted edits remain for the owner to record. No
workbook, Projects status or unrelated issue state was changed.
