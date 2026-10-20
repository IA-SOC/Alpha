# S3-US4-T01 (#27): timeline acceptance criteria

Parent story: #4, reconstruct a chronological incident timeline.
Owner: Ethan. Used by #28 (implementation), #29 (persistence), #30 (fixtures)
and #31 (tests).

Sources: `skills/soc-case-investigator/references/protocolo.md` (phase 3 and
"Tiempos"), `references/report-schema.json` (`timeline`) and the validator
`scripts/validate_report.py`. Status is the behavior on `main` after PR #62.

## Criteria

### Ordering

| ID | Criterion | Verified by | Status |
| --- | --- | --- | --- |
| TL-01 | Events with a usable time are ordered by their **UTC instant**, never by the text of the timestamp. Explicit offsets (`-05:00`) are converted before comparing. | `test_dated_events_follow_their_utc_instant` | Met |
| TL-02 | Events with the **same UTC instant** keep the order in which the alerts were submitted. | `test_equal_timestamps_keep_submission_order` | Met |
| TL-03 | Events **without a usable time** (missing, invalid, without zone, or conflicting between fields) are not placed inside the dated sequence. They go after it, in submission order, and the Markdown report shows them under their own heading. | `test_undated_and_zone_less_events_come_after_the_dated_sequence` | Met |
| TL-04 | The order is the same on the API path and the direct path (`run_synthetic`, demo). | API tests in `test_timeline_order.py` | Partly: no direct-path ordering test |

### Times

| ID | Criterion | Verified by | Status |
| --- | --- | --- | --- |
| TL-05 | `timestamp_original` keeps the submitted value exactly, including its offset and precision. | `test_offsets_become_utc_and_keep_the_original_value`, `test_every_entry_points_to_one_submitted_alert` | Met |
| TL-06 | `timestamp_utc` is filled only when the original has an explicit zone. A time without a zone gets `timestamp_utc: null` and `timezone_unknown: true`; UTC is **never assumed**. | `test_missing_zone_is_flagged_and_never_assumed_utc` | Met |
| TL-07 | `submitted_at` or the processing time is never used in place of a missing event time. | Adapter warning "submitted_at is not substituted" | Met, no dedicated test |
| TL-08 | If `@timestamp` and `timestamp` disagree in one alert, the event has no UTC time and a warning says so. | `evidence.extract_events` | Met on the API path, no dedicated test (#30 fixture) |
| TL-09 | Every time problem is reported with its alert ID: a missing time in `input.missing_fields`, an invalid, zone-less or conflicting time in `input.warnings` (and from there in the limitations). | `normalize_case` | Met, no dedicated test |

### References

| ID | Criterion | Verified by | Status |
| --- | --- | --- | --- |
| TL-10 | Every submitted alert appears **exactly once** in the timeline; none is dropped, including noise and undated alerts. | `test_every_entry_points_to_one_submitted_alert` | Met |
| TL-11 | Each entry has `alert_ids` with **exactly one** ID, and that ID is the original alert ID (native ID, or `alert-NNN` only when the alert has none). | Same test; validator `check_ref` | Met |
| TL-12 | Each entry carries `source_fields` pointing to the original fields it came from, including the timestamp field. The rules for those references are the EV criteria of #42. | `test_timeline_entries_cite_the_original_fields` | Met |
| TL-13 | `certainty` is `observed` for events read from an alert. `inferred` is reserved for events the agent deduces; the agent does not produce any today. | `test_entries_are_observed_not_inferred` | Met |

### Persistence (input for #29)

| ID | Criterion | Verified by | Status |
| --- | --- | --- | --- |
| TL-14 | The API response and the stored report return the same timeline, with all the fields above, after a server restart. | `test_evidence_survives_restart_...` covers evidence, not the timeline fields | To verify in #29 |

## Out of scope

- Detecting clocks that drift between sources (the protocol mentions
  "relojes incoherentes"). It needs a reference clock that cases don't carry.
- Inferring a time for undated events from their neighbors.

## Fixtures that #30 needs

One Elastic, one Wazuh and one mixed case with: an explicit offset, two equal
UTC instants written differently (`12:00:00Z` and `07:00:00-05:00`), a
fractional-second time next to a whole-second one, a time without a zone, a
missing time, an invalid time, and one alert whose `@timestamp` and
`timestamp` disagree.

## Decisions for Ethan

1. TL-03: keep undated events **in** the `timeline` array, after the dated
   ones (current behavior), or move them to a separate `undated_events` field?
   The current choice keeps the report schema unchanged.
2. TL-08: should conflicting times also lower the confidence of the
   hypotheses that cite that alert? Today only a missing zone does.
