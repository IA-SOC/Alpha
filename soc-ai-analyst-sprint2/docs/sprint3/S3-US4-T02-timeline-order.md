# S3-US4-T02 (#28): timeline order and undated events

Parent story: #4, reconstruct a chronological incident timeline.

## Problem

`core/logic.build_timeline` sorted alerts by the `timestamp` **string**.

- Undated alerts carry `""`, so they sorted to the **top** of the timeline,
  mixed in with the dated sequence.
- In the direct path a zone-less time keeps its original string, so it was
  compared as text against UTC strings and landed in an arbitrary place.
- Text order is not time order: `10:00:00Z` sorts after `10:00:00.5Z`.

The strict xfail `test_undated_and_zone_less_events_come_after_the_dated_sequence`
from #31 documented this.

## Change

| File | What changed |
| --- | --- |
| `core/logic.py` | New `_utc_instant()` parses the time and returns `None` if it is missing, invalid or has no zone. `build_timeline` orders dated events by that instant (Python's stable sort keeps submission order for ties), then appends undated and zone-less events in submission order. |
| `agent/render.py` | The Markdown report shows the undated events under their own heading, "Eventos sin hora UTC utilizable (fuera de la secuencia)". |
| `servers/timeline_server.py` | Tool docstring describes the new order. |
| `tests/test_timeline_order.py` | xfail marker removed. |

Zone-less times are still never assumed to be UTC: `timestamp_utc` stays
`null` and `timezone_unknown` stays `true`.

## How to check

```powershell
python -m pytest tests/test_timeline_order.py -q
```

Covered: UTC order including a `-05:00` offset, ties in submission order,
offsets converted with the original kept, zone-less flagged and not converted,
undated and zone-less events after the dated sequence.
