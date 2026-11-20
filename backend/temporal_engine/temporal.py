from typing import Optional
from datetime import timedelta
from core.workspace import workspace as _ws


def detect_conflicts(events: list) -> list:
    conflicts = []
    conflicts.extend(_out_of_order(events))
    conflicts.extend(_clock_skew(events))
    conflicts.extend(_duplicate_timestamps(events))
    conflicts.extend(_gap_anomalies(events))
    return conflicts


def _out_of_order(events: list) -> list:
    threshold = _ws.temporal.out_of_order_threshold_seconds
    conflicts = []
    by_source: dict = {}
    for e in events:
        if e.source and e.timestamp:
            by_source.setdefault(e.source, []).append(e)
    for source, evs in by_source.items():
        sorted_evs = sorted(evs, key=lambda x: x.timestamp)
        for i in range(1, len(sorted_evs)):
            prev, curr = sorted_evs[i - 1], sorted_evs[i]
            if curr.timestamp < prev.timestamp - timedelta(seconds=threshold):
                conflicts.append({
                    "type": "out_of_order",
                    "source": _basename(source),
                    "event_a_id": str(prev.id),
                    "event_b_id": str(curr.id),
                    "delta_seconds": (prev.timestamp - curr.timestamp).total_seconds(),
                    "description": (
                        f"[{_basename(source)}] Line {curr.source_line} timestamp is "
                        f"{_fmt_delta(prev.timestamp - curr.timestamp)} before line {prev.source_line}"
                    ),
                })
    return conflicts


def _clock_skew(events: list) -> list:
    conflicts = []
    by_actor: dict = {}
    for e in events:
        if e.actor and e.timestamp:
            by_actor.setdefault(e.actor, []).append(e)
    for actor, evs in by_actor.items():
        sources = {e.source for e in evs}
        if len(sources) < 2:
            continue
        sorted_evs = sorted(evs, key=lambda x: x.timestamp)
        for i in range(1, len(sorted_evs)):
            prev, curr = sorted_evs[i - 1], sorted_evs[i]
            if prev.source == curr.source:
                continue
            skew = abs((curr.timestamp - prev.timestamp).total_seconds())
            if skew > _ws.temporal.clock_skew_threshold_seconds:
                conflicts.append({
                    "type": "clock_skew",
                    "source": f"{_basename(prev.source)} vs {_basename(curr.source)}",
                    "event_a_id": str(prev.id),
                    "event_b_id": str(curr.id),
                    "delta_seconds": skew,
                    "description": (
                        f"[clock skew] Actor '{actor}' appears in {_basename(prev.source)} "
                        f"and {_basename(curr.source)} with {_fmt_delta(timedelta(seconds=skew))} gap"
                    ),
                })
    return conflicts


def _duplicate_timestamps(events: list) -> list:
    conflicts = []
    by_source: dict = {}
    for e in events:
        if e.source and e.timestamp:
            by_source.setdefault(e.source, []).append(e)
    for source, evs in by_source.items():
        ts_map: dict = {}
        for e in evs:
            key = e.timestamp.isoformat()
            ts_map.setdefault(key, []).append(e)
        for ts_str, group in ts_map.items():
            if len(group) >= _ws.temporal.duplicate_timestamp_min_count:
                conflicts.append({
                    "type": "duplicate_timestamps",
                    "source": _basename(source),
                    "event_a_id": str(group[0].id),
                    "event_b_id": str(group[-1].id),
                    "delta_seconds": 0,
                    "description": (
                        f"[{_basename(source)}] {len(group)} events share identical timestamp {ts_str}"
                    ),
                })
    return conflicts


def _gap_anomalies(events: list) -> list:
    import statistics
    conflicts = []
    by_source: dict = {}
    for e in events:
        if e.source and e.timestamp:
            by_source.setdefault(e.source, []).append(e)
    for source, evs in by_source.items():
        if len(evs) < 4:
            continue
        sorted_evs = sorted(evs, key=lambda x: x.timestamp)
        gaps = [
            (sorted_evs[i + 1].timestamp - sorted_evs[i].timestamp).total_seconds()
            for i in range(len(sorted_evs) - 1)
            if (sorted_evs[i + 1].timestamp - sorted_evs[i].timestamp).total_seconds() >= 0
        ]
        if not gaps:
            continue
        try:
            median_gap = statistics.median(gaps)
        except Exception:
            continue
        if median_gap < 1:
            continue
        for i, gap in enumerate(gaps):
            if gap > max(median_gap * _ws.temporal.gap_anomaly_multiplier, _ws.temporal.gap_anomaly_min_seconds):
                conflicts.append({
                    "type": "gap_anomaly",
                    "source": _basename(source),
                    "event_a_id": str(sorted_evs[i].id),
                    "event_b_id": str(sorted_evs[i + 1].id),
                    "delta_seconds": gap,
                    "description": (
                        f"[{_basename(source)}] {_fmt_delta(timedelta(seconds=gap))} gap between "
                        f"line {sorted_evs[i].source_line} and {sorted_evs[i+1].source_line} "
                        f"(median gap: {_fmt_delta(timedelta(seconds=median_gap))})"
                    ),
                })
    return conflicts


def _basename(path: Optional[str]) -> str:
    if not path:
        return "unknown"
    return path.split("/")[-1]


def _fmt_delta(td: timedelta) -> str:
    secs = int(abs(td.total_seconds()))
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m {secs % 60}s"
    return f"{secs // 3600}h {(secs % 3600) // 60}m"
