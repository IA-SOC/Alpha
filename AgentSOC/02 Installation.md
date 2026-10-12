---
tags: [agentsoc, usage]
aliases: [Install AgentSOC, Setup]
updated: 2026-10-11
---

# Installation

## Requirements

- **Python 3.12**, the version the suite was verified with. Python 3.14 is in the CI matrix but was not run remotely.
- **Git**, if you will clone the repository.
- Recommended: **VS Code** with the Microsoft **Python** extension, which includes Pylance and the Python Debugger.

No API key, external database, SIEM access, intelligence subscription or model download is needed.

## Steps

Open PowerShell in the code folder:

```powershell
cd "C:\Users\Caliche\Documents\UTP\Implentde prueba\SOC_AI_Analyst_Sprint2_Integrated\soc-ai-analyst-sprint2"
```

Create the environment and install the dependencies (first time only):

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

After that, just activate it:

```powershell
.venv\Scripts\Activate.ps1
```

The prompt must start with `(.venv)`.

> [!tip] PowerShell blocks activation
> If you see "running scripts is disabled on this system", run once:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

On Linux or macOS, activation is `source .venv/bin/activate`.

> [!note] One environment for everything
> In the previous version, the backend and the agent had **two** virtual environments, and the backend needed `AGENT_DIR` to find the agent. Sprint 2 has a single `.venv` and no extra variables. See [[19 Changes from the previous version]].

## Check that it works

```powershell
python -m pytest -q
```

It should end with `184 passed`. If it fails, see [[13 Troubleshooting]].

## Dependencies

Direct dependencies are **pinned** to the tested versions in `requirements.txt`:

| Package | Version | For what |
| --- | --- | --- |
| `fastapi` | 0.142.1 | The HTTP API |
| `pydantic` | 2.13.5 | Contract and output models |
| `uvicorn` | 0.54.0 | The web server |
| `rfc3339-validator` | 0.1.4 | Timestamp validation in the contract |
| `mcp` | 1.30.0 | The analysis MCP servers and the client that calls them |
| `langgraph` | 1.2.14 | The six-phase flow, the case state and the human-review pause |

`requirements-dev.txt` adds the test and lint tools. The full installed environment is recorded in `docs/verification/environment.txt`.

## VS Code

1. *File → Open Folder* and choose `soc-ai-analyst-sprint2`.
2. `Ctrl+Shift+P` → **Python: Select Interpreter** → `.\.venv\Scripts\python.exe`.
3. Open a terminal with `` Ctrl+` ``. It should activate the venv on its own.
4. Optional: Testing panel (flask icon) → *Configure Python Tests* → **pytest** → root folder.

Next: [[03 Daily use]] · Back to [[00 Home]]
