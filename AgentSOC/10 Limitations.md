---
tags: [agentsoc, limitations]
aliases: [Limitations, What it does not detect]
updated: 2026-10-19
---

# Limitations

> [!danger] The main limitation
> The analysis uses **seven keyword rules**. What those rules do not name, the agent does not see. In the holdout case, which describes a real attack with other rule names, the agent only finds RDP (T1021) with `baja` confidence and misses the other three techniques.

## The rule catalog

`RULES` in `core/logic.py`. An alert matches a rule if any word in `match_any` appears **inside** the rule name or a tag. Both are compared lowercase with every non-alphanumeric run turned into `_`, so "Volume Shadow Copy Deletion" becomes `volume_shadow_copy_deletion` and "Tactic: Lateral Movement" becomes `tactic_lateral_movement`.

| Technique | Tactic | Words it looks for |
| --- | --- | --- |
| T1110 Brute Force | Credential Access | `brute_force`, `failed_login`, `multiple_auth_failures` |
| T1021 Remote Services | Lateral Movement | `lateral_movement`, `smb_admin_share`, `remote_exec` |
| T1566 Phishing | Initial Access | `phishing`, `suspicious_attachment`, `credential_harvest` |
| T1041 Exfiltration Over C2 Channel | Exfiltration | `data_exfiltration`, `large_outbound_transfer`, `dns_tunneling` |
| T1569.002 System Services: Service Execution | Execution | `psexec`, `service_execution` |
| T1490 Inhibit System Recovery | Impact | `shadow_copy_delet`, `shadow_copies_delet`, `vssadmin`, `wbadmin`, `backup_catalog_delet` |
| T1486 Data Encrypted for Impact | Impact | `file_encryption`, `ransom_note`, `ransomware` |

### Consequences

- **It depends on how the rule is named.** An Elastic rule called "Kerberos Service Ticket Requests with RC4 Encryption Burst" contains no catalog word. Punctuation and spaces no longer matter, but the words still have to be in the catalog.
- **It does not correlate sequences of techniques.** It does not see that a successful login after several failures is worse than the failures alone (T1078). The new correlation engine groups alerts by shared entities, but it does not reason about order.
- **Few sub-techniques.** Only T1569.002 is a sub-technique; the rest are top-level.
- **`vssadmin` and `wbadmin` match any use of those tools**, including legitimate backup jobs. The mapping stays a candidate, and a `backup` tag on the same host lowers confidence.
- **No pinned ATT&CK version.** The catalog does not say which ATT&CK version it was written against.

### Signals it does not detect today (from the test cases)

| Signal | Expected technique | Case |
| --- | --- | --- |
| Successful login after failures | T1078 Valid Accounts | Wazuh, scaffold |
| Login from another country | T1078 Valid Accounts | Phishing |
| Mail forwarding rule | T1114.003 Email Forwarding Rule | Phishing |
| `sudo` to root | T1548.003 Sudo and Sudo Caching | Wazuh |
| Compressing a share | T1560 Archive Collected Data | Exfiltration |
| Office spawns PowerShell | T1059.001 PowerShell | Holdout |
| Kerberoasting | T1558.003 | Holdout |
| RDP to a server | T1021.001 (found as T1021, no sub-technique) | Holdout |
| rclone to the cloud | T1567.002 | Holdout |

How to fix it: [[12.1 Adding a MITRE rule]] and [[12.3 Sequence correlations]].

## Correlation limits (new)

| Limit | Effect |
| --- | --- |
| `related` means shared entities, not causation | Two related alerts can still be benign activity |
| Noise is relative to the case and rule profile | An `unrelated` alert is a noise *candidate*; it is never discarded |
| Groups are connected components | A group does not mean every pair inside it is directly related |
| Names compared exactly | `jdoe` and `DOMAIN\jdoe` do not match; tenant/domain scoping needs customer validation |
| Unknown custom fields are kept but not compared | Correlating on them needs verified mappings |
| O(n²) pairs | 50 alerts produce 1,225 pair records; fine at this size |

Detail in [[16 Correlation engine]].

## IoC limits (new)

| Limit | Effect |
| --- | --- |
| No real N8N samples | The N8N backlog task stays *in progress*; only the documented v1.0 wrapper is verified |
| No provider interpretation | A verdict or score is shown as supplied; it never raises confidence |
| Exact typed matches only | No substring or free-text matching (deliberate, to avoid false links) |

Detail in [[17 IoC integration and traceability]].

## Other limitations

| Limitation | Effect | Guide |
| --- | --- | --- |
| No LLM | Always identical results; nothing outside the catalog | [[11 Where the LLM fits]] |
| Review checkpoints in memory | After a server restart, saved reports are readable but `POST /review` returns `409` until the case is investigated again | [[12.5 Persistence and performance]] |
| Single worker only | Checkpoints and per-case locks are process-local | [[15 The backend#Why a single worker]] |
| Agent runs in the API process | A hard crash inside the agent affects the API (the previous version isolated it in a subprocess) | [[19 Changes from the previous version]] |
| MCP servers started one after another | About 0.9 s per server per case; the previous version started them in parallel | [[12.5 Persistence and performance]] |
| `POST /investigate` is synchronous | The HTTP request waits for the whole investigation (up to 300 s) | [[15 The backend]] |
| Reruns replace the last report | No report history | [[15 The backend#Persistence]] |
| 50-alert investigation not benchmarked | Pair enumeration for 50 alerts is unit-tested; full latency is not measured | [[12.5 Persistence and performance]] |
| No precision measurement | No accuracy percentage can be claimed | [[12.6 Measuring precision]] |
| Legacy evidence text not checked | The validator checks that a cited alert exists; only the new `source_fields` pointers are checked against values | [[17 IoC integration and traceability#Traceability check]] |
| Simplified evidence against | Only counts benign tags on the same host; ignores the time window | `BENIGN_TAGS` in `agent/investigation.py` |
| No authentication | The API is open | [[15 The backend]] |
| No analyst UI | Review happens through the API (Swagger) or code | [[15 The backend]] |
| No case manager integration | JSON ingestion into TheHive or similar was not tested | — |

Next: [[11 Where the LLM fits]] · Back to [[00 Home]]
