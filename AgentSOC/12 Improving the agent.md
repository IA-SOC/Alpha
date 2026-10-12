---
tags: [agentsoc, improvements, index]
aliases: [Improvements, Agent roadmap]
updated: 2026-10-11
---

# Improving the agent

Step-by-step guides, ordered from least to most effort. Each one says which files to touch and how to check the change.

| Guide | What it solves | Effort | Sample code status |
| --- | --- | --- | --- |
| [[12.1 Adding a MITRE rule]] | Detect new techniques | Low | Tested in the previous version |
| [[12.2 Adding a test case]] | More coverage and regression | Low | — |
| [[12.3 Sequence correlations]] | Successful login after failures (T1078) and similar | Medium | Tested in the previous version |
| [[12.5 Persistence and performance]] | Reviews that survive restarts; less latency | Medium | Parallel MCP start already exists in the previous version |
| [[12.6 Measuring precision]] | Know how accurate it is | Medium, depends on the team | — |
| [[12.4 Adding an LLM node]] | Reason beyond the catalog | High | Proposal, not tested |

## Recommended order

1. **Restore the parallel MCP start** (12.5, option A). It is a small port from the previous version and roughly halves agent time per case.
2. **Persist review checkpoints** (12.5). Today a restart blocks pending reviews.
3. **Expand the catalog** with the client's MITRE guide (12.1) and add sequence correlations (12.3). This gains the most coverage for the least risk.
4. **Build a set of analyst-labeled cases** and measure (12.2 and 12.6). Without this, no improvement can be compared.
5. **Close the N8N task** with real anonymized N8N output and fixture tests (see [[17 IoC integration and traceability#N8N status]]).
6. **LLM** (12.4), compared against the measurement from step 4.

## Checklist for any change

- [ ] `python -m pytest -q` passes, or you updated the expectations on purpose.
- [ ] `python demo/verify_local.py` passes.
- [ ] You ran the holdout case and noted whether it changed.
- [ ] If you used the holdout case to tune something, you created a new one.
- [ ] You regenerated `data/reportes_sinteticos/` and `demo/output/`.
- [ ] You updated these notes if behavior changed.

## Other pending improvements

- Split rules that are grouped today: shadow copies → T1490; PsExec → T1569.002.
- Make evidence against look at the time window, not just the host.
- Extend the traceability check to the legacy `observation` text.
- Pin an ATT&CK version and store it in `source_version`.
- Run `POST /investigate` as a background job with a status endpoint, so the HTTP request does not wait.
- Add authentication to the API.
- Keep report history instead of replacing the last report.
- Test JSON ingestion into a case manager (TheHive or similar).
- Change the fixed validator path in the skill to a relative one.

Back to [[00 Home]]
