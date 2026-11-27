"""Tests for the evidence gap detector (backend/temporal_engine/gaps.py).

``detect_gaps`` is pure: it only reads ``.timestamp`` and ``.id`` from event
objects and returns plain dicts.  Minimal dataclasses are used as event doubles.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from temporal_engine.gaps import detect_gaps

BASE = datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc)


@dataclass
class Ev:
    id: str
    timestamp: datetime | None


# ── Basic detection ───────────────────────────────────────────────────────────

def test_no_gap_when_events_are_close():
    events = [
        Ev("1", BASE),
        Ev("2", BASE + timedelta(minutes=10)),
        Ev("3", BASE + timedelta(minutes=20)),
    ]
    assert detect_gaps(events, min_gap_seconds=1800) == []


def test_gap_detected_when_window_exceeds_threshold():
    events = [Ev("1", BASE), Ev("2", BASE + timedelta(hours=1))]
    gaps = detect_gaps(events, min_gap_seconds=1800)
    assert len(gaps) == 1


def test_gap_references_correct_event_ids():
    events = [Ev("first", BASE), Ev("second", BASE + timedelta(hours=1))]
    gap = detect_gaps(events, min_gap_seconds=1800)[0]
    assert gap["before_event_id"] == "first"
    assert gap["after_event_id"] == "second"


def test_gap_duration_is_correct():
    events = [Ev("1", BASE), Ev("2", BASE + timedelta(hours=2))]
    gap = detect_gaps(events, min_gap_seconds=1800)[0]
    assert gap["duration_seconds"] == 7200.0


def test_multiple_gaps_all_detected():
    events = [
        Ev("1", BASE),
        Ev("2", BASE + timedelta(hours=2)),
        Ev("3", BASE + timedelta(hours=5)),
    ]
    gaps = detect_gaps(events, min_gap_seconds=1800)
    assert len(gaps) == 2


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_fewer_than_two_events_returns_empty():
    assert detect_gaps([Ev("1", BASE)], min_gap_seconds=1800) == []
    assert detect_gaps([], min_gap_seconds=1800) == []


def test_single_event_without_timestamp_returns_empty():
    assert detect_gaps([Ev("1", None)]) == []


def test_events_without_timestamp_are_skipped():
    events = [Ev("1", BASE), Ev("no-ts", None), Ev("3", BASE + timedelta(hours=2))]
    gaps = detect_gaps(events, min_gap_seconds=1800)
    assert len(gaps) == 1
    gap = gaps[0]
    assert gap["before_event_id"] == "1"
    assert gap["after_event_id"] == "3"


def test_all_events_without_timestamps_returns_empty():
    events = [Ev("1", None), Ev("2", None)]
    assert detect_gaps(events) == []


# ── Threshold boundary conditions ────────────────────────────────────────────

def test_exactly_at_threshold_is_included():
    events = [Ev("1", BASE), Ev("2", BASE + timedelta(seconds=1800))]
    gaps = detect_gaps(events, min_gap_seconds=1800)
    assert len(gaps) == 1


def test_one_second_under_threshold_not_flagged():
    events = [Ev("1", BASE), Ev("2", BASE + timedelta(seconds=1799))]
    assert detect_gaps(events, min_gap_seconds=1800) == []


# ── Timezone handling ─────────────────────────────────────────────────────────

def test_naive_timestamps_treated_as_utc():
    naive = datetime(2026, 11, 20, 12, 0, 0)  # no tzinfo — 2 h after BASE
    events = [Ev("1", BASE), Ev("2", naive)]
    gaps = detect_gaps(events, min_gap_seconds=1800)
    assert len(gaps) == 1
    assert gaps[0]["duration_seconds"] == 7200.0


def test_mixed_aware_and_naive_timestamps_do_not_crash():
    naive = datetime(2026, 11, 20, 10, 30, 0)
    events = [Ev("1", BASE), Ev("2", naive), Ev("3", BASE + timedelta(hours=3))]
    gaps = detect_gaps(events, min_gap_seconds=1800)
    assert isinstance(gaps, list)


# ── Output structure ──────────────────────────────────────────────────────────

def test_gap_dict_has_required_keys():
    events = [Ev("1", BASE), Ev("2", BASE + timedelta(hours=1))]
    gap = detect_gaps(events, min_gap_seconds=1800)[0]
    for key in ("start_time", "end_time", "duration_seconds", "before_event_id", "after_event_id", "description"):
        assert key in gap, f"Missing key: {key}"


def test_gap_description_includes_time_window():
    events = [Ev("1", BASE), Ev("2", BASE + timedelta(hours=1))]
    gap = detect_gaps(events, min_gap_seconds=1800)[0]
    assert "10:00:00" in gap["description"]
    assert "11:00:00" in gap["description"]


def test_gaps_ordered_chronologically():
    events = [
        Ev("1", BASE),
        Ev("2", BASE + timedelta(hours=2)),
        Ev("3", BASE + timedelta(hours=5)),
    ]
    gaps = detect_gaps(events, min_gap_seconds=1800)
    durations = [g["duration_seconds"] for g in gaps]
    assert durations == sorted(durations)
