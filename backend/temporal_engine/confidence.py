"""Reconstruction Confidence Score.

Computes a 0–100 score representing how much we can trust the reconstructed
timeline for an investigation. Lower score = more uncertainty.

Five penalty dimensions:
  1. timestamp_coverage   — % events that have a verified timestamp
  2. integrity_failures   — evidence files whose SHA-256 could not be verified
  3. unresolved_conflicts — temporal conflicts that remain open
  4. coverage_gaps        — time windows with no evidence (from gap detector)
  5. low_confidence_events— events with timestamp_confidence < 0.8
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConfidenceDimension:
    name: str
    score: float          # 0–100 for this dimension
    weight: float         # contribution weight (all weights sum to 1.0)
    detail: str           # human-readable explanation
    penalty: float        # penalty applied (0 = none, 100 = max)


@dataclass
class ReconstructionConfidence:
    overall: float                              # 0–100 final score
    label: str                                  # "High" / "Medium" / "Low" / "Critical"
    summary: str                                # one-line explanation
    dimensions: list[ConfidenceDimension] = field(default_factory=list)
    gaps: list[dict] = field(default_factory=list)   # evidence gaps (from gap detector)


def compute_confidence(
    events: list,
    evidence_files: list,
    conflicts: list,
    gaps: list[dict],
) -> ReconstructionConfidence:
    dimensions: list[ConfidenceDimension] = []

    total_events = len(events)
    total_files = len(evidence_files)

    # ── 1. Timestamp coverage (weight 0.30) ─────────────────────────────────
    if total_events == 0:
        ts_score = 100.0
        ts_detail = "No events yet"
    else:
        with_ts = sum(1 for e in events if e.timestamp is not None)
        ratio = with_ts / total_events
        ts_score = round(ratio * 100, 1)
        ts_detail = f"{with_ts}/{total_events} events have verified timestamps"
    dimensions.append(ConfidenceDimension(
        name="Timestamp coverage",
        score=ts_score,
        weight=0.30,
        detail=ts_detail,
        penalty=round(100 - ts_score, 1),
    ))

    # ── 2. Evidence integrity (weight 0.25) ──────────────────────────────────
    if total_files == 0:
        integrity_score = 100.0
        integrity_detail = "No evidence files uploaded"
    else:
        verified = sum(1 for f in evidence_files if f.sha256 and f.status == "processed")
        ratio = verified / total_files
        integrity_score = round(ratio * 100, 1)
        integrity_detail = f"{verified}/{total_files} evidence files integrity-verified (SHA-256)"
    dimensions.append(ConfidenceDimension(
        name="Evidence integrity",
        score=integrity_score,
        weight=0.25,
        detail=integrity_detail,
        penalty=round(100 - integrity_score, 1),
    ))

    # ── 3. Unresolved temporal conflicts (weight 0.25) ───────────────────────
    if not conflicts:
        conflict_score = 100.0
        conflict_detail = "No temporal conflicts detected"
    else:
        # Each conflict reduces score; diminishing returns after 5
        n = len(conflicts)
        penalty = min(100.0, n * 15)
        conflict_score = round(100 - penalty, 1)
        conflict_detail = f"{n} unresolved temporal conflict{'s' if n != 1 else ''} detected"
    dimensions.append(ConfidenceDimension(
        name="Temporal consistency",
        score=conflict_score,
        weight=0.25,
        detail=conflict_detail,
        penalty=round(100 - conflict_score, 1),
    ))

    # ── 4. Evidence coverage gaps (weight 0.10) ──────────────────────────────
    if not gaps:
        gap_score = 100.0
        gap_detail = "No coverage gaps in timeline"
    else:
        n = len(gaps)
        penalty = min(100.0, n * 20)
        gap_score = round(100 - penalty, 1)
        gap_detail = f"{n} time window{'s' if n != 1 else ''} with no evidence coverage"
    dimensions.append(ConfidenceDimension(
        name="Evidence coverage",
        score=gap_score,
        weight=0.10,
        detail=gap_detail,
        penalty=round(100 - gap_score, 1),
    ))

    # ── 5. Low-confidence extractions (weight 0.10) ──────────────────────────
    if total_events == 0:
        extract_score = 100.0
        extract_detail = "No events to assess"
    else:
        low = sum(1 for e in events if e.timestamp_confidence < 0.8)
        ratio = low / total_events
        penalty = round(ratio * 100, 1)
        extract_score = round(100 - penalty, 1)
        extract_detail = (
            f"{low} event{'s' if low != 1 else ''} with extraction confidence < 80%"
            if low else "All events extracted with high confidence"
        )
    dimensions.append(ConfidenceDimension(
        name="Extraction confidence",
        score=extract_score,
        weight=0.10,
        detail=extract_detail,
        penalty=round(100 - extract_score, 1),
    ))

    # ── Overall weighted score ───────────────────────────────────────────────
    overall = round(sum(d.score * d.weight for d in dimensions), 1)

    if overall >= 85:
        label = "High"
        summary = "Timeline reconstruction is reliable"
    elif overall >= 65:
        label = "Medium"
        top = max(dimensions, key=lambda d: d.penalty)
        summary = f"Moderate confidence — primary concern: {top.name.lower()}"
    elif overall >= 40:
        label = "Low"
        top = max(dimensions, key=lambda d: d.penalty)
        summary = f"Low confidence — significant issues with {top.name.lower()}"
    else:
        label = "Critical"
        summary = "Reconstruction unreliable — insufficient or conflicting evidence"

    return ReconstructionConfidence(
        overall=overall,
        label=label,
        summary=summary,
        dimensions=dimensions,
        gaps=gaps,
    )
