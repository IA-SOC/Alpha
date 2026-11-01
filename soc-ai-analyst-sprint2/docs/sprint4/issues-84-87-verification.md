# Sprint 4: confidence and JSON report validation (#84, #87)

Implementation on `feat/84-87-confidence-report-validation`, based on
`c2c91cb156e99522176fb90e4b066df6e528ee1a` (also `origin/main` at verification).
Verification date: 2026-10-31. Environment: Windows, Python 3.12.2, existing
project `.venv`; no dependency installation or demo regeneration.

## Contract and compatibility

- [#84](https://github.com/IA-SOC/Alpha/issues/84): preserve the existing wire
  values `insuficiente`, `baja`, `media`, `alta` (insufficient, low, medium, high).
  Every hypothesis requires nonblank justification and evidence. Low/medium/high
  require supporting evidence; insufficient may cite only contradicting evidence.
  Supporting and contradicting arrays enforce their respective evidence roles.
  Numeric/percentage confidence and probability/score side fields are rejected.
  The existing deterministic rubric, contradiction/timestamp downgrades and
  synthetic cap are unchanged; provider scores never promote confidence.
- [#87](https://github.com/IA-SOC/Alpha/issues/87): enforce the existing
  [v1.1 schema](../../skills/soc-case-investigator/references/report-schema.json)
  at runtime for timeline, MITRE mappings, hypotheses/confidence, blast radius,
  recommendations and required metadata. The serializer preserves values,
  Unicode, evidence and extension fields and rejects non-finite JSON numbers.
  The graph derives its schema ID from that schema. A declared schema version
  must match v1.1; legacy reports without methodology remain readable.
- The graph serializer, standalone skill validator and backend traceability
  boundary share structural validation. Existing case-reference, original-value,
  pointer and audience-projection checks remain in place. Backend validation does
  not trust a stale agent `validation.ok` flag.
- `jsonschema==4.26.0` moves from dev requirements to runtime requirements. It
  was already installed and required transitively by MCP; no new library is added.
- The six maintained synthetic report artifacts round-trip unchanged. The old
  `holdout_kerberoast.json` lacks action `approval_status` and `hypothesis_ranks`
  already required by the previous schema. It remains unchanged and is explicitly
  tested as invalid; approval metadata is never invented to repair it.

## Executed verification

Commands run from `soc-ai-analyst-sprint2/` using the existing interpreter:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_report_contract.py tests/test_pipeline.py tests/test_hypotheses.py tests/test_report_formatter.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_report_contract.py -q
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m ruff check app tests demo/run_pipeline.py demo/verify_local.py --exclude tests/test_agent_graph.py
.\.venv\Scripts\python.exe -m ruff check core/report_contract.py --select E,F,I
.\.venv\Scripts\python.exe -m ruff check agent/graph.py skills/soc-case-investigator/scripts/validate_report.py --select F
git diff --check
```

The initial focused run stalled under the documented Windows sandbox socket
restriction and was interrupted. The run outside the sandbox passed **105 tests**.
After adding three backend stale-validation regression cases, contract-only tests
passed **67 tests**. The final full suite, including those three new backend
checks, passed **403 tests, 2 skipped in 264.59 seconds** outside the sandbox.
The skips require opt-in local customer data (`ALIGO_PREPARED_DIR` and the
customer ZIP). All listed lint scopes and `git diff --check` passed. No
whole-repository lint claim is made.

## Acceptance boundary and AI collaboration

Automated tests check structure, supporting references, rubric behavior, strict
serialization, API/agent integration, persistence and review compatibility. They
do not establish the semantic truth or calibration of security inferences.

Codex assisted source inspection, implementation, test authoring and verification.
Owner review/demo and actual human effort/AI-use logging remain for the assigned
owner; no human review or work duration is fabricated. Issues remain open pending
that acceptance evidence. No workbook or GitHub Projects status is changed.
