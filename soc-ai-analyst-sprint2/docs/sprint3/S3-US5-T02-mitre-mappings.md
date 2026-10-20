# S3-US5-T02 (#33): extend and correct candidate technique mappings

Parent story: #5, map suspicious behavior to MITRE ATT&CK.

## Problem

- Shadow-copy deletion was mapped to **T1486** Data Encrypted for Impact,
  together with file encryption. It is **T1490** Inhibit System Recovery.
- PsExec was only seen as T1021 Remote Services; the service it installs is
  **T1569.002** Service Execution.
- Matching compared raw lowercase text with underscore keywords, so real rule
  names never matched: "Volume Shadow Copy Deletion via VssAdmin" does not
  contain `shadow_copy_deleted`, and a `Tactic: Lateral Movement` tag does not
  contain `lateral_movement`.

## Change

| File | What changed |
| --- | --- |
| `core/logic.py` | New rule T1490 (`shadow_copy_delet`, `shadow_copies_delet`, `vssadmin`, `wbadmin`, `backup_catalog_delet`). New rule T1569.002 (`psexec`, `service_execution`) with the Execution tactic in `TACTIC_ORDER`, `TACTIC_TO_STAGE` and `ACTIONS_BY_TACTIC`. T1486 keeps `file_encryption`, `ransom_note` and adds `ransomware`. `_alert_signals` now lowercases and turns every non-alphanumeric run into `_` before matching. |
| `agent/investigation.py` | Alternatives, unknowns and priority for Execution. |
| `tests/test_mitre_mapping.py` | xfail marker removed; new test with 8 real Elastic and Wazuh rule names. |
| `tests/test_agent_graph.py` | `pre_ransomware` now expects T1021, T1569.002, T1490, T1486. |
| `demo/build_demo.py`, `AgentSOC/09`, `AgentSOC/10`, `AgentSOC/12` | Removed the "shadow copies go to T1486" notes; updated the catalog table and coverage. |

## Probe with vendor rule names

| Rule name | Before | After |
| --- | --- | --- |
| Volume Shadow Copy Deletion via VssAdmin (Elastic) | none | T1490 |
| Volume Shadow Copy Deleted or Resized via VssAdmin (Elastic) | none | T1490 |
| Deleting Backup Catalogs with Wbadmin (Elastic) | none | T1490 |
| Shadow copies deletion via vssadmin.exe (Wazuh) | none | T1490 |
| Wbadmin delete catalog command executed (Wazuh) | none | T1490 |
| PsExec Network Connection (Elastic) | none | T1569.002 |
| PsExec service installed (PSEXESVC) (Wazuh) | none | T1569.002 |
| Ransomware - Detected - Elastic Defend | none | T1486 |
| Service Command Lateral Movement (Elastic) | none | T1021 |

Coverage in `AgentSOC/09` went from 8 to 10 of 19 reference techniques
(pre-ransomware T1490, holdout RDP as T1021).

## Known limits

- `vssadmin` and `wbadmin` match any use of those tools, legitimate backups
  included. Mappings stay candidates, and a `backup` tag on the same host is
  evidence against.
- Vendor names were checked against the names listed above, not against a
  live Elastic or Wazuh rule set.

## How to check

```powershell
python -m pytest tests/test_mitre_mapping.py tests/test_agent_graph.py -q
```
