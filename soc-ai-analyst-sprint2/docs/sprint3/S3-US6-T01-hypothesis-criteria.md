# S3-US6-T01 (#37): hypothesis criteria

Parent story: #6, formulate an evidence-based attack hypothesis.
Owner: Ethan. Used by #38 (implementation), #39 (backend delivery), #40
(cases) and #41 (tests).

Sources: `protocolo.md` (phase 2, "Evidencia y ATT&CK" and "Rúbrica ordinal
de confianza"), `report-schema.json` (`hypotheses`) and the validator. Status
is the behavior on `main` after PR #62.

## 1. What a hypothesis must contain

| ID | Criterion | Verified by | Status |
| --- | --- | --- | --- |
| HY-01 | `rank` (1 = most likely), `statement`, `confidence`, `confidence_basis`, `evidence_for`, `evidence_against`, `alternatives` and `unknowns` are always present. Empty lists are allowed for `evidence_against`; the others need content. | Validator; `test_every_hypothesis_is_complete` | Met |
| HY-02 | The statement says what the activity is **compatible with**, never that it is confirmed ("Actividad compatible con …"). | `test_sin_porcentajes_ni_confirmaciones` | Met |
| HY-03 | No hypothesis is raised without at least one mapped supporting alert. Benign activity alone raises no hypothesis and no action. | `test_no_hypothesis_without_mapped_evidence`, `test_ruido_benigno_sin_hipotesis_y_con_limitaciones` | Met |

## 2. Supporting evidence

| ID | Criterion | Verified by | Status |
| --- | --- | --- | --- |
| HY-04 | Each item in `evidence_for` cites an alert of the case, with role `supporting`, an observation, why it matters, and `source_fields` (EV criteria, #42). | Validator; `test_evidencia_cita_campos_originales_en_ruta_directa` | Met |
| HY-05 | All supporting alerts of a hypothesis belong to **one correlation group**. Alerts with no related pair form their own hypothesis. A shared technique never merges groups. | `test_hypotheses_stay_inside_their_correlation_group`, `test_direct_agent_keeps_unrelated_alerts_of_one_technique_apart`, `test_unrelated_same_mitre_technique_does_not_pool_confidence` | Met |
| HY-06 | Enrichment (IoC) is attached as `ioc_evidence` with role `context`. It never raises confidence and never becomes a verdict of its own. | `test_findings_reference_real_ioc_evidence_without_increasing_confidence` | Met |

## 3. Contradicting evidence

| ID | Criterion | Verified by | Status |
| --- | --- | --- | --- |
| HY-07 | Alerts that point to legitimate activity (`backup`, `scheduled_task`, `maintenance`, `change_approved`) on the **same host** as the supporting evidence go to `evidence_against`, with role `contradicting`, and lower the confidence one level. | `test_legitimate_activity_is_kept_as_evidence_against`, `test_wazuh_respaldo_legitimo_queda_ambiguo` | Met |
| HY-08 | Contradicting evidence should also be close **in time** (same correlation window), not just on the same host. | — | **Not met**: today any time counts |

## 4. Alternatives and unresolved questions

| ID | Criterion | Verified by | Status |
| --- | --- | --- | --- |
| HY-09 | `alternatives` lists at least one benign explanation for the tactic. | `test_every_hypothesis_is_complete` | Met for the 6 tactics in the catalog; a tactic with no entry would get an empty list |
| HY-10 | `unknowns` lists the evidence that would tell the hypothesis apart from its alternatives (the protocol's "evidencia necesaria para discriminar"). | Same test | Partly: fixed text per tactic, not specific to the case |

## 5. Confidence

Ordinal only: `alta`, `media`, `baja`, `insuficiente`. Never a percentage.

| ID | Criterion | Verified by | Status |
| --- | --- | --- | --- |
| HY-11 | Starting level: 3+ alerts with 2+ different rules → `alta`; 2 alerts → `media`; 1 → `baja`; none → `insuficiente`. | `ordinal_confidence` | Met |
| HY-12 | One level down for each: contradicting evidence; a supporting alert without a time zone or with an invalid time. | `test_legitimate_activity_is_kept_as_evidence_against` (contradiction only) | Met; the time-zone drop has no dedicated test |
| HY-13 | A synthetic case never goes above `media`. | `test_sinteticos_no_superan_confianza_media` | Met |
| HY-14 | `confidence_basis` explains the level in one or two sentences, including every downgrade. | `test_every_hypothesis_is_complete` | Met |
| HY-15 | Two fields copied from the same source don't count as independent corroboration. | — | **Not met**: the rubric counts distinct rule names, not distinct sources |
| HY-16 | Missing key fields (host, user) also lower confidence. | — | **Not met**: the protocol asks for it, the code doesn't |

## 6. Sequences and actions

| ID | Criterion | Verified by | Status |
| --- | --- | --- | --- |
| HY-17 | The report never asserts an attack sequence across groups that are not related, on either path. | `test_api_summary_asserts_no_sequence_across_unrelated_groups`, `test_direct_agent_summary_asserts_no_sequence_across_unrelated_alerts` | Met |
| HY-18 | Hypotheses are ranked by confidence, then by tactic order (initial access first). | `ordinal_confidence` / `correlated_attack_analysis` | Partly: across groups the order is by confidence only |
| HY-19 | `insuficiente` hypotheses produce no action; `baja` ones lower the action priority one step. Every action requires human approval. | `test_ransomware_prioriza_impacto` (priority only) | Met; the `insuficiente` rule has no dedicated test |

## Cases that #40 needs

One case per expectation, each with the alerts that support or contradict it:

- **Attack**: 3 related alerts, 2 rules, same host and user within 5 minutes → `media` (synthetic cap).
- **Benign**: only `maintenance` / `backup` activity → no hypothesis.
- **Ambiguous**: an attack signal plus a backup on the same host → lowered confidence and `evidence_against`.
- **Same technique, unrelated**: two brute-force alerts on different hosts and users → two `baja` hypotheses.
- **Downgrades**: a supporting alert without a time zone, and one without a host (for HY-16 once decided).

## Decisions for Ethan

1. HY-08: add the time window to contradicting evidence? It would stop a
   backup from last week lowering today's hypothesis.
2. HY-15 and HY-16: implement them in this sprint or record them as known
   limits? Both change confidence values in the demo.
3. HY-10: are fixed per-tactic unknowns enough for the prototype, or should
   they name the missing fields of the case (for example "no EDR telemetry
   for WKS-15")?
