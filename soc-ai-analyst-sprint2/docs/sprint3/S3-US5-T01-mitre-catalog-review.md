# S3-US5-T01 (#32): MITRE catalog review, supported mappings and expected labels

Parent story: #5, map suspicious behavior to MITRE ATT&CK.
Owner: Ethan. Used by #33 (implementation), #34 (persistence), #35 (samples)
and #36 (tests).

Sources: `core/logic.py` (`RULES`), `protocolo.md` ("Evidencia y ATT&CK" and
"Medición de precisión") and the reference techniques in `demo/build_demo.py`.
Status is the behavior on `main` after PR #62.

## 1. Catalog review

An alert matches a rule when a pattern appears inside its rule name or a tag,
after lowercasing and turning punctuation and spaces into `_`.

| Rule | Patterns | Tactic | Verdict | Notes |
| --- | --- | --- | --- | --- |
| T1110 Brute Force | `brute_force`, `failed_login`, `multiple_auth_failures` | Credential Access | Keep | Wazuh groups `authentication_failed` and `invalid_login` reach it through `TAG_SYNONYMS`. A single `failed_login` is weak evidence; confidence handles that. |
| T1021 Remote Services | `lateral_movement`, `smb_admin_share`, `remote_exec` | Lateral Movement | Keep, refine later | Covers SMB, SSH and RDP alike with no sub-technique. `lateral_movement` is a tactic word, so it maps any lateral-movement tag to T1021. |
| T1566 Phishing | `phishing`, `suspicious_attachment`, `credential_harvest` | Initial Access | Keep | A visit to a credential-harvest page is still T1566 (the link is the vector). |
| T1041 Exfiltration Over C2 Channel | `data_exfiltration`, `large_outbound_transfer`, `dns_tunneling` | Exfiltration | Review | T1041 assumes the data leaves over the C2 channel, which the alerts do not show. `dns_tunneling` fits T1048 or T1071.004 better. |
| T1569.002 Service Execution | `psexec`, `service_execution` | Execution | Keep | New in #33. PsExec also keeps T1021 through `remote_exec`; both are valid. |
| T1490 Inhibit System Recovery | `shadow_copy_delet`, `shadow_copies_delet`, `vssadmin`, `wbadmin`, `backup_catalog_delet` | Impact | Keep | New in #33. `vssadmin` and `wbadmin` also match legitimate use. |
| T1486 Data Encrypted for Impact | `file_encryption`, `ransom_note`, `ransomware` | Impact | Keep | |

The catalog has no pinned ATT&CK version: `source_version` says "catálogo
local core/logic.RULES (sin versión ATT&CK fijada)".

## 2. Mapping criteria

| ID | Criterion | Verified by | Status |
| --- | --- | --- | --- |
| MP-01 | Every mapping is a **candidate** (`status: candidate`). Mapping is never a confirmation. | `test_mappings_are_candidates_that_cite_their_alerts_and_catalog` | Met |
| MP-02 | Every mapping cites at least one alert of the case as evidence, with `source_fields` (EV criteria, #42). | Validator; `test_evidencia_cita_campos_originales_en_ruta_directa` | Met |
| MP-03 | Every mapping records the catalog it came from in `source_version`. | `test_mappings_are_candidates_that_cite_their_alerts_and_catalog` | Met, but no ATT&CK version (see decision 3) |
| MP-04 | A mapping only uses technique IDs that are in the catalog, in `T####` or `T####.###` format. | Validator | Met |
| MP-05 | Behavior with no catalog pattern gets **no mapping, no hypothesis and no action**, and the limitations say the catalog does not cover it. | `test_behavior_outside_the_catalog_is_not_mapped` | Met |
| MP-06 | A shared technique never makes alerts related: correlation is the same with or without technique tags. | `test_a_shared_technique_does_not_relate_alerts`, `test_unrelated_same_mitre_technique_does_not_pool_confidence` | Met |
| MP-07 | One alert may support more than one technique when the pattern is compatible with several (PsExec: T1021 and T1569.002). Alternative candidates are kept, not merged. | `pre_ransomware` in `test_agent_graph.py` | Met |
| MP-08 | A sub-technique is used only when the evidence discriminates it; otherwise use the parent technique. | Catalog review | Met (only T1569.002) |
| MP-09 | No threat actor or group is ever inferred from a technique. | Code review: the report has no actor field | Met |

## 3. Label vocabulary for the synthetic cases

Taken from step 1 of "Medición de precisión" in the protocol:

- **expected**: the technique an analyst would assign.
- **acceptable**: an alternative that is also correct and should not count as an error.
- **not mappable**: the behavior is real, but outside the catalog; the right output is no mapping plus the limitation.
- **no technique**: benign or context activity; any mapping is a false positive.

## 4. Expected labels per alert (proposed, Ethan confirms)

"Agent" is the current output. **Result**: ✅ correct · ⚠️ acceptable or
debatable · ❌ missed (outside the catalog) · — nothing to map.

### phishing_ecs

| Alert | Behavior | Expected | Acceptable | Agent | Result |
| --- | --- | --- | --- | --- | --- |
| ecs-ph-001 | Suspicious attachment or link in mail | T1566 | T1566.001, T1566.002 | T1566 | ✅ |
| ecs-ph-002 | Credential-harvest page visited | T1566 | T1566.002 | T1566 | ✅ |
| ecs-ph-003 | Login from a new country | T1078 | — | none | ❌ not mappable |
| ecs-ph-004 | New inbox forwarding rule | T1114.003 | T1114 | none | ❌ not mappable |

### bruteforce_wazuh

| Alert | Behavior | Expected | Acceptable | Agent | Result |
| --- | --- | --- | --- | --- | --- |
| …1001 | SSH login with a non-existent user | T1110 | T1110.001 | T1110 | ✅ |
| …1002 | SSH authentication failed | T1110 | T1110.001 | T1110 | ✅ |
| …1003 | SSH brute force | T1110 | T1110.001 | T1110 | ✅ |
| …1004 | SSH login success after the failures | T1078 | — | none | ❌ not mappable |
| …1005 | sudo to root | T1548.003 | — | none | ❌ not mappable |
| …1006 | Internal SSH web → database | T1021 | T1021.004 | T1021 | ⚠️ designed ambiguous: matches a legitimate backup |
| …1007 | Scheduled backup timer | no technique | — | none | — |
| …1008 | tar archive under /var/backups | no technique | — | none | — |

### exfiltration

| Alert | Behavior | Expected | Acceptable | Agent | Result |
| --- | --- | --- | --- | --- | --- |
| ex-1 | Archive of a sensitive share | T1560 | T1560.001 | none | ❌ not mappable |
| ex-2 | Large outbound transfer | T1041 | T1048, T1567 | T1041 | ✅ |
| ex-3 | DNS tunneling suspected | T1048 | T1071.004, T1041 | T1041 | ⚠️ see decision 2 |
| ex-4 | Large outbound transfer | T1041 | T1048, T1567 | T1041 | ✅ |

### pre_ransomware

| Alert | Behavior | Expected | Acceptable | Agent | Result |
| --- | --- | --- | --- | --- | --- |
| rw-1 | SMB admin share access | T1021 | T1021.002 | T1021 | ✅ |
| rw-2 | Remote execution with PsExec service | T1569.002 | T1021, T1021.002 | T1021, T1569.002 | ✅ |
| rw-3 | Shadow copies deleted | T1490 | — | T1490 | ✅ |
| rw-4 | Mass file encryption | T1486 | — | T1486 | ✅ |
| rw-5 | Ransom note created | T1486 | — | T1486 | ✅ |

### benign_noise

| Alert | Behavior | Expected | Agent | Result |
| --- | --- | --- | --- | --- |
| bn-1 | Software update | no technique | none | ✅ |
| bn-2 | Authorized vulnerability scan | no technique | none | ✅ |
| bn-3 | Service restarted | no technique | none | ✅ |

### sample_case_bruteforce

| Alert | Behavior | Expected | Acceptable | Agent | Result |
| --- | --- | --- | --- | --- | --- |
| a1 | Multiple authentication failures | T1110 | — | T1110 | ✅ |
| a2 | Successful login after the failures | T1078 | — | none | ❌ not mappable |
| a3 | SMB admin share access | T1021 | T1021.002 | T1021 | ✅ |
| a4 | Remote execution | T1021 | T1569.002 | T1021 | ✅ |

### Holdout (never used for tuning)

| Alert | Behavior | Expected | Acceptable | Agent | Result |
| --- | --- | --- | --- | --- | --- |
| ho-001 | Office spawns PowerShell | T1059.001 | T1204.002 | none | ❌ |
| ho-002 | Kerberos RC4 ticket burst | T1558.003 | — | none | ❌ |
| ho-003 | RDP logon from workstation | T1021.001 | T1021 | T1021 | ⚠️ parent technique |
| ho-004 | rclone with a cloud remote | T1567.002 | — | none | ❌ |
| ho-005 | Unusual outbound volume to cloud storage | T1567.002 | T1048 | none | ❌ |

**Totals:** 33 alerts, 28 with a technique to find. The agent finds 18 of them
correctly or acceptably (4 of those are ⚠️), misses 10 that are outside the
catalog, and maps none of the 5 benign alerts (no false positives on these
cases; see section 5 for names that do produce them).

## 5. Samples that #35 needs

- **Positive**: one per pattern, with a vendor rule name, not only the
  underscore keyword (the #33 test already covers eight names).
- **Negative**: names that contain a pattern but are not the behavior.
  Checked against the current catalog:

  | Rule name | Current mapping | Correct? |
  | --- | --- | --- |
  | Shadow Copy Creation | none | ✅ |
  | Volume Shadow Copy Created | none | ✅ |
  | Anti-phishing policy updated | T1566 | ❌ false positive |
  | Failed login page CSS updated | T1110 | ❌ false positive |
  | vssadmin list shadows | T1490 | ❌ false positive |

  Substring matching can't tell these apart; the samples should make the
  false positives visible, and decision 4 proposes how to reduce them.
- **Unknown pattern**: the holdout techniques (T1059.001, T1558.003,
  T1567.002), which should produce no mapping and a limitation.

## Decisions for Ethan

1. Confirm or correct the per-alert labels in section 4, especially the
   acceptable alternatives. Once confirmed, they replace the case-level list
   in `demo/build_demo.py` as the reference.
2. `dns_tunneling`: keep it under T1041, or move it to a T1048 rule?
3. Pin an ATT&CK version (for example Enterprise v16) in `CATALOG_VERSION`,
   or keep "no pinned version" until the client's MITRE guide arrives?
4. Negative patterns: should a rule be able to require a second word
   (`vssadmin` + `delete`/`resize`) or exclude one (`anti_phishing`)? That
   removes the three false positives in section 5 at the cost of a slightly
   more complex rule format.
