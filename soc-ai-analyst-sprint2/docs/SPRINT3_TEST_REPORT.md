# Sprint 3 test report, 19 October 2026

Covers the Sprint 3 test tasks #31, #36, #41 and #46. Everything was run from
`soc-ai-analyst-sprint2/` on Windows 11 with Python 3.14.4 and the pinned
`requirements-dev.txt`, in a fresh virtual environment.

## Results

| Check | Command | Result |
| --- | --- | --- |
| Regression, whole suite | `python -m pytest tests -q` | **214 passed, 3 xfailed**, 75 s |
| Baseline before the new tests | `python -m pytest -q` | 184 passed, same as the Sprint 2 report |
| Lint, same scope as Sprint 2 | `ruff check app tests demo/run_pipeline.py demo/verify_local.py --exclude tests/test_agent_graph.py` | Passed |
| End to end over real HTTP | `python demo/verify_local.py` | Passed. 4 alerts went from intake to `pending_review` in 2.8 s, report structure and traceability OK |

The 3 xfails are strict. Each one describes behavior the criteria ask for and
the code doesn't do yet. When the linked task fixes it, the test starts passing,
strict mode turns that into a failure, and whoever fixed it removes the marker.

## What the new tests check

**#31, timeline order**, in `tests/test_timeline_order.py`

- Dated events follow their UTC instant, including an explicit `-05:00` offset.
- Equal timestamps keep the order the alerts were submitted in.
- Offsets become UTC and the original value is kept.
- A time without a zone is flagged as unknown and never turned into UTC.
- Every entry points to exactly one submitted alert, none is lost, and the
  traceability check passes.
- Every entry is marked as observed.

**#36, MITRE mapping**, in `tests/test_mitre_mapping.py`

- Each of the 15 catalog patterns maps to its technique and tactic.
- Every mapping is a candidate that cites its alerts and the catalog version.
- Behavior outside the catalog, like Kerberoasting, gets no mapping, no
  hypothesis and no action, and the limitations say the catalog doesn't cover it.
- Two unrelated alerts with the same technique stay unrelated, and their
  correlation is the same with or without the technique tags.
- Related alerts with different techniques keep one correlation group.

**#41, hypotheses**, in `tests/test_hypotheses.py`

- Every hypothesis has a rank, supporting alerts from the case, alternatives,
  unknowns, an ordinal confidence and its basis.
- A legitimate backup on the same host shows up as evidence against and lowers
  the confidence.
- Benign activity alone raises no hypothesis and no action.
- A hypothesis never cites alerts outside its correlation group.
- Through the API, the summary asserts no attack sequence across unrelated
  groups.

The criteria come from `skills/soc-case-investigator/references/protocolo.md`
and the task titles, since the criteria tasks #27, #32 and #37 are still open.
Each test file lists them at the top. If those tasks change the criteria, the
tests should follow.

## Known defects, tracked as strict xfails

| Test | Defect | Fixed by |
| --- | --- | --- |
| `test_undated_and_zone_less_events_come_after_the_dated_sequence` | Undated and zone-less events are sorted to the top of the timeline instead of being kept apart | #28 |
| `test_shadow_copy_deletion_maps_to_inhibit_system_recovery` | Shadow-copy deletion still maps to T1486 together with file encryption, not to T1490 | #33 |
| `test_direct_agent_summary_asserts_no_sequence_across_unrelated_alerts` | Run directly, the way `agent/run_synthetic.py` and the demo page do, the agent writes "Secuencia de ataque sugerida: Phishing → Brute Force → Remote Services" for three unrelated hosts. The API path is fine | #38 |

## CI

The workflow lived in `soc-ai-analyst-sprint2/.github/workflows/`, and GitHub
only reads workflows from the repo root, so it never ran: the repo had zero
workflow runs. It now lives in `.github/workflows/tests.yml` at the root and
runs from `soc-ai-analyst-sprint2/`. It runs on pull requests and on pushes to
`main`, with Python 3.12 and 3.14, and it adds the lint step above.

## Demo runbook

A short traceable investigation, from intake to the analyst decision.

1. Set up once: `python -m venv .venv`, then
   `.venv/Scripts/python -m pip install -r requirements-dev.txt`.
   On Linux or macOS the folder is `.venv/bin/`.
2. Run `python demo/verify_local.py`. It starts the API on a free local port
   with a throwaway database, submits `examples/sprint2_demo.json`, runs the
   investigation and stops the server. The evidence stays in `demo/output/`.
3. Walk through the output:
   - `submitted_case.json` and `accepted.json` show the case as sent and the
     UUID it got.
   - `investigation.json` has the correlation: 1 related pair, 3 unrelated,
     2 uncertain, and `ecs-noise-003` kept as noise, not dropped.
   - `report.md` is the readable report. Pick one hypothesis, follow its alert
     IDs to the timeline, then to the original field through the JSON Pointer
     in `source_fields`, and show the value in `submitted_case.json`.
   - Point out the IoC section: the provider result is shown as it came, with
     no verdict of our own and no effect on confidence.
   - `summary.json` closes with `pending_review` and `traceability_ok: true`.
4. Recording the analyst decision through the API is covered by
   `test_review_resumes_existing_graph_and_persists_decision`. In the live demo
   it will happen from the web UI, #56.

`demo/output/` is ignored by git, so each run starts clean.
