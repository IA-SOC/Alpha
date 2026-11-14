# #149 — Prepared Wazuh regression

Delivery scope agreed with the project owner on 2026-11-13: synthetic expected
outcomes while Aligo's incident labels are unavailable. Real labelled accuracy
evaluation remains deferred; no customer verdicts are inferred.

The manifest-driven tests exercise the real API/local MCP agent, original intake,
duplicate rejection, report validation, resolvable evidence, pending human review
and identical results after reopening SQLite. Synthetic cases cover the 50-alert
boundary plus a remainder, zero/one/multiple native MITRE techniques, candidate
status and Wazuh provenance. Expected IDs are authored from input rule metadata,
not copied from generated reports. Empty manifests, duplicate paths and path
escapes are rejected.

## External cases

Private data remains outside the repository. From the application root:

```powershell
$env:WAZUH_REGRESSION_DIR='D:/Repositorios/private-data/aligo-148-cases'
.\.venv\Scripts\python.exe -B -m pytest tests/test_prepared_case_regression.py -q -p no:cacheprovider --tb=short --show-capture=no
```

Without the variable, the external test skips. Invalid configured datasets fail.
All manifest cases run sequentially with temporary databases. LLM_PROVIDER=none
and the shared test configuration disables automatic investigation. This tests
the local agent, not live Gemini.

Unlabelled private cases check contract/persistence/traceability, not field
accuracy. Labelled evaluation belongs with #150 once Aligo supplies reviewed labels.

## Verification

Base 2e85a0f (merged #176), Windows/Python 3.12.2; no dependency installs.
The three explicit synthetic scenarios passed in 19.42s. Final pre-PR checks
are recorded below.

Historical only: on dfee0e0, 2026-11-11, two synthetic prepared cases and all 58
external cases passed intake, local-agent, traceability and restart checks in
501.12s. That is not current verification of the changed MITRE mapping.

Final combined verification on 2e85a0f plus both task changes:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_prepared_case_regression.py tests/test_wazuh_cases.py tests/test_llm_security.py tests/test_llm.py tests/test_chat.py tests/test_prompts.py -q -p no:cacheprovider --tb=short
.\.venv\Scripts\python.exe -m ruff check app tests demo/run_pipeline.py demo/verify_local.py --exclude tests/test_agent_graph.py
git diff --check
```

79 passed, 1 skipped (external dataset not configured), 1 strict xfail (semantic
claim rejection), 94.48s. CI-scope Ruff and whitespace checks passed. API/MCP
tests ran outside the Windows sandbox. The full project suite was not run locally.
