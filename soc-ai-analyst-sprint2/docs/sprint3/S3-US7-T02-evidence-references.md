# S3-US7-T02 (#43): traceable evidence in timeline, MITRE mapping and hypotheses

Parent story: #7, maintain traceable supporting evidence.

## Problem

- Timeline entries cited only `alert_ids`, with no pointer to the original
  fields.
- `source_fields` (JSON Pointer + original value) was only added to MITRE and
  hypothesis evidence on the API path; the direct path had none.
- `verify_traceability` checked hypotheses but not the timeline or the MITRE
  mapping.

## Change

| File | What changed |
| --- | --- |
| `app/services/evidence.py` | `SIGNAL_PATHS` moved here from `agent_adapter.py`, so the agent and the adapter cite the same fields. |
| `agent/normalize.py` | Every normalized alert carries `source_fields`: the signal fields plus the timestamp, as `{alert_id, path, value}` with a JSON Pointer into the submitted case. API cases take them from the adapter (`signal_evidence` + `timestamp_evidence`); direct cases compute them with `read_field`. Values are deep copies of the raw values. |
| `agent/investigation.py` | Timeline entries, MITRE evidence and hypothesis evidence copy the alert's `source_fields`. The API-only injection in `correlated_attack_analysis` was removed. |
| `app/services/traceability.py` | Also verifies every timeline and MITRE `source_fields` against the original payload, and that a timeline field belongs to the entry's own alert. |
| `tests/test_timeline_order.py` | New test: every entry cites its own alert, the `@timestamp` pointer and value are exact, and a tampered value is rejected. |
| `tests/test_agent_graph.py` | New test over all synthetic cases: every pointer in timeline, MITRE and hypotheses resolves to the same value in the input file. |

Raw fields are not modified: `original_case` and `raw` stay as submitted, and
every cited value must equal the value at its pointer.

## How to check

```powershell
python -m pytest tests/test_timeline_order.py tests/test_agent_graph.py tests/test_pipeline.py -q
python demo/verify_local.py   # summary.json ends with traceability_ok: true
```
