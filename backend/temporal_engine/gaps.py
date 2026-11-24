"""Evidence gap detector.

Finds time windows across the full investigation timeline where no evidence
exists. Unlike gap_anomaly (which detects large gaps *within* a single source),
this looks at the *merged* timeline across all sources and identifies windows
where the reconstructed sequence has no coverage — meaning something could have
happened that we have no evidence for.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional


def _as_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


def detect_gaps(events: list, min_gap_seconds: int = 1800) -> list[dict]:
    """Return a list of evidence gaps across the merged timeline.

    A gap is a window longer than ``min_gap_seconds`` where no events exist
    from *any* source. Each gap dict contains:
        start_time, end_time, duration_seconds, before_event_id, after_event_id
    """
    timestamped = [e for e in events if e.timestamp is not None]
    if len(timestamped) < 2:
        return []

    sorted_evs = sorted(timestamped, key=lambda e: _as_utc(e.timestamp))

    gaps = []
    for i in range(len(sorted_evs) - 1):
        a = sorted_evs[i]
        b = sorted_evs[i + 1]
        a_ts = _as_utc(a.timestamp)
        b_ts = _as_utc(b.timestamp)
        duration = (b_ts - a_ts).total_seconds()
        if duration >= min_gap_seconds:
            gaps.append({
                "start_time": a_ts.isoformat(),
                "end_time": b_ts.isoformat(),
                "duration_seconds": round(duration, 1),
                "before_event_id": str(a.id),
                "after_event_id": str(b.id),
                "description": (
                    f"No evidence for {_fmt_delta(timedelta(seconds=duration))} "
                    f"between {a_ts.strftime('%H:%M:%S')} and {b_ts.strftime('%H:%M:%S')}"
                ),
            })
    return gaps


def _fmt_delta(td: timedelta) -> str:
    secs = int(abs(td.total_seconds()))
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m {secs % 60}s"
    return f"{secs // 3600}h {(secs % 3600) // 60}m"
