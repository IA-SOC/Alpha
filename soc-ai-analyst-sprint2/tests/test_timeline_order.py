"""S3-US4-T05 (#31): timeline order and links back to the original alerts.

Criteria used here until #27 lands, taken from the skill protocol
(references/protocolo.md, phase 3 and "Tiempos"):

- events with a known time are ordered by their UTC instant;
- equal timestamps keep the order in which the alerts were submitted;
- explicit offsets are converted to UTC and the original value is kept;
- a time without a zone is flagged as unknown and never turned into UTC;
- undated or zone-less events are kept apart from the dated sequence;
- every entry points to exactly one submitted alert, and none is lost.

"""

from copy import deepcopy
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.traceability import verify_traceability
from tests.helpers import investigate, tagged

ALERTS = [
    tagged("late", ["brute_force"], time="2026-10-09T12:10:00Z"),
    tagged("undated", ["brute_force"], time=None),
    tagged("no-zone", ["brute_force"], time="2026-10-09T12:05:00"),
    tagged("offset", ["brute_force"], time="2026-10-09T07:02:00-05:00"),
    tagged("tie-1", ["brute_force"], time="2026-10-09T12:00:00Z"),
    tagged("tie-2", ["brute_force"], time="2026-10-09T12:00:00Z"),
    tagged(
        "early",
        ["phishing"],
        ip="198.51.100.77",
        host="mail-09",
        user="other",
        time="2026-10-09T11:00:00Z",
    ),
]
DATED_ORDER = ["early", "tie-1", "tie-2", "offset", "late"]


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    path = tmp_path_factory.mktemp("timeline") / "cases.sqlite3"
    with TestClient(create_app(database_path=path)) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def result(client):
    return investigate(client, *ALERTS)


@pytest.fixture(scope="module")
def timeline(result):
    return result["report"]["timeline"]


def entry(timeline, alert_id):
    return next(t for t in timeline if t["alert_ids"] == [alert_id])


def test_dated_events_follow_their_utc_instant(timeline):
    dated = [t for t in timeline if t["timestamp_utc"]]
    assert [t["alert_ids"][0] for t in dated] == DATED_ORDER
    instants = [datetime.fromisoformat(t["timestamp_utc"]) for t in dated]
    assert instants == sorted(instants)


def test_equal_timestamps_keep_submission_order(client):
    reversed_ties = [
        tagged("tie-b", ["brute_force"], time="2026-10-09T12:00:00Z"),
        tagged("tie-a", ["brute_force"], time="2026-10-09T12:00:00Z"),
    ]
    timeline = investigate(client, *reversed_ties)["report"]["timeline"]
    assert [t["alert_ids"][0] for t in timeline] == ["tie-b", "tie-a"]


def test_offsets_become_utc_and_keep_the_original_value(timeline):
    offset = entry(timeline, "offset")
    assert offset["timestamp_original"] == "2026-10-09T07:02:00-05:00"
    assert datetime.fromisoformat(offset["timestamp_utc"]) == datetime.fromisoformat(
        "2026-10-09T12:02:00+00:00"
    )
    assert offset["timezone_unknown"] is False


def test_missing_zone_is_flagged_and_never_assumed_utc(timeline):
    no_zone = entry(timeline, "no-zone")
    assert no_zone["timestamp_original"] == "2026-10-09T12:05:00"
    assert no_zone["timestamp_utc"] is None
    assert no_zone["timezone_unknown"] is True


def test_undated_and_zone_less_events_come_after_the_dated_sequence(timeline):
    positions = [bool(t["timestamp_utc"]) for t in timeline]
    first_without_time = positions.index(False)
    assert all(positions[:first_without_time])
    assert not any(positions[first_without_time:])


def test_every_entry_points_to_one_submitted_alert(result, timeline):
    submitted = [alert["alert_id"] for alert in ALERTS]
    assert all(len(t["alert_ids"]) == 1 for t in timeline)
    assert sorted(t["alert_ids"][0] for t in timeline) == sorted(submitted)
    for alert in ALERTS:
        raw = alert["raw_alert"]
        assert entry(timeline, alert["alert_id"])["timestamp_original"] == raw.get(
            "@timestamp"
        )
    verify_traceability(result["investigation_context"], result["report"])


def test_entries_are_observed_not_inferred(timeline):
    assert {t["certainty"] for t in timeline} == {"observed"}


def test_timeline_entries_cite_the_original_fields(result, timeline):
    """#43: each entry points to the raw fields it came from; tampering is caught."""
    for t in timeline:
        assert t["source_fields"]
        assert {f["alert_id"] for f in t["source_fields"]} == set(t["alert_ids"])
    stamp = next(
        f
        for f in entry(timeline, "offset")["source_fields"]
        if f["path"].endswith("@timestamp")
    )
    assert stamp["path"] == "/alerts/3/raw_alert/@timestamp"
    assert stamp["value"] == "2026-10-09T07:02:00-05:00"
    broken = deepcopy(result["report"])
    broken["timeline"][0]["source_fields"][0]["value"] = "tampered"
    with pytest.raises(ValueError):
        verify_traceability(result["investigation_context"], broken)
