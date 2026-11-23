# Issue #210: hypothesis criteria, stage 1

Task: [S6-US6-T01](https://github.com/IA-SOC/Alpha/issues/210), US6 / US8,
R6 / R8. Baseline inspected: `20ff2313ccfd9318d31e3986c1ce832a73e94e80`
(`origin/main`), 2026-11-23. Branch: `feat/210-hypothesis-criteria-stage-1`.
This is a partial increment; issue #210 and full US6 acceptance remain open.

## Review before changing behavior

Sources: [HY criteria](../sprint3/S3-US6-T01-hypothesis-criteria.md),
[protocol](../../skills/soc-case-investigator/references/protocolo.md#rúbrica-ordinal-de-confianza),
[analysis](../../agent/investigation.py),
[normalization](../../agent/normalize.py),
[correlation](../../app/services/correlation.py) and
[adapter](../../app/services/agent_adapter.py).

| Criterion | Behavior on baseline main | This stage |
| --- | --- | --- |
| HY-08 | Correlation limits related **pairs** to the configured window (300 seconds by default), but connected groups can span longer intervals. `build_attack_analysis` accepts any same-host benign-tagged alert in the group as contradiction, even when far from every supporting alert. Missing hosts can also compare equal in the ungrouped fallback. | Require a nonempty equal host and comparable UTC timestamps within the configured window of at least one supporting alert. |
| HY-09/10 | Six catalog tactics have fixed alternatives/unknowns. Native Wazuh tactics and combined ambiguous tactic labels may produce empty lists. Unknowns do not describe the case's missing evidence. | Pending; do not infer absent telemetry from an alert that simply does not contain it. |
| HY-15 | Three supporting alerts and two distinct rule names can produce `alta`. Neither rule names nor duplicated fields establish independent sources. Normalized `source_format` is a format, and mapping source describes classification provenance. | Definition proposed below; no confidence-source change in this stage. |
| HY-16 | Timestamp problems and contradictions lower confidence; missing host/user do not. | Pending: define when each field is relevant, its absence, and the cumulative downgrade. |
| HY-18 | Within a group, confidence then tactic order is used. The combined group list is sorted only by confidence, so input/group order can override tactic order on ties. | Pending. Ranking must never imply an attack sequence. |

The historical Sprint 3 criteria document is a snapshot, not proof of current
acceptance. Existing timestamp downgrades, synthetic caps and explicit analyst
legitimate marks must retain their behavior during HY-08 changes.

## HY-08 rule for this increment

An automatically selected benign-tagged alert contradicts a hypothesis only if:

1. It is not one of that mapping's supporting alerts.
2. Its normalized host is present and equals a supporting alert's host.
3. Both alerts have a reliable timezone-aware time normalized to UTC.
4. Their absolute time difference is at most `correlation.window_seconds`.

The window is inclusive in both directions. Group membership alone is
insufficient, and time is checked against actual supporting alerts, not bridge
events or the whole group's first/last timestamp. The ungrouped fallback uses
the existing 300-second default, also retained for legacy internal correlation
contexts without `window_seconds`. Missing/invalid/zone-less times cannot establish
temporal contradiction; they remain in the input/timeline with their existing
limitations. Different hosts and two missing hosts do not establish contradiction.
Automatic benign tags remain an existing heuristic, not verified benign verdicts.

An explicit `analyst_legitimate` mark on mapped evidence remains counter-evidence
even without usable times: it is a human instruction about that evidence, not a
new automatically inferred temporal association. Source values, IDs/pointers,
correlation groups, original reports' contract and human review remain intact.

## Independent-source definition proposed for the next stage

This is a proposal, not an agreed rubric or an implemented feature. The task
requires agreement before implementing HY-15.

- Independent corroboration requires explicit provenance identifying distinct
  originating telemetry producers, together with evidence that the observations
  are not copies of the same original event. A different rule, field, alert ID,
  ATT&CK mapping path, provider score or export format is insufficient.
- Preserve the producer identity and original-event reference with resolvable
  case pointers; distinguish origin from collector, forwarding and enrichment.
  `source_system` alone (`elastic` / `wazuh`) cannot establish independence.
- When origin or duplication cannot be resolved from available provenance,
  record independence as unknown. Never manufacture an identity or use missing
  metadata as positive corroboration. IoC/provider context cannot raise confidence.
- Before implementation, agree the supported provenance fields and conflict/copy
  rules using available Elastic/Wazuh examples, then add same-origin, copied,
  distinct-origin and unknown-provenance regressions on both intake paths.

HY-09/10, HY-15, HY-16 and HY-18 remain separate follow-up work. Completing HY-08
does not establish acceptance of the entire issue or US6.

## Verification

Environment: Windows, Python 3.12.2, project `.venv`; pinned dependencies from
`requirements-dev.txt` (pytest 9.2.0, FastAPI 0.162.5, LangGraph 1.2.21,
MCP 2.3.0). Executed on 2026-11-23, against the baseline above with this stage's
local changes. Existing unrelated `frontend/package-lock.json` changes were
preserved and excluded from this increment.

Commands executed from `D:/Repositorios/Alpha/soc-ai-analyst-sprint2/`:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pytest --version
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest tests/test_hypothesis_time_window.py -q -k 'not api and not direct_agent' --tb=short
.\.venv\Scripts\python.exe -m pytest tests/test_hypothesis_time_window.py tests/test_hypotheses.py tests/test_report_contract.py tests/test_mitre_mapping.py tests/test_language_investigation.py tests/test_correlation_engine.py tests/test_pipeline.py tests/test_instructions.py -q --tb=short
.\.venv\Scripts\python.exe -m ruff check app tests demo/run_pipeline.py demo/verify_local.py --exclude tests/test_agent_graph.py
.\.venv\Scripts\python.exe -m ruff check agent/investigation.py --select F
git diff --check
```

- Initial collection failed because the older Alpha environment lacked
  `reportlab`. Dependency synchronization first failed with sandbox DNS errors,
  then succeeded outside the sandbox. `pip check`: no broken requirements.
- Before the implementation change, the new logic regressions produced
  **11 failed, 7 passed, 2 deselected**, reproducing the temporal/host defects.
  After the first fix: **18 passed, 2 deselected**.
- The API/MCP run stalled inside the sandbox and was interrupted; it is not a
  successful verification. Outside it, the first expanded run produced
  **184 passed, 1 failed**: a pre-existing provenance test supplied a correlation
  context without `window_seconds`. The fix retains the 300-second fallback for
  such internal callers; the configured-window regressions still exercise 60
  and 300 seconds explicitly.
- Final expanded rerun: **185 passed in 142.74 seconds**, including all 20 new
  HY-08 cases. Executed outside the sandbox with the same command above.
- CI-scope Ruff and the separate agent F checks passed. This is not a claim of
  whole-repository lint coverage.

The new module has 20 cases covering inclusive before/after boundaries, an
older unrelated backup, UTC offsets, different/missing hosts, unavailable times,
transitive groups with configured windows, explicit analyst marks, and the real
API/local-agent/MCP paths. Integration assertions protect unchanged input counts,
pending human review and API traceability. Existing nearby-backup, benign-only,
unrelated-group, report contract and ordinal/synthetic-cap tests run alongside it.
No real Gemini calls, client data, full-suite run, performance benchmark or demo
regeneration form part of this stage. Human effort has not been inferred from
the estimate; AI-assisted changes require human review before acceptance.
