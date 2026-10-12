---
tags: [agentsoc, usage]
aliases: [Commands, How to use the agent]
updated: 2026-10-11
---

# Daily use

Every command runs from `soc-ai-analyst-sprint2/` with the venv active (see [[02 Installation]]).

There are two ways in:

| Way | When to use it | Input format |
| --- | --- | --- |
| **The API** (FastAPI) | The normal path: intake, correlation, IoC, investigation, review | Intake contract v1.0 |
| **The agent CLI** (`agent/graph.py`) | Quick checks of the six phases on a legacy case | Direct alerts (internal, ECS, Wazuh) |

Formats in [[04 Case format]].

## 1. The full pipeline through the API

Start the server (a single worker, see [[15 The backend#Why a single worker]]):

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

In a second terminal, submit a case:

```powershell
curl.exe -s -X POST http://127.0.0.1:8000/api/v1/cases -H "Content-Type: application/json" --data-binary "@examples/sprint2_demo.json"
```

The response is `201` with a `case_id` (UUID). Use that UUID in the next calls:

```powershell
curl.exe -s http://127.0.0.1:8000/api/v1/cases/<uuid>/context          # correlation + IoC, no agent
curl.exe -s -X POST http://127.0.0.1:8000/api/v1/cases/<uuid>/investigate   # run the agent, returns the report
curl.exe -s http://127.0.0.1:8000/api/v1/cases/<uuid>/investigation    # last saved result
curl.exe -s -X POST http://127.0.0.1:8000/api/v1/cases/<uuid>/review -H "Content-Type: application/json" -d "{\"status\":\"validated\",\"analyst\":\"analyst-l2\",\"notes\":\"Evidence reviewed.\"}"
```

> [!important] UUID, not the submitted ID
> All `{case_id}` paths use the **application UUID returned by intake**, not the `case_id` you sent (for example `SPRINT2-DEMO-001`). Sending the same submitted ID twice returns `409`.

> [!tip] Use `curl.exe` on Windows
> In PowerShell, `curl` is an alias of another command. Swagger UI at `http://127.0.0.1:8000/docs` is an easier alternative.

## 2. The real HTTP demo (one command)

```powershell
python demo/verify_local.py
```

It starts a temporary Uvicorn server and SQLite database, submits `examples/sprint2_demo.json` over real HTTP and checks the result. It saves its evidence in `demo/output/`: submitted JSON, acceptance response, investigation JSON, Markdown report, summary and server log. The temporary server and database are removed on exit. Each run uses a new submitted ID to avoid the duplicate check.

Expected: 4 alerts, 6 pairs (1 related, 2 uncertain, 3 unrelated), one noise candidate (`ecs-noise-003`), 3 IoC items, a valid report and `pending_review`.

For a server that is already running:

```powershell
python demo/run_pipeline.py --base-url http://127.0.0.1:8000
```

## 3. The agent alone (CLI)

```powershell
python agent/graph.py data/synthetic/phishing_ecs.json
```

It prints the Markdown draft. At the end, on stderr, it shows the skill validator result.

> [!tip] Clean output for a demo
> The MCP servers write lines like `Processing request of type CallToolRequest`. They are normal. To hide them:
> ```powershell
> python agent/graph.py data/synthetic/phishing_ecs.json 2>$null
> ```

### Available cases

| Command | What it shows |
| --- | --- |
| `python agent/graph.py data/synthetic/phishing_ecs.json` | Phishing (ECS); hostile text treated as data |
| `python agent/graph.py data/synthetic/bruteforce_wazuh.json` | Brute force (Wazuh); legitimate backup as evidence against |
| `python agent/graph.py data/synthetic/exfiltration.json` | Exfiltration; no enrichment |
| `python agent/graph.py data/synthetic/pre_ransomware.json` | Pre-ransomware; urgent actions |
| `python agent/graph.py data/synthetic/benign_noise.json` | Benign noise; no hypotheses |
| `python agent/graph.py data/holdout/kerberoast_rdp_rclone_ecs.json` | Holdout case; the agent detects nothing |

More in [[09 Tests and synthetic cases]].

### All synthetic cases at once

```powershell
python agent/run_synthetic.py
```

It saves each report in `data/reportes_sinteticos/` as `.json` (for machines) and `.md` (for people).

## Tests

```powershell
python -m pytest -q
```

Runs the 184 tests in about 20 seconds. See [[09 Tests and synthetic cases]].

## Validate a report by hand

```powershell
python skills/soc-case-investigator/scripts/validate_report.py --case data/synthetic/exfiltration.json --report data/reportes_sinteticos/exfiltration.json
```

Answers `REPORT STRUCTURE OK` or the list of errors. See [[08 The soc-case-investigator skill#The validator]].

## Using the agent from Python

```python
import asyncio, json
from agent.graph import build_graph, investigate, submit_review

app = build_graph()
case = json.load(open("data/synthetic/bruteforce_wazuh.json", encoding="utf-8"))

# Phases 1 to 5: pauses waiting for the analyst
state = asyncio.run(investigate(case, thread_id="case-1", app=app))
print(state["report"]["review"]["status"])     # pending

# Phase 6: the analyst decision resumes the graph
state = asyncio.run(submit_review(app, "case-1", {
    "status": "validated",          # validated | corrected | rejected
    "analyst": "analyst-l2",
    "notes": "Matches what the EDR shows",
}))
print(state["report"]["review"]["status"])     # validated
```

> [!important] Same `app`, same `thread_id`
> The case state lives in the checkpointer of `app`, in memory. To resume, use the same `app` object and the same `thread_id`. The backend does exactly this, which is why review only works in the process that ran the investigation (see [[15 The backend#Persistence]]).

## Original orchestrator (no LangGraph)

```powershell
python orchestrator/client.py data/sample_case_bruteforce.json
```

The pre-skill pipeline: it chains the four MCP servers and returns the old format, with percentage confidence. Kept as a reference.

Next: [[04 Case format]] · Back to [[00 Home]]
