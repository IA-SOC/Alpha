# S3-US7-T01 (#42): evidence acceptance criteria

Parent story: #7, maintain traceable supporting evidence.
Owner: Ethan. Used by #43 (implementation), #44 (validation across report
sections), #45 (traceability tests) and #46 (regression and demo).

Sources: `protocolo.md` ("Evidencia y ATT&CK" and phase 4),
`report-schema.json` (`$defs/evidence`), `scripts/validate_report.py` and
`app/services/traceability.py`. Status is the behavior on `main` after PR #62.

## 1. The evidence reference

Every finding points to its evidence with these fields:

| Field | Meaning | Example |
| --- | --- | --- |
| `alert_id` | Original ID of the alert in the case | `1726387340.1003` |
| `role` | `supporting`, `contradicting` or `context` | `supporting` |
| `observation` | What was seen, in a short sentence | `sshd: brute force … en web-01` |
| `relevance` | Why it matters for this finding | `Alerta que coincide con el patrón de la técnica.` |
| `source_fields[]` | One item per original field used: `{alert_id, path, value}` | `{"path": "/alerts/2/raw_alert/rule/description", "value": "sshd: brute force …"}` |

## 2. Criteria

### Alert IDs

| ID | Criterion | Verified by | Status |
| --- | --- | --- | --- |
| EV-01 | Every `alert_id` in the report (evidence, timeline, actions, blast radius, correlation, IoC) exists in the submitted case. | Validator `check_ref`; `test_validador_rechaza_referencia_rota_y_el_grafo_no_pasa_a_revision` | Met |
| EV-02 | The ID is the native one; a local `alert-NNN` is used only when the alert has none, and a warning says so. | `normalize_alert`; warnings | Met |
| EV-03 | Duplicate alert IDs in a case are reported. Correlation is then skipped on the direct path and the limitations say so. | `normalize_case` warnings; `correlate_direct` | Met, no dedicated test |

### Original field paths

| ID | Criterion | Verified by | Status |
| --- | --- | --- | --- |
| EV-04 | `path` is an RFC 6901 JSON Pointer into the **case as submitted** (`/alerts/{i}/raw_alert/…` through the API, `/alerts/{i}/…` on the direct path), with `~0` and `~1` escaping. | `verify_traceability`; `test_evidencia_cita_campos_originales_en_ruta_directa` | Met |
| EV-05 | The pointer belongs to the same alert as the `alert_id` it is listed under. | `verify_traceability` (`Evidence pointer belongs to a different alert`) | Met |
| EV-06 | Both flat (`"host.name"`) and nested (`host.name`) layouts are cited where they really are, including the Elastic `_source` export envelope. | `read_field`; correlation tests | Met; nested exports are #45 |
| EV-07 | Timeline, MITRE mapping and hypothesis evidence all carry `source_fields`. | `test_timeline_entries_cite_the_original_fields`, `test_evidencia_cita_campos_originales_en_ruta_directa` | Met |
| EV-08 | Blast-radius entries and recommended actions cite alert IDs. Field pointers for them are not required. | Validator | Met (IDs only, by design) |

### Observed values

| ID | Criterion | Verified by | Status |
| --- | --- | --- | --- |
| EV-09 | `value` is exactly the JSON value at `path` in the submitted case. Normalized values (lowercase, UTC) are never shown as the observed value. | `verify_traceability` (`Evidence value differs from the original payload`) | Met |
| EV-10 | The original payload (`original_case`, `raw_alert`) is stored unchanged; the agent works on copies. | `test_evidence_survives_restart_...`, `test_restart_preserves_evidence_and_submitted_id_uniqueness` | Met |
| EV-11 | Only the fields the agent actually used are cited (`SIGNAL_PATHS` plus the timestamp). Custom fields stay in the raw payload but are not cited unless a rule reads them. | `app/services/evidence.py` | Met; custom fields are #45 |
| EV-12 | A missing field is never invented: it has no `source_fields` entry, and if it is a key field (ID, timestamp, rule name, host) the gap is listed in `input.missing_fields`. | `normalize_alert` | Met, no dedicated test (#45) |
| EV-13 | Free text in `observation` is built from cited values only. | — | **Not verified**: the check covers `source_fields`, not `observation` |

### IoC references

| ID | Criterion | Verified by | Status |
| --- | --- | --- | --- |
| EV-14 | Each IoC item keeps the provider, observable and `raw_result` exactly as supplied, plus its `evidence_id` and `source_path` into the case. | `test_typed_match_preserves_provider_payload_and_references`; `verify_traceability` | Met |
| EV-15 | Each link between an IoC and an alert says how it was made: `explicit_reference` (the case declared it) and/or `observable_match` (same typed value in a cited field). The two are never mixed up. | `test_explicit_link_is_distinct_from_observed_match`, `test_both_link_types_and_multiple_providers_remain_separate` | Met |
| EV-16 | No match on substrings, alert IDs or free text. | `test_no_false_match_on_alert_id_message_or_substring` | Met |
| EV-17 | Hypotheses cite IoCs as `context`. They never raise confidence and the agent adds no verdict of its own. | `test_findings_reference_real_ioc_evidence_without_increasing_confidence` | Met |
| EV-18 | No external lookups; a case without enrichment says `no_disponible`. | `test_sin_enriquecimiento_se_declara_no_disponible`, `test_no_enrichment_is_supported` | Met |

### Enforcement

| ID | Criterion | Verified by | Status |
| --- | --- | --- | --- |
| EV-19 | On the API path, a report that breaks any EV rule is rejected: the investigation fails, the accepted case is kept and can be retried. | `verify_traceability` in `investigation_service`; `test_failure_retains_accepted_evidence_and_allows_retry` | Met |
| EV-20 | On the direct path, the same rules hold. | Tests only | **Partly**: `verify_traceability` runs only on the API path; the direct path is checked by tests, not at runtime |

## 3. What #44 and #45 should add

- **#44**: run the pointer and value checks on the direct path too (EV-20),
  and reject reports whose `observation` mentions values that are not cited
  (EV-13).
- **#45**: fixtures for custom fields, nested `_source` exports, missing
  values, non-string values (a numeric `@timestamp`) and two providers that
  disagree about one observable.

## Decisions for Ethan

1. EV-08: are alert IDs enough for the blast radius and actions, or should
   they also carry field pointers (for example the `host.name` that makes a
   host suspected)?
2. EV-13: tracing the free text is hard to do strictly. Accept "every value
   quoted in `observation` must appear in `source_fields`" as the rule?
3. EV-20: validate at runtime on the direct path (it would fail
   `run_synthetic` on a broken report) or keep it test-only?
