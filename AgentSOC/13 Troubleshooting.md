---
tags: [agentsoc, usage, troubleshooting]
aliases: [Errors, FAQ, Troubleshooting]
updated: 2026-10-11
---

# Troubleshooting

## Installation and environment

> [!question]- "Running scripts is disabled on this system"
> PowerShell blocks `Activate.ps1`. Run once:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

> [!question]- `ModuleNotFoundError: No module named 'fastapi'` (or `mcp`, `langgraph`)
> The venv is not active or you are using another Python. Check that the prompt starts with `(.venv)` and run `.venv\Scripts\Activate.ps1`. In VS Code, choose the interpreter `.\.venv\Scripts\python.exe`.

> [!question]- `can't open file 'agent/graph.py'` or `No such file or directory: 'data/...'`
> You are in the wrong folder. Paths are relative to `soc-ai-analyst-sprint2/` (the one with `app/`, `agent/` and `core/`).

> [!question]- The venv stopped working after moving the folder or changing machines
> A venv stores absolute paths. Delete it and create it again (see [[02 Installation]]).

> [!question]- `pip check` reports conflicts after installing something
> Direct dependencies are pinned. If you add a package, pin it too and rerun `python -m pip check` and the tests.

## The API

> [!question]- `422` with a `VR-xx` rule on `POST /cases`
> The case breaks the contract. The response lists each issue with its rule and path. Common ones:
> - `VR-10`: `alert_id` does not match the ID inside `raw_alert` at the configured path (`/event/id` for Elastic, `/id` for Wazuh). Fix the case or set `ELASTIC_ALERT_ID_POINTER` / `WAZUH_ALERT_ID_POINTER` **before** starting the server.
> - `VR-11`: duplicate `alert_id` within the case.
> - `VR-05`: a timestamp without a zone in the envelope.
> - An unknown top-level field: the envelope is strict. Put custom data inside `raw_alert`.

> [!question]- `409` on `POST /cases`
> That submitted `case_id` was already accepted. Use a new one. `demo/verify_local.py` randomizes it for this reason.

> [!question]- `404` on `/cases/{id}/...`
> You used the submitted ID instead of the **UUID** returned by intake, or the database is a different file (`CASE_DATABASE_PATH`).

> [!question]- `422` on `/cases/not-a-uuid/...`
> The path is not a valid UUID.

> [!question]- `404` on `GET /investigation`
> The case exists but has not been investigated yet. Call `POST /investigate` first.

> [!question]- `502` "Investigation failed; accepted evidence is retained"
> The agent, an MCP server, the skill validator or the traceability check failed. The server log has the exception type and message. The case stays stored: fix the cause and call `POST /investigate` again.

> [!question]- `504` after 300 seconds
> The investigation exceeded the timeout. It was cancelled. Check whether an MCP server hangs on start-up (try `python agent/graph.py data/synthetic/phishing_ecs.json`).

> [!question]- `409` on `POST /review` "No resumable investigation in this process"
> The server restarted since the investigation, or the case was already reviewed. Review checkpoints live in memory. Call `POST /investigate` again (it replaces the last report) and then review. See [[12.5 Persistence and performance]].

> [!question]- `409` "The investigation is not awaiting review"
> The graph is no longer paused at review, for example because the decision was already recorded.

> [!question]- `422` on `POST /review`
> `status` must be `validated`, `corrected` or `rejected`. `analyst` and `notes` are mandatory and cannot be blank. No extra fields are allowed.

> [!question]- Strange review behavior with several workers
> Run **one** Uvicorn worker (`--workers 1`). Checkpoints and locks are per process: a review can hit a worker that never ran the investigation.

> [!question]- `curl` fails in PowerShell
> Use `curl.exe`, or Swagger at `http://127.0.0.1:8000/docs`.

## The agent (CLI)

> [!question]- Many `Processing request of type CallToolRequest` lines
> Normal: these are MCP server messages on stderr. Add `2>$null` to hide them.

> [!question]- `UnicodeEncodeError: 'charmap' codec can't encode character`
> The Windows console uses cp1252 and cannot print characters like `→` or `—`. `agent/graph.py`, `agent/run_synthetic.py` and `orchestrator/client.py` already force UTF-8. In your own scripts, add `sys.stdout.reconfigure(encoding="utf-8")` or run `$env:PYTHONIOENCODING = "utf-8"` first.

> [!question]- No report and the validator says `REPORT VALIDATION FAILED`
> The graph ended at phase 5 without reaching review. The error list says what fails, for example `unknown alert_id 'x'`. Most common: a new rule produces a malformed technique ID (it must be `T1234` or `T1234.567`).

> [!question]- I passed a v1.0 contract file to `agent/graph.py` and the result looks wrong
> The CLI does not unwrap the contract. Use the API. See [[04 Case format#Legacy direct format (CLI)]].

> [!question]- The agent detects nothing in my case
> Most likely no rule name or tag contains catalog words. See [[10 Limitations#The rule catalog]] and [[12.1 Adding a MITRE rule]].

> [!question]- All hypotheses are `media` at most
> The case has `"synthetic": true`. That is intentional: the skill lowers confidence on synthetic data.

> [!question]- Two alerts with the same technique gave two `baja` hypotheses instead of one `media`
> Intentional. They are not `related`, so each is analysed alone. See [[16 Correlation engine]].

## Tests

> [!question]- `test_tecnicas_y_formato_esperados` fails after changing rules
> Expected if the new rule detects something in a synthetic case. Check it is correct and update `EXPECTED_TECHNIQUES` in `tests/test_agent_graph.py`.

> [!question]- Tests are slow
> Agent and pipeline tests start real MCP servers. The full suite takes about 20 s on the verification machine.

> [!question]- `demo/verify_local.py` gets "connection refused"
> Server and client must run in the same environment. `verify_local.py` starts both itself; do not split them across isolated sessions.

## Git and GitHub

> [!question]- "CRLF will be replaced by LF" warnings
> They come from `.gitattributes`, which normalizes line endings. They are not errors.

> [!question]- `data/cases.sqlite3` shows up in `git status`
> It should not: `.gitignore` excludes local databases while keeping the synthetic `data/` files.

Back to [[00 Home]]
