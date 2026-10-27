# Issue #66 — Rule-based reports for two audiences

## Agreed scope

Issue: https://github.com/IA-SOC/Alpha/issues/66 (current product mapping US19;
the issue title retains historical `S4-US9-T07`). The user confirmed on
2026-10-26 that both sections use rules, authored output is English, and this
delivery also connects the formatter to the agent. Aligo requested technical and
non-technical parts without prescribing a template. The layout below is a project
design choice, not an externally certified reporting standard.

## Data contract and responsibility

`app.services.report_formatter.format_report(report)` is a pure formatter over an
existing investigation report. It returns an additive `audience_sections` object:

| Field | Meaning |
| --- | --- |
| `formatter_version` | `soc-audiences-rules-v1` |
| `language` | `en`, the language of authored headings and rule templates |
| `technical.title` | Technical findings |
| `technical.data` | Deep copies of source report fields, including evidence, IDs, original values, confidence basis, limitations and human review |
| `technical.report_paths` | JSON pointers to the corresponding fields in the source report |
| `non_technical.title` | Non-technical summary |
| `non_technical.observations` | Alert processing and observed timeline counts |
| `non_technical.hypotheses` | Candidate explanations, confidence, support/contradiction counts, alternatives and unknowns |
| `non_technical.potential_impact` | Separate observed, suspected and confirmed asset counts; no invented financial/business impact |
| `non_technical.proposed_actions` | Existing proposals, translated through fixed templates where known, requiring human approval |
| `non_technical.limitations` | Coverage, input gaps, supplied intelligence limitations and source-specific limitations/open questions |
| `non_technical.review` | Current human review status; approval is not proof of an attack |

Each summary claim carries `text` and `report_paths`. These pointers resolve into
the canonical report, whose evidence still points to the original accepted case.
They are not a replacement for original raw-alert pointers. Existing input v1.0,
report v1.1 fields and ordinal confidence values are unchanged. No new required
field is imposed on older reports. An optional extension uses the report schema's
existing allowance for extra root fields.

The formatter does not call Gemini, change hypotheses, correlate alerts, calculate
confidence, query intelligence or execute responses. Francisco can continue to
produce the canonical report; this integration handles its audience presentation.
Santiago can consume the extension through the existing investigation response;
no additional endpoint or database migration is introduced here.

## Language and conservative rendering

Authored headings and narrative rules are English. Known confidence labels,
technique descriptions, actions and limitation templates have fixed English
wording. Unknown/ambiguous technique descriptions use a neutral label and point
to the original finding; the formatter does not infer a new technique.

Original evidence, alert names, analyst notes and source text are not translated
or rewritten. The technical section explicitly labels them as original-language
source records. Unknown action text stays in the technical record; unknown
limitations are explicitly quoted as original wording in the summary rather than
omitted or mistranslated. Consequently a source quotation can still be Spanish or
another language even though the report presentation is English. Arbitrary
automatic translation would require a separate agreed translation strategy.

Summary markup is escaped. Technical source records are displayed as indented
JSON, preserving arbitrary nested fields without treating embedded text as markup
or instructions. Provider scores do not become confidence or attack verdicts.
No hypotheses does not mean no incident; observed assets are not compromised
assets; correlation/time ordering does not establish causality.

## Agent, API and review integration

In phase 5, the graph builds its canonical report, attaches the audience views,
checks their consistency, executes the existing report validator and renders both
sections to Markdown. Invalid report validation still prevents human review.
The six graph phases and single-worker/in-memory checkpoint constraints remain.

On analyst review, the graph rebuilds the derived views after updating the review
metadata, so rendered status cannot stay `pending` after correction/rejection.
The backend traceability validator rejects audience views that differ from a
fresh projection of the source report. The older report shape remains supported
and uses the legacy renderer when the extension is absent.

The existing SQLite investigation result stores the extended report and Markdown.
`POST /api/v1/cases/{id}/investigate`, `GET /api/v1/cases/{id}/investigation` and the
review response expose it through `report.audience_sections`. No change is made to
the static demo or original fixtures. This does not implement per-finding review,
version history, new UI rendering or independent report-file export.

## Verification

Unit tests: `tests/test_report_formatter.py` covers deterministic/non-mutating
formatting, exact technical data, resolvable summary references, all confidence
levels, conflicting evidence counts, empty findings, unknown source text,
incomplete reports, stale review state, hostile markup and older report rendering.

`tests/test_pipeline.py` verifies that the real API/LangGraph/MCP path returns both
English sections, preserves them across database reopen and refreshes them after
human correction. Full-suite execution also exercises the direct-agent route.

Commands and actual results are recorded in `issue-66-verification.md`.
