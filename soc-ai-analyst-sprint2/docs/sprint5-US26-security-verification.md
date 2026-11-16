# #154 — Security regression coverage

Base 2e85a0f, Windows/Python 3.12.2. No live provider calls or dependency installs.

Tests cover injection in untrusted evidence, foreign/malformed references,
preservation of original input, rejection of bad items without losing valid
siblings, and malformed ranks/assessments. The guard now checks types before
hash-based membership, preventing list/dict TypeError and bool/float rank aliasing.

A real graph/local MCP test supplies an unsupported claim through a fake provider
and checks that canonical hypotheses, MITRE mappings, recommendations and pending
human review remain identical to the baseline.

## Known semantic-safety defect

One strict xfail preserves the unmet requirement to reject invented exfiltration
with a valid login-alert citation. The guard validates structure and references,
not whether prose follows from evidence. It remains reproducible without Aligo
labels or live Gemini. A future fix produces XPASS and requires removing the
marker. The unsafe behavior is not reclassified as passing acceptance.

This delivery provides security coverage and type hardening, not proof that all
unsupported claims or injection variants are prevented. Semantic rejection is a
documented follow-up; human review remains required.

## Verification

Earlier focused guard run: 20 passed, 1 strict xfail, 3 deselected.
Final pre-PR checks including graph containment are recorded below.

Final combined verification on 2e85a0f plus both task changes:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_prepared_case_regression.py tests/test_wazuh_cases.py tests/test_llm_security.py tests/test_llm.py tests/test_chat.py tests/test_prompts.py -q -p no:cacheprovider --tb=short
.\.venv\Scripts\python.exe -m ruff check app tests demo/run_pipeline.py demo/verify_local.py --exclude tests/test_agent_graph.py
git diff --check
```

79 passed, 1 skipped (external dataset not configured), 1 strict xfail (semantic
claim rejection), 94.48s. CI-scope Ruff and whitespace checks passed. API/MCP
tests ran outside the Windows sandbox. The full project suite was not run locally.
