# S5-US14-T01 — JSON export redaction (#151)

`GET /api/v1/cases/{case_id}/export` applies redaction to a detached copy of the
stored investigation, including older stored results. The frontend's existing
Export JSON link uses this endpoint. Original intake, stored reports and internal
review responses retain their evidence.

The export policy replaces values with `[REDACTED]` for credential fields,
including passwords, API keys, access/refresh/session tokens, authorization,
cookies, private keys, credentials and connection strings. Matching ignores
case, underscores and hyphens and supports dotted keys. Evidence pointer/value
pairs targeting these fields are also redacted. Field locations remain visible.
Copies of identified secret strings in narrative fields are redacted throughout
the exported document. This conservative replacement may mask benign text that
matches a secret. Free-text matching covers password/token assignments, Basic
and Bearer authentication, URL credentials and PEM private keys.

This policy is credential-focused. It does not anonymize all names, IP addresses
or arbitrary personal information. Unlabelled secrets in arbitrary prose and
unknown credential field names require additional policy rules. Exported
redacted values are unsuitable for checking equality against the original
evidence; validation fields describe the stored investigation before redaction.

Verification uses synthetic credentials in `tests/test_export_redaction.py`.
It covers nested and dotted fields, free text, evidence pointers, repeated HTTP
exports of a stored result and preservation of the original intake and storage.

Verified 2026-11-10 on Windows, Python 3.12.2, branch
`feat/151-json-export-redaction`, base `82ff5d9`, with the task changes applied.
Commands executed from the application root using `.venv/Scripts/python.exe`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_export_redaction.py tests/test_sprint4_isabella.py -q
.\.venv\Scripts\python.exe -m ruff check app tests demo/run_pipeline.py demo/verify_local.py --exclude tests/test_agent_graph.py
git diff --check
```

Results: 37 passed, 1 skipped (private Aligo cases require `ALIGO_PREPARED_DIR`),
CI-scope Ruff passed, whitespace check passed. TestClient stalled inside the
sandbox; the completed test run used approved execution outside it. The existing
user change to `frontend/package-lock.json` was present before this task.
