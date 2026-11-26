# Sprint 6 verification for #216

Use only the two repository fixtures below. They use input v1.0 and their alert
IDs are distinct. Keep the original alert values unchanged and use a fresh
SQLite database per run.

| Scenario | Fixture under `examples/sprint3/` | Expected rule output | Evidence IDs |
| --- | --- | --- | --- |
| A | `us6_attack.json` | At least one predefined hypothesis | `login-1`, `login-2` |
| B | `us6_benign.json` | Zero predefined hypotheses | `backup-1`, `job-1` |

## Existing-flow checks

From `soc-ai-analyst-sprint2/`, with Python 3.12 and dev dependencies installed:

```sh
python -m pytest -q tests/test_automatic_investigation.py tests/test_chat.py tests/test_instructions.py tests/test_pdf_report.py tests/test_export_redaction.py tests/sprint3/test_us6_cases.py
python -m ruff check scripts/smoke_gemini.py tests/test_chat.py
```

Run `npm ci`, `npm test`, `npm run typecheck` and `npm run e2e` from
`frontend/` with Node 22.22 or later. The existing Playwright configuration
expects Chrome and uses an isolated database when its ports are free. Run the
offline checks without a Gemini key. Test doubles and rules-only fallback
demonstrate application behavior. Record those results separately from live calls.

## Live acceptance in the browser

Set `GEMINI_API_KEY` through a local secret environment or masked console
prompt. Set `GEMINI_MODEL` to a model available to that credential. In
PowerShell, from `soc-ai-analyst-sprint2/` with the virtual environment active:

```powershell
$secret = Read-Host "Gemini API key" -AsSecureString
$env:GEMINI_API_KEY = [System.Net.NetworkCredential]::new('', $secret).Password
Remove-Variable secret
$env:GEMINI_MODEL = Read-Host "Gemini model ID"
$env:LLM_PROVIDER = "gemini"
$env:SOC_AUTO_INVESTIGATE = "true"
$env:GEMINI_RETRY_ATTEMPTS = "0"
$env:GEMINI_FALLBACK_MODELS = " "
$env:LLM_TIMEOUT_SECONDS = "90"
$env:CASE_DATABASE_PATH = Join-Path ([System.IO.Path]::GetTempPath()) ("soc216-" + [guid]::NewGuid() + ".sqlite3")
git rev-parse HEAD
python --version
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

The whitespace-only fallback value keeps the variable defined in Windows
PowerShell and is ignored by the fallback parser. In a second terminal from
`frontend/`, run `node --version` and `npm run dev -- --port 5173 --strictPort`.
Open `http://localhost:5173` and sign in as a test analyst.

1. Submit A and B from **New case**. Let automatic investigation finish.
   Record both application UUIDs. Check **Agent analysis** against
   `GET /api/v1/cases/<uuid>/investigation`. Require
   `report.model_review.provider=gemini`, `status=ok`, a successful model
   attempt and a visible initial assessment for both. Resolve its citations in
   the **Evidence** tab against the fixture. Check that any Gemini hypotheses
   carry the candidate label and remain distinct from the rule hypotheses.
   Record absent or rejected candidates explicitly. A result with no candidates
   leaves the live candidate-label check unexercised.
2. In A's **Chat**, attach `login-1` and ask “What does alert login-1 show?
   Cite its evidence.” Open the citation and inspect its details. Ask “What
   evidence is missing to confirm your previous answer?” Verify that the
   reply addresses the previous exchange and that both answers use A's
   evidence. Close and reopen A. Switch to B's chat and verify its history
   is empty. Return to A and verify both exchanges.
3. Stop Uvicorn, then run the same command in the same terminal with the same
   `CASE_DATABASE_PATH`. Reload A and B. Verify the two exchanges are still
   in A and there are none in B. Repeat from the dashboard when #203 is
   integrated. Verify the saved report renders both audiences when #208 is
   integrated. Record the locale and output behavior for #187.
4. Before sending an instruction for A, save one `mcp:<run_id>:…` key from
   `GET /api/v1/cases/<uuid>/chat-evidence`. After #209 is integrated, submit
   “Focus on the evidence supporting login-1 and describe what remains
   unverified.” Verify the incremented revision and instruction history.
   Before #209, the same request can be checked through the API by posting
   `{"analyst_id":"<name>","instruction":"Focus on login-1","revision":1}`
   to `/api/v1/cases/<uuid>/instructions` with `X-Analyst-Id: <name>`. Read
   the current revision before submitting. The API check does not cover the
   instructions screen.
5. Send the saved old reference and a nonexistent reference in separate
   requests to A's `POST /api/v1/cases/<uuid>/messages`. Each request uses
   the same analyst header and a body with `analyst_id`, `message` and a
   one-element `evidence_refs` array. Verify HTTP 422 and unchanged history.
   The UI may remove an expired selection after a refresh. The backend stale
   reference regression and frontend error handling checks cover the two parts
   independently when the browser cannot submit the stale selection directly.
6. Review the revised findings in A, record your decisions and a note, then
   export JSON and PDF from the same case. Check the case ID and saved review in
   both downloads and the revision and instruction history in JSON. Check that
   the review decision is visible and the case status remains under analyst control.
7. To check bad configuration without a provider call, stop Uvicorn, remove
   `Env:GEMINI_API_KEY` and restart against the same database. Send a valid
   chat question. Verify the visible 503 and retained draft, with no exchange
   appended. Use the existing simulated 502/504 tests to verify provider failure
   and timeout. Identify any network or quota failures observed on a live run
   separately from these simulations.

Budget **five** provider requests for the browser run. This allows one per
automatic investigation, one per chat turn and one for the instruction rerun.
No retries or fallbacks are configured. Stop on a failed call and check provider
usage before retrying. Record report `model_review.attempts` and `usage`, chat
HTTP outcomes and provider-side counts if available. Chat responses do not
expose token usage. Exported and captured evidence must contain synthetic data
only and omit credentials.

For a separate API smoke run, use `python scripts/smoke_gemini.py` with the
model and key configured. It uses an additional budget of at most **four**
provider requests and checks assessment, citations, candidate tagging, two
chat turns and histories after reopening the same database in a new app
instance. It emits JSON lines suitable for the evidence record. Use the browser
run to verify a full process restart and the UI.

## Evidence record

Record the exact commit SHA, OS, Python/Node/browser versions, model ID,
commands, scenario, case UUID, outcome, observed requests versus budget,
reported token usage, and any defect or dependency still open. Record the
human reviewer, actual effort and how AI was used after delivery. Repeat the UI
checks against the revision that integrates the required Sprint 6 changes.
