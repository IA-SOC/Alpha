# Test map

[US28 (#200)](https://github.com/IA-SOC/Alpha/issues/200) tracks test traceability.
Story and requirement IDs follow the [acceptance matrix](sprint4/acceptance-v1/README.md)
and the [Sprint 5 backlog](https://github.com/IA-SOC/Alpha/issues/139).
Each row records a file's primary test type and the failure it is meant to catch.

## Backend

Run from `soc-ai-analyst-sprint2/` with the development requirements installed.

```sh
python -m pytest tests -q         # Full suite, same command as CI
python -m pytest -m unit -q
python -m pytest -m integration -q
python -m pytest -m security -q
python -m pytest -m regression -q
```

Each file gets the marker of its folder. Put new tests in the most relevant
folder and add a row to this map. A file can exercise more than one layer.
Three Wazuh/Aligo dataset checks need opt-in local inputs and skip by default.
The synthetic cases and provider doubles work without a Gemini key.

### Unit (`unit`)

| Test file | Story / requirement | Risk checked |
| --- | --- | --- |
| [`test_case_parser.py`](../tests/unit/test_case_parser.py) | US1 / R1 | Missing fields or malformed JSON reaching intake. |
| [`test_correlation_engine.py`](../tests/unit/test_correlation_engine.py) | US2 / R2, US7 / R7 | Incorrect relationships, UTC boundaries or pointers to changed evidence. |
| [`test_evaluate_labelled_cases.py`](../tests/unit/test_evaluate_labelled_cases.py) | US22 | False agreement when a technique has the wrong citation or has been rejected. |
| [`test_gemini_benchmark.py`](../tests/unit/test_gemini_benchmark.py) | US17 | Inflated quality or cost claims when citations, token usage or provider results are missing. |
| [`test_ioc_integration.py`](../tests/unit/test_ioc_integration.py) | US3 / R3, US7 / R7 | False IoC matches or loss of original provider data and references. |
| [`test_language_investigation.py`](../tests/unit/test_language_investigation.py) | US11 / R11, #187 | Mixed-language investigation text and warnings. |
| [`test_llm_fallback.py`](../tests/unit/test_llm_fallback.py) | US17, US24 | Lost fallback, repeated permanent errors or incorrect attempt metadata. |
| [`test_prompts.py`](../tests/unit/test_prompts.py) | US26 | Unversioned instructions, missing response fields or weakened evidence rules. |
| [`test_report_formatter.py`](../tests/unit/test_report_formatter.py) | US11 / R11, US19 | Invented findings, altered confidence or summaries without provenance. |
| [`test_wazuh_enrichment.py`](../tests/unit/test_wazuh_enrichment.py) | US3 / R3, US21 | Provider results that change source values, invent IoCs or lose pointers. |

### Integration (`integration`)

| Test file | Story / requirement | Risk checked |
| --- | --- | --- |
| [`test_automatic_investigation.py`](../tests/integration/test_automatic_investigation.py) | US24 | Accepted cases missing a model attempt, stuck jobs or unusable fallback reports. Gemini is doubled. |
| [`test_blast_radius.py`](../tests/integration/test_blast_radius.py) | US9 / R9, US19 | Duplicate assets, lost alert references or missing persisted audience sections. |
| [`test_cases.py`](../tests/integration/test_cases.py) | US1 / R1, US15 / R15 | Invalid intake, duplicate IDs, or case closure losing saved analysis. |
| [`test_chat.py`](../tests/integration/test_chat.py) | US25, US12 / R12 | Mixed case histories, invalid evidence, partial turns or chat lost after restart. Gemini is doubled. |
| [`test_configuration.py`](../tests/integration/test_configuration.py) | US1 / R1 | Disagreement between configured intake limits, validation and OpenAPI. |
| [`test_context_import.py`](../tests/integration/test_context_import.py) | US18 | Partial writes or source metadata lost between import and MCP retrieval. |
| [`test_context_store.py`](../tests/integration/test_context_store.py) | US18 | Write access, fabricated context or unreadable SQLite treated as an empty result. |
| [`test_contract.py`](../tests/integration/test_contract.py) | US1 / R1 | Divergence between the shipped input examples, JSON Schema and API behavior. |
| [`test_enrichment.py`](../tests/integration/test_enrichment.py) | US3 / R3 | Rejecting cases without enrichment or changing supplied provider payloads. |
| [`test_follow_up.py`](../tests/integration/test_follow_up.py) | US20, US6 / R6 | Analyst feedback mutating prior reports or unrelated hypotheses. |
| [`test_hypotheses.py`](../tests/integration/test_hypotheses.py) | US6 / R6, US8 / R8 | Unsupported hypotheses or confidence pooled across unrelated evidence. |
| [`test_instructions.py`](../tests/integration/test_instructions.py) | US20, US25 | Wrong analyst identity, stale revisions or missing revision history after restart. |
| [`test_language_graph.py`](../tests/integration/test_language_graph.py) | US11 / R11, US26, #187 | Report or provider instructions using a different language from the configured one. |
| [`test_llm.py`](../tests/integration/test_llm.py) | US17, US24, US26 | Untrusted model content changing findings, escaping scope or bypassing approval. |
| [`test_mitre_mapping.py`](../tests/integration/test_mitre_mapping.py) | US5 / R5, US7 / R7 | Unsupported ATT&CK techniques, false associations or missing citations. |
| [`test_model_review_report.py`](../tests/integration/test_model_review_report.py) | US17, US24 | Incorrect primary/fallback reporting or loss of the deterministic report. |
| [`test_pdf_report.py`](../tests/integration/test_pdf_report.py) | US27, US14 / R14 | Unreadable PDF, missing downloads or credentials in exported findings. |
| [`test_pipeline.py`](../tests/integration/test_pipeline.py) | US1–US3 / R1–R3, US7 / R7, US11–US13 / R11–R13 | Intake, LangGraph, local MCP, SQLite and human review losing evidence or saved results. |
| [`test_report_contract.py`](../tests/integration/test_report_contract.py) | US8 / R8, US10–US11 / R10–R11 | Invalid report contracts, numeric confidence or actions without approval. |
| [`test_service.py`](../tests/integration/test_service.py) | US1 / R1, US15 / R15 | Duplicate allocation or lost evidence across concurrent intake and restart. |
| [`test_siem_samples.py`](../tests/integration/test_siem_samples.py) | US1 / R1, US3 / R3, US21 | Sample conversion changing IDs, provider evidence or input-v1.0 validation. |
| [`test_timeline_order.py`](../tests/integration/test_timeline_order.py) | US4 / R4, US7 / R7 | Incorrect UTC order, unstable ties or lost original timestamps. |
| [`test_wazuh_cases.py`](../tests/integration/test_wazuh_cases.py) | US21, US22 | Unreproducible samples, dropped alert types or missing source provenance. |
| [`test_wazuh_enrichment_pipeline.py`](../tests/integration/test_wazuh_enrichment_pipeline.py) | US3 / R3, US21–US22 | Wazuh enrichment rejected by intake or lost during investigation and restart. |

### Security (`security`)

| Test file | Story / requirement | Risk checked |
| --- | --- | --- |
| [`test_export_redaction.py`](../tests/security/test_export_redaction.py) | US14 / R14, US25, US27 | Credentials revealed through nested fields, copied values or exported content. |
| [`test_llm_guard_tasks.py`](../tests/security/test_llm_guard_tasks.py) | US24–US26 | Fabricated references, unsupported conclusions or model suggestions presented as confirmed. |
| [`test_llm_security.py`](../tests/security/test_llm_security.py) | US17, US24–US26 | Untrusted inputs or provider responses altering canonical findings or crossing evidence scope. |

### Regression (`regression`)

| Test file | Story / requirement | Risk checked |
| --- | --- | --- |
| [`test_agent_graph.py`](../tests/regression/test_agent_graph.py) | US4–US11 / R4–R11, US13 / R13 | Changed results or evidence across the direct graph's synthetic cases and review decisions. |
| [`test_finding_review_and_json_export.py`](../tests/regression/test_finding_review_and_json_export.py) | US1 / R1, US13–US14 / R13–R14, US22 | Invalid intake/review, stale decisions, missing exports or client-compatibility regressions. |
| [`test_noise_cases.py`](../tests/regression/test_noise_cases.py) | US1–US2 / R1–R2 | Benign fixture alerts unintentionally dropped or rejected by intake. |
| [`test_prepared_case_regression.py`](../tests/regression/test_prepared_case_regression.py) | US22, US7 / R7 | Prepared Wazuh batches losing provenance, persistence or established report results. |
| [`test_report_audience_evidence.py`](../tests/regression/test_report_audience_evidence.py) | US19, US7–US8 / R7–R8 | Either audience losing evidence provenance, uncertainty or provider attribution. |
| [`test_synthetic_evidence_traceability.py`](../tests/regression/test_synthetic_evidence_traceability.py) | US7 / R7, US3 / R3 | Changed source values, fabricated pointers or merged provider disagreements. |
| [`test_synthetic_hypotheses.py`](../tests/regression/test_synthetic_hypotheses.py) | US6 / R6, US8 / R8 | Benign or contradictory evidence failing to suppress or lower confidence. |
| [`test_synthetic_mitre.py`](../tests/regression/test_synthetic_mitre.py) | US5 / R5 | Fixture techniques or tactics drifting or mapping unsupported events. |
| [`test_synthetic_timeline.py`](../tests/regression/test_synthetic_timeline.py) | US4 / R4, US7 / R7 | Mixed-source times losing offsets, ties, or IDs. |

## Frontend

Run `npm test` from `frontend/` for Vitest and `npm run e2e` for the Playwright
browser flow. The type in this table describes the frontend test itself.

| Test file | Type | Story / requirement | Risk checked |
| --- | --- | --- | --- |
| [`client.test.ts`](../../frontend/src/api/client.test.ts) | Unit | US1 / R1, US16 | Invalid request bodies or loss of API error details. |
| [`Layout.test.tsx`](../../frontend/src/app/Layout.test.tsx) | Integration | US15 / R15, US23 | Wrong starting page, branding or language preference. |
| [`CasePage.test.tsx`](../../frontend/src/features/case/CasePage.test.tsx) | Integration | US12 / R12, US24 | Duplicate investigations, lost reports or silent failure on retry. |
| [`ChatTab.test.tsx`](../../frontend/src/features/case/chat/ChatTab.test.tsx) | Integration | US25, US7 / R7 | Lost conversation context, unusable citations or lost drafts. |
| [`AgentTab.test.tsx`](../../frontend/src/features/case/report/AgentTab.test.tsx) | Integration | US24, US12 / R12 | Candidate assessments, provider failures or citations hidden from the analyst. |
| [`EvidenceTab.test.tsx`](../../frontend/src/features/case/report/EvidenceTab.test.tsx) | Integration | US7 / R7, US12 / R12 | Incorrect evidence display or traceability to original alerts. |
| [`ReportView.test.tsx`](../../frontend/src/features/case/report/ReportView.test.tsx) | Integration | US12 / R12, US14 / R14, US27 | Missing report sections, fallback status, or download links. |
| [`ReviewTab.test.tsx`](../../frontend/src/features/case/report/ReviewTab.test.tsx) | Integration | US13 / R13 | Incomplete finding decisions, stale reviews or lost notes. |
| [`TimelineTab.test.tsx`](../../frontend/src/features/case/report/TimelineTab.test.tsx) | Integration | US4 / R4, US7 / R7 | Wrong event order or missing original timestamps. |
| [`format.test.ts`](../../frontend/src/features/case/report/format.test.ts) | Unit | US4 / R4, US12 / R12 | Misleading display of time or original evidence values. |
| [`pointer.test.ts`](../../frontend/src/features/case/report/pointer.test.ts) | Unit | US7 / R7 | Incorrect JSON Pointer resolution or evidence comparison. |
| [`review.test.ts`](../../frontend/src/features/case/report/review.test.ts) | Unit | US13 / R13 | Wrong finding keys, review suggestions, drafts or structured decisions. |
| [`severity.test.ts`](../../frontend/src/features/case/report/severity.test.ts) | Unit | US7 / R7, US12 / R12 | Incorrect alert severity or invented source fields. |
| [`CasesPage.test.tsx`](../../frontend/src/features/cases/CasesPage.test.tsx) | Integration | US15 / R15 | Lost case state, stale counts or filters. |
| [`NewCasePage.test.tsx`](../../frontend/src/features/new-case/NewCasePage.test.tsx) | Integration | US1 / R1, US16 | Failed upload/paste or an incorrect handoff from intake. |
| [`jsonText.test.ts`](../../frontend/src/features/new-case/jsonText.test.ts) | Unit | US1 / R1, US16 | Invalid JSON accepted or useful validation locations lost. |
| [`session.test.tsx`](../../frontend/src/session/session.test.tsx) | Integration | US13 / R13, US15 / R15 | Analyst session state lost or attributed incorrectly. |
| [`alpha-flow.spec.ts`](../../frontend/e2e/alpha-flow.spec.ts) | End-to-end | US12–US16 / R12–R15, US24, US27 | Browser-to-backend intake, review, reopen, duplicate handling or PDF regressions. |
