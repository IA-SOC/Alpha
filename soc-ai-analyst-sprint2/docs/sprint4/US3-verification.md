# US3 verification — 2026-10-26

Branch: `feat/us3-siem-enrichment`. Base revision:
`e60f3d1f14170e31e8b24c9d857731afcf24f8ae`, with uncommitted US3 adapter/importer,
two test modules, application README and Sprint 4 documentation changes.
Pre-existing changes in the repository-root README, `AgentSOC/02 Installation.md`
and untracked Obsidian files were preserved and are not part of this work.

Environment: Windows, Python 3.12.2, project `.venv`; installed using
`python -m venv .venv` and `.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`.
Relevant resolved versions: pytest 9.1.1, ruff 0.16.9, FastAPI 0.142.1,
Pydantic 2.13.5, MCP 1.30.0, LangGraph 1.2.14, Starlette 1.10.0, AnyIO 4.15.1.

## Commands actually executed

From `D:/Repositorios/Alpha/soc-ai-analyst-sprint2`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_wazuh_enrichment.py tests/test_ioc_integration.py -q
```

Result: **27 passed in 0.14s**.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_wazuh_enrichment.py tests/test_wazuh_enrichment_pipeline.py tests/test_ioc_integration.py tests/test_pipeline.py -q
```

Result: **43 passed, 1 skipped in 20.44s**. The skipped test requires the private
customer ZIP and was executed separately below. Includes real LangGraph/local
MCP, report validation, traceability, human-review state and database reopen.

```powershell
$env:ALIGO_WAZUH_ZIP='D:\Repositorios\wazuh-alerts-2026-08-10_16.zip'
.\.venv\Scripts\python.exe -m pytest tests/test_wazuh_enrichment_pipeline.py::test_customer_sample_compatibility -q -s --basetemp D:/Repositorios/.us3-private-verified
```

Result: **1 passed in 9.68s**. Seven customer alerts: four provider records plus
three referenced original alerts. Three enrichments preserved; one diagnostic
`no_supported_observable` for the error-only VirusTotal record. Report validation
and traceability passed, status reached `pending_review`, and accepted input and
report enrichments survived database reopen.

Samples are from archive member `wazuh-alerts-2026-08-10_16/ossec-alerts-10.json.gz`:

| Provider outcome | NDJSON line |
| --- | ---: |
| VirusTotal found | 265 |
| VirusTotal not found | 271 |
| VirusTotal error | 2048 |
| MISP | 156555 |

No customer alert contents were added to tracked fixtures or this document.
The local verification database is outside the repository under the dedicated
pytest temporary directory. These records are compatibility samples, not labels
of true attacks or a performance benchmark.

```powershell
.\.venv\Scripts\python.exe -m ruff check app tests demo/run_pipeline.py demo/verify_local.py --exclude tests/test_agent_graph.py
git diff --check
```

Results: **All checks passed** for the existing CI lint scope; no whitespace
errors. Git emitted line-ending notices for pre-existing user files.

## Environment issues and limits

The initial sandboxed dependency install failed DNS resolution; the authorized
retry outside the sandbox succeeded. Sandboxed integration attempts stalled
before application execution: pytest faulthandler showed Windows asyncio's local
`socketpair()` blocked in `accept()` while starting TestClient. Those attempts were
interrupted. The successful integration commands above ran outside the sandbox.
No application workaround was introduced for this environment restriction.

The full test suite and HTTP demo were not run; relevant tests and the exact CI
lint scope were run. No demo/report fixtures were regenerated. No live SIEM,
n8n, provider API, Gemini integration, adjudicated accuracy or complete-dataset
compatibility is claimed. The workbook's planning/acceptance status is unchanged.
