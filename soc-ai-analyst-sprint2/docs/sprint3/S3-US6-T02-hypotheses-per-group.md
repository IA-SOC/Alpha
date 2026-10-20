# S3-US6-T02 (#38): hypotheses per related group

Parent story: #6, formulate an evidence-based attack hypothesis.

## Problem

Through the API, hypotheses were already built per correlation group. Run
directly (`agent/run_synthetic.py`, the demo page, `python agent/graph.py`),
the agent had no correlation:

- one hypothesis per technique merged every alert with that technique, even
  on unrelated hosts, which raised confidence;
- the executive summary said "Secuencia de ataque sugerida: Phishing → Brute
  Force → Remote Services" for three unrelated hosts.

The strict xfail `test_direct_agent_summary_asserts_no_sequence_across_unrelated_alerts`
from #41 documented this.

## Change

| File | What changed |
| --- | --- |
| `app/services/agent_adapter.py` | New `correlate_direct(case, alerts)`. It wraps the normalized alerts in the v1.0 contract only to run the existing correlation engine (`extract_events` + `correlate`), then rewrites evidence pointers from `/alerts/i/raw_alert/...` to `/alerts/i/...` so they point into the case as given. Returns `None` if the case can't be wrapped: duplicate IDs, non-object alerts, or alerts the contract rejects. |
| `agent/graph.py` | Phase 2 takes the correlation from the API context or from `correlate_direct`, and runs `correlated_attack_analysis` whenever there is one. The summary never states a sequence. The report carries `correlation` on both paths; without one, the limitations say hypotheses group by technique and may mix unrelated activity. |
| `tests/test_hypotheses.py` | xfail marker removed; new direct-path test: two related brute-force alerts form one hypothesis, an unrelated one stays apart, and every correlation pointer resolves to the raw case value. |
| `AgentSOC/06`, `AgentSOC/09` | Describe the direct-path correlation and the new results. |

## Effect on the synthetic cases

Alerts with no related pair are now analysed on their own, so confidence goes
down where the old result came from merging them:

| Case | Before | After |
| --- | --- | --- |
| phishing_ecs | T1566 `media` | T1566 `baja` ×2 |
| exfiltration | T1041 `media` | T1041 `media`; T1041 `baja` |
| sample_case_bruteforce | T1021 `media`; T1110 `baja` | T1110 `baja`; T1021 `baja` ×2 |
| bruteforce_wazuh, pre_ransomware | unchanged | unchanged |

This is the intended behavior: a shared technique is not evidence that two
alerts observe the same activity.

## How to check

```powershell
python -m pytest tests/test_hypotheses.py -q
python agent/run_synthetic.py
```
