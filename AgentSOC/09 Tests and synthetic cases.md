---
tags: [agentsoc, testing]
aliases: [Tests, Test cases, Synthetic cases]
updated: 2026-10-11
---

# Tests and synthetic cases

## The cases

### Agent cases (legacy direct format)

| File | Scenario | Format | Alerts | Agent result |
| --- | --- | --- | --- | --- |
| `data/synthetic/phishing_ecs.json` | Phishing with credential theft; hostile text in the email subject; 3 IoC | ECS | 4 | T1566 · `media` |
| `data/synthetic/bruteforce_wazuh.json` | SSH brute force, successful login, sudo; internal SSH that matches a backup | Wazuh | 8 | T1110 · `media`; T1021 · `insuficiente` |
| `data/synthetic/exfiltration.json` | Compression and outbound transfer with DNS tunneling | Internal | 4 | T1041 · `media` |
| `data/synthetic/pre_ransomware.json` | SMB, PsExec, shadow copy deletion, encryption | Internal | 5 | T1021 · `media`; T1486 · `media` |
| `data/synthetic/benign_noise.json` | Update and authorized scan; broken times | Internal | 3 | No hypotheses |
| `data/sample_case_bruteforce.json` | Original scaffold case | Internal | 4 | T1021 · `media`; T1110 · `baja` |
| `data/holdout/kerberoast_rdp_rclone_ecs.json` | **Holdout:** Office macro, Kerberoasting, RDP, rclone to the cloud | ECS | 5 | **No hypotheses** |

### API cases (contract v1.0)

| File | What it exercises |
| --- | --- |
| `examples/sprint2_demo.json` | **The Sprint 2 demo:** mixed Elastic + Wazuh, one related pair, one noise alert, one uncertain alert, 3 IoC (typed match, declared link only, unmatched) |
| `examples/elastic.json`, `examples/wazuh.json`, `examples/mixed.json` | Valid single-source and mixed cases |
| `examples/invalid_missing_case_id.json`, `examples/test_cases/invalid_missing_alerts.json` | Rejected with `422` |
| `examples/test_cases/with_enrichment.json`, `without_enrichment.json` | IoC present and absent |
| `examples/test_cases/valid_related_with_noise.json` | Related alerts plus noise |

> [!warning] Synthetic cases do not measure detection
> The cases in `data/synthetic/` were written together with the catalog rules, with tags the catalog recognizes. They check the **procedure** (order, format, controls), not the ability to detect attacks. The `data/holdout/` case is the only one never used to tune anything.

### Holdout rule

A holdout case stops being one as soon as it is used to tune rules or prompts. If you improve the agent by looking at the holdout case, create a new holdout case before measuring. See [[12.6 Measuring precision]].

## Current coverage

Count against reference techniques we wrote when designing each case. It is not a precision measurement.

| Case | Expected techniques | Detected |
| --- | --- | --- |
| Phishing | T1566, T1078, T1114.003 | T1566 |
| Wazuh brute force | T1110, T1078, T1548.003, T1021 | T1110, T1021 |
| Exfiltration | T1560, T1041 | T1041 |
| Pre-ransomware | T1021, T1490, T1486 | T1021, T1486 |
| Benign noise | none | none (correct) |
| Scaffold | T1110, T1078, T1021 | T1110, T1021 |
| **Holdout** | T1059.001, T1558.003, T1021.001, T1567.002 | **none** |
| **Total** | **19** | **8** |

## The test suite

```powershell
python -m pytest -q
```

**184 tests, about 20 s** (verified on 9 October 2026, Python 3.12). 145 are the original tests of both projects, unchanged; 39 are new parametrized cases. Agent and integration tests run the **real** LangGraph graph and MCP subprocesses: there is no mocked happy-path agent.

| File | What it covers |
| --- | --- |
| `test_cases.py`, `test_case_parser.py`, `test_contract.py`, `test_configuration.py`, `test_service.py`, `test_enrichment.py`, `test_noise_cases.py` | Original intake: contract, VR rules, native IDs, limits, duplicates, restart (111 tests) |
| `test_agent_graph.py` | Original agent: six phases on the synthetic cases (34 tests) |
| `test_correlation_engine.py` | **New.** Correlation rules R1–R4 |
| `test_ioc_integration.py` | **New.** IoC associations |
| `test_pipeline.py` | **New.** Full API flow through the real graph |

### Selected new tests

| Test | What it checks |
| --- | --- |
| `test_two_related_alerts_across_sources` | An ECS and a Wazuh alert sharing IP + user + host within 300 s are `related` |
| `test_one_ip_or_time_alone_is_not_enough` | A single shared family, or time alone, never gives `related` |
| `test_mitre_or_submitter_correlation_labels_are_not_evidence` | Same technique or a submitted label is not correlation evidence |
| `test_time_window_timezone_and_missing_time` | Window boundary, `-05:00` vs `Z` equivalence, missing time |
| `test_each_evidence_pointer_resolves_to_original_value` | Every pointer resolves to the stated value |
| `test_configurable_window_and_fifty_alerts` | 50 alerts produce 1,225 pairs |
| `test_explicit_link_is_distinct_from_observed_match` | Declared link vs. field match stay separate |
| `test_no_false_match_on_alert_id_message_or_substring` | No IoC match on IDs, free text or substrings |
| `test_full_api_pipeline_reaches_real_langgraph_and_mcp` | POST → context → investigate → valid report |
| `test_unrelated_same_mitre_technique_does_not_pool_confidence` | Two unrelated alerts give two `baja` hypotheses, not one pooled one |
| `test_findings_reference_real_ioc_evidence_without_increasing_confidence` | `ioc_evidence` exists and confidence does not change |
| `test_failure_retains_accepted_evidence_and_allows_retry` | Injected MCP failure → `502`, case kept, retry works |
| `test_evidence_survives_restart_but_live_review_checkpoint_is_explicitly_temporary` | Report readable after restart; review returns `409` |
| `test_untyped_custom_native_fields_cannot_crash_agent` | Non-string custom fields do not crash phase 1 |

> [!tip] If you change the rule catalog
> `EXPECTED_TECHNIQUES` in `tests/test_agent_graph.py` sets the expected techniques per case. If a new rule detects something in a synthetic case, update that dictionary. A failing test there is expected: it tells you the behavior changed.

## The real HTTP demo

```powershell
python demo/verify_local.py
```

| Pair | Classification |
| --- | --- |
| ecs-auth-001 / wazuh-auth-002 | related |
| ecs-auth-001 / ecs-noise-003 | unrelated |
| ecs-auth-001 / ecs-uncertain-004 | uncertain |
| wazuh-auth-002 / ecs-noise-003 | unrelated |
| wazuh-auth-002 / ecs-uncertain-004 | uncertain |
| ecs-noise-003 / ecs-uncertain-004 | unrelated |

IoC 1 matches both authentication alerts, IoC 2 is linked only by declared reference, and IoC 3 stays unmatched. One hypothesis: T1110 · `media` on web-01, built from the related pair. The report validates and stops at `pending_review`.

Recorded timings: 1.569 s in the verification run (`docs/VERIFICATION.md`) and 3.288 s in the stored `demo/output/summary.json`. Both cover intake to investigation for 4 alerts, excluding server start. They are observations, not a throughput guarantee.

## Lint and CI

```powershell
ruff check app tests demo/run_pipeline.py demo/verify_local.py --exclude tests/test_agent_graph.py
```

Passes on the backend, new tests and demo scripts. The legacy agent code is not in the lint scope. `.github/workflows/tests.yml` runs the suite on Python 3.12 and 3.14, but that remote matrix was not executed for this delivery.

Execution evidence: `docs/verification/` (`pytest.log`, `pytest.xml`, `lint.log`, `demo.log`, `environment.txt`, `contract-sha256.txt`).

## After changing something

```powershell
python -m pytest -q                                                  # nothing broke
python agent/graph.py data/holdout/kerberoast_rdp_rclone_ecs.json    # did the holdout improve?
python demo/verify_local.py                                          # the end-to-end flow still works
python agent/run_synthetic.py                                        # regenerate CLI reports
```

Next: [[10 Limitations]] · Back to [[00 Home]]
