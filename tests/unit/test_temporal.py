"""Tests for the temporal conflict detector (backend/temporal_engine/temporal.py).

Thresholds come from the active workspace config (defaults when none is set).
These tests build lightweight event doubles — the detector only reads the
attributes below, so we don't need the full ORM Event model or a database.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from core.workspace import workspace as ws
from temporal_engine.temporal import detect_conflicts

BASE = datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc)


@dataclass
class Ev:
    id: str
    source: str
    timestamp: datetime
    actor: str | None = None
    source_line: int | None = None


def _types(conflicts):
    return {c["type"] for c in conflicts}


def test_duplicate_timestamps_flagged():
    n = ws.temporal.duplicate_timestamp_min_count
    events = [Ev(str(i), "app.log", BASE, source_line=i) for i in range(n)]
    assert "duplicate_timestamps" in _types(detect_conflicts(events))


def test_gap_anomaly_flagged_for_large_gap():
    big = ws.temporal.gap_anomaly_min_seconds + 600
    events = [
        Ev("1", "app.log", BASE, source_line=1),
        Ev("2", "app.log", BASE + timedelta(seconds=60), source_line=2),
        Ev("3", "app.log", BASE + timedelta(seconds=120), source_line=3),
        Ev("4", "app.log", BASE + timedelta(seconds=180), source_line=4),
        Ev("5", "app.log", BASE + timedelta(seconds=180 + big), source_line=5),
    ]
    assert "gap_anomaly" in _types(detect_conflicts(events))


def test_clock_skew_flagged_across_sources_for_same_actor():
    skew = ws.temporal.clock_skew_threshold_seconds + 100
    events = [
        Ev("1", "git.log", BASE, actor="alice", source_line=1),
        Ev("2", "ci.log", BASE + timedelta(seconds=skew), actor="alice", source_line=1),
    ]
    assert "clock_skew" in _types(detect_conflicts(events))


def test_clean_single_source_has_no_conflicts():
    events = [
        Ev(str(i), "app.log", BASE + timedelta(seconds=60 * i), source_line=i)
        for i in range(1, 5)
    ]
    assert detect_conflicts(events) == []


@pytest.mark.xfail(
    strict=True,
    reason="Known bug: _out_of_order sorts events by timestamp before comparing, so it "
    "can never fire. Needs a line-order-vs-timestamp comparison. Follow-up PR.",
)
def test_out_of_order_flagged_when_line_order_contradicts_timestamps():
    """Line 2 has an earlier timestamp than line 1 in the same source — a classic
    out-of-order anomaly that should be reported."""
    events = [
        Ev("1", "app.log", BASE, source_line=1),
        Ev("2", "app.log", BASE - timedelta(seconds=120), source_line=2),
    ]
    assert "out_of_order" in _types(detect_conflicts(events))
