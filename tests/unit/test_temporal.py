"""Tests for the temporal conflict detector (backend/temporal_engine/temporal.py).

Thresholds and dependency rules come from the active workspace config (defaults
when none is set). These tests build lightweight event doubles — the detector
only reads the attributes below, so we don't need the ORM Event model or a DB.
"""
import contextlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from core.workspace import workspace as ws
from temporal_engine.temporal import detect_conflicts

BASE = datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc)


@dataclass
class Ev:
    id: str
    source: str
    timestamp: datetime
    actor: str | None = None
    action: str | None = None
    object: str | None = None
    source_line: int | None = None


def _types(conflicts):
    return {c["type"] for c in conflicts}


@contextlib.contextmanager
def _dependency_rules(rules):
    original = ws.temporal.dependency_rules
    ws.temporal.dependency_rules = rules
    try:
        yield
    finally:
        ws.temporal.dependency_rules = original


DEPLOY_AFTER_BUILD = {
    "name": "deploy-after-build",
    "cause": {"action": "build"},
    "effect": {"action": "deploy"},
    "scope": ["object"],
}


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


def test_clock_skew_flagged_for_same_actor_and_action_across_sources():
    skew = ws.temporal.clock_skew_threshold_seconds + 100
    events = [
        Ev("1", "git.log", BASE, actor="alice", action="commit", source_line=1),
        Ev("2", "ci.log", BASE + timedelta(seconds=skew), actor="alice", action="commit", source_line=1),
    ]
    assert "clock_skew" in _types(detect_conflicts(events))


def test_clock_skew_not_flagged_for_different_actions_elapsed_time():
    """Two different activities by one actor, far apart, are ordinary elapsed
    time across systems — not clock skew."""
    gap = ws.temporal.clock_skew_threshold_seconds + 100
    events = [
        Ev("1", "git.log", BASE, actor="alice", action="commit", source_line=1),
        Ev("2", "ci.log", BASE + timedelta(seconds=gap), actor="alice", action="deploy", source_line=1),
    ]
    assert "clock_skew" not in _types(detect_conflicts(events))


def test_clean_single_source_has_no_conflicts():
    events = [
        Ev(str(i), "app.log", BASE + timedelta(seconds=60 * i), source_line=i)
        for i in range(1, 5)
    ]
    assert detect_conflicts(events) == []


def test_out_of_order_flagged_when_line_order_contradicts_timestamps():
    """A later line carrying an earlier timestamp within one source is an
    out-of-order anomaly that must be reported."""
    events = [
        Ev("1", "app.log", BASE, source_line=1),
        Ev("2", "app.log", BASE - timedelta(seconds=120), source_line=2),
    ]
    assert "out_of_order" in _types(detect_conflicts(events))


def test_mixed_naive_and_aware_timestamps_do_not_crash():
    """Real multi-source investigations mix tz-aware and naive timestamps; the
    detector must treat naive as UTC rather than raising a TypeError."""
    naive = datetime(2026, 11, 20, 10, 0, 30)  # no tzinfo
    events = [
        Ev("1", "app.log", BASE, source_line=1),
        Ev("2", "app.log", naive, source_line=2),
    ]
    result = detect_conflicts(events)  # must not raise
    assert isinstance(result, list)


def test_dependency_violation_when_deploy_precedes_build():
    with _dependency_rules([DEPLOY_AFTER_BUILD]):
        events = [
            Ev("1", "ci.log", BASE, action="deploy", object="svc-a", source_line=1),
            Ev("2", "ci.log", BASE + timedelta(seconds=60), action="build", object="svc-a", source_line=2),
        ]
        assert "dependency_violation" in _types(detect_conflicts(events))


def test_no_dependency_violation_when_build_precedes_deploy():
    with _dependency_rules([DEPLOY_AFTER_BUILD]):
        events = [
            Ev("1", "ci.log", BASE, action="build", object="svc-a", source_line=1),
            Ev("2", "ci.log", BASE + timedelta(seconds=60), action="deploy", object="svc-a", source_line=2),
        ]
        assert "dependency_violation" not in _types(detect_conflicts(events))


def test_dependency_scope_isolates_by_object():
    with _dependency_rules([DEPLOY_AFTER_BUILD]):
        events = [
            Ev("1", "ci.log", BASE, action="build", object="svc-a", source_line=1),
            Ev("2", "ci.log", BASE + timedelta(seconds=60), action="deploy", object="svc-a", source_line=2),
            Ev("3", "ci.log", BASE + timedelta(seconds=120), action="deploy", object="svc-b", source_line=3),
        ]
        violations = [c for c in detect_conflicts(events) if c["type"] == "dependency_violation"]
        assert len(violations) == 1
        assert violations[0]["event_b_id"] == "3"
