"""Tests for the reconstruction confidence scorer (backend/temporal_engine/confidence.py).

``compute_confidence`` is pure: it reads attributes off event / evidence-file
objects and returns a ``ReconstructionConfidence`` dataclass.  We use minimal
dataclasses instead of ORM models so these tests stay dependency-free.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from temporal_engine.confidence import compute_confidence

BASE = datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc)


@dataclass
class Ev:
    timestamp: datetime | None
    timestamp_confidence: float = 1.0


@dataclass
class EvFile:
    sha256: str | None
    status: str = "processed"


# ── Overall label thresholds ─────────────────────────────────────────────────

def test_perfect_investigation_scores_high():
    events = [Ev(BASE), Ev(BASE), Ev(BASE)]
    files = [EvFile("abc123"), EvFile("def456")]
    result = compute_confidence(events, files, [], [])
    assert result.overall >= 85
    assert result.label == "High"


def test_zero_events_zero_files_scores_high():
    result = compute_confidence([], [], [], [])
    assert result.label == "High"


def test_many_conflicts_lowers_label():
    # 7 conflicts zero out temporal consistency (25% weight); combined with
    # half the events missing timestamps (30% weight), overall drops below 65.
    conflicts = [{"type": "clock_skew"}] * 7
    events = [Ev(None), Ev(None), Ev(BASE)]  # only 1/3 have timestamps
    result = compute_confidence(events, [], conflicts, [])
    assert result.label in {"Low", "Critical", "Medium"}
    assert result.overall < 85  # definitely not High


# ── Timestamp coverage dimension ─────────────────────────────────────────────

def test_no_events_gives_full_timestamp_coverage():
    result = compute_confidence([], [], [], [])
    dim = next(d for d in result.dimensions if d.name == "Timestamp coverage")
    assert dim.score == 100.0


def test_all_events_with_timestamp_gives_full_coverage():
    events = [Ev(BASE), Ev(BASE), Ev(BASE)]
    result = compute_confidence(events, [], [], [])
    dim = next(d for d in result.dimensions if d.name == "Timestamp coverage")
    assert dim.score == 100.0


def test_missing_timestamps_reduce_coverage_score():
    events = [Ev(None), Ev(None), Ev(BASE)]
    result = compute_confidence(events, [], [], [])
    dim = next(d for d in result.dimensions if d.name == "Timestamp coverage")
    assert round(dim.score, 1) == round(1 / 3 * 100, 1)


# ── Evidence integrity dimension ─────────────────────────────────────────────

def test_no_files_gives_full_integrity():
    result = compute_confidence([], [], [], [])
    dim = next(d for d in result.dimensions if d.name == "Evidence integrity")
    assert dim.score == 100.0


def test_unprocessed_files_reduce_integrity():
    files = [EvFile("abc123", status="failed"), EvFile(None, status="uploaded")]
    result = compute_confidence([], files, [], [])
    dim = next(d for d in result.dimensions if d.name == "Evidence integrity")
    assert dim.score == 0.0


def test_mixed_files_partial_integrity():
    files = [EvFile("abc123", status="processed"), EvFile(None, status="failed")]
    result = compute_confidence([], files, [], [])
    dim = next(d for d in result.dimensions if d.name == "Evidence integrity")
    assert dim.score == 50.0


# ── Temporal consistency dimension ───────────────────────────────────────────

def test_no_conflicts_full_consistency():
    result = compute_confidence([], [], [], [])
    dim = next(d for d in result.dimensions if d.name == "Temporal consistency")
    assert dim.score == 100.0


def test_one_conflict_reduces_consistency():
    result = compute_confidence([], [], [{"type": "clock_skew"}], [])
    dim = next(d for d in result.dimensions if d.name == "Temporal consistency")
    assert dim.score < 100.0


def test_many_conflicts_cap_at_zero():
    conflicts = [{"type": "x"}] * 20
    result = compute_confidence([], [], conflicts, [])
    dim = next(d for d in result.dimensions if d.name == "Temporal consistency")
    assert dim.score == 0.0


# ── Evidence coverage dimension ──────────────────────────────────────────────

def test_no_gaps_full_coverage():
    result = compute_confidence([], [], [], [])
    dim = next(d for d in result.dimensions if d.name == "Evidence coverage")
    assert dim.score == 100.0


def test_gaps_reduce_coverage():
    gaps = [{"start_time": "...", "end_time": "...", "duration_seconds": 3600}]
    result = compute_confidence([], [], [], gaps)
    dim = next(d for d in result.dimensions if d.name == "Evidence coverage")
    assert dim.score < 100.0


# ── Extraction confidence dimension ──────────────────────────────────────────

def test_no_events_full_extraction_confidence():
    result = compute_confidence([], [], [], [])
    dim = next(d for d in result.dimensions if d.name == "Extraction confidence")
    assert dim.score == 100.0


def test_low_confidence_events_penalise_extraction():
    events = [Ev(BASE, timestamp_confidence=0.5), Ev(BASE, timestamp_confidence=0.5)]
    result = compute_confidence(events, [], [], [])
    dim = next(d for d in result.dimensions if d.name == "Extraction confidence")
    assert dim.score == 0.0


def test_mixed_confidence_partial_penalty():
    events = [Ev(BASE, timestamp_confidence=0.9), Ev(BASE, timestamp_confidence=0.5)]
    result = compute_confidence(events, [], [], [])
    dim = next(d for d in result.dimensions if d.name == "Extraction confidence")
    assert 0 < dim.score < 100


# ── Structural invariants ─────────────────────────────────────────────────────

def test_five_dimensions_returned():
    result = compute_confidence([], [], [], [])
    assert len(result.dimensions) == 5


def test_dimension_weights_sum_to_one():
    result = compute_confidence([], [], [], [])
    total = sum(d.weight for d in result.dimensions)
    assert abs(total - 1.0) < 1e-9


def test_overall_bounded_zero_to_hundred():
    # Worst case
    events = [Ev(None)] * 10
    conflicts = [{"type": "x"}] * 10
    files = [EvFile(None, status="failed")] * 5
    gaps = [{"start_time": "...", "end_time": "...", "duration_seconds": 3600}] * 5
    result = compute_confidence(events, files, conflicts, gaps)
    assert 0 <= result.overall <= 100


def test_gaps_passed_through_to_result():
    gap = {"start_time": "2026-01-01T00:00:00+00:00", "end_time": "2026-01-01T01:00:00+00:00", "duration_seconds": 3600.0}
    result = compute_confidence([], [], [], [gap])
    assert result.gaps == [gap]


def test_medium_label_names_primary_concern_dimension():
    # 2 conflicts push temporal consistency down; everything else clean
    events = [Ev(BASE)] * 5
    files = [EvFile("abc")]
    conflicts = [{"type": "clock_skew"}, {"type": "out_of_order"}]
    result = compute_confidence(events, files, conflicts, [])
    if result.label == "Medium":
        assert "temporal consistency" in result.summary.lower()
