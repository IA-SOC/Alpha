# Issue #66 verification — 2026-10-26

Branch: `feat/66-rule-based-report-formatter`. Base revision:
`86005d475462c62e9728b2ef71644e10405d26ce`, plus local uncommitted formatter,
agent/rendering/traceability integration, tests and documentation changes.

Environment: Windows, Python 3.12.2, project `.venv`. Dependencies synchronized
with the current `requirements-dev.txt`: FastAPI 0.161.1, MCP/MCP types 2.3.0,
LangGraph 1.2.16, Pydantic 2.13.5, pytest 9.1.1 and ruff 0.16.9.
Tests that start asyncio/MCP run outside the sandbox because Windows asyncio
requires a local socket that was blocked in the earlier US3 sandbox run.

## Executed checks

Working directory: `D:/Repositorios/Alpha/soc-ai-analyst-sprint2`.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests -q --tb=short
.\.venv\Scripts\python.exe -m pytest tests/test_report_formatter.py -q
.\.venv\Scripts\python.exe -m ruff check app tests demo/run_pipeline.py demo/verify_local.py --exclude tests/test_agent_graph.py
.\.venv\Scripts\python.exe -m ruff check agent/graph.py agent/render.py --select F
git diff --check
```

Full-suite result after the validator fix: **303 passed, 1 skipped in 161.95s**.
The skipped test is the opt-in private Aligo ZIP test. A final presentation-only
adjustment removed internal paths from summary Markdown (retaining JSON provenance)
and improved asset-count wording; formatter tests and lint passed afterward.
Final formatter unit check: **12 passed in 0.32s**. Exact CI lint scope passed;
the separately scoped agent F checks also passed. No whitespace errors.

The API integration assertions cover two English audience sections, unchanged
canonical report schema validation, traceability, persistence after database
reopen and regeneration after human correction. The direct-agent regression
suite exercises all six phases and multiple synthetic scenarios. Formatter
tests preserve all technical data and check missing information, conflicting
evidence, no hypotheses, confidence levels, source pointers and hostile markup.

## Resolved failures during verification

The first full run used a stale virtual environment: MCP 1.30.0 was still
installed although main requires MCP 2.3.0. Server startup failed with
`ModuleNotFoundError: mcp.server.mcpserver` (42 failures, 81 errors, 180 passed,
1 skipped). Installing the versions already fixed in requirements resolved
that environmental mismatch; no dependency files or MCP server code were changed.

The next run had 302 passed, 1 failed, 1 skipped. The new audience check correctly
rejected stale views but obscured the existing invalid-alert diagnostic. The
validator now retains both canonical validation errors and audience consistency
errors. The original regression test remains unchanged.

## Scope and review material

The private Aligo ZIP test is opt-in and is not part of this run. No claim of
customer-labelled accuracy, Gemini integration or live SIEM/provider access is
made. Original synthetic reports and the static demo were not regenerated.

A separate local preview was deliberately generated from the existing synthetic
`data/reportes_sinteticos/bruteforce_wazuh.json` at
`D:/Repositorios/docs/issue-66-report-preview.md` for human review of presentation.
It is outside the repository and contains synthetic data only. The preview is
not a new investigation or a substitute for the live pipeline tests above.

The contract and original-language quotation policy are documented in
`US19-issue-66-report-formatter.md`. No workbook status, issue state, commit or
pull request was changed by this implementation turn.
