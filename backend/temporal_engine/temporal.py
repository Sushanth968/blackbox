"""Temporal reconciliation engine.

Detects inconsistencies in event timing across reconstructed events:
  * out_of_order        — a later source line carries an earlier timestamp
  * clock_skew          — same actor appears in two sources with a large gap
  * duplicate_timestamps— many events share one exact timestamp
  * gap_anomaly         — an unusually large gap vs the source's median
  * dependency_violation— a configured causal rule is broken (effect before cause)

All comparisons go through ``_as_utc`` so a mix of naive and tz-aware timestamps
(common across real multi-source evidence) never raises, and naive values are
treated as UTC.
"""
from typing import Optional
from datetime import datetime, timedelta, timezone

from core.workspace import workspace as _ws


def _as_utc(ts: datetime) -> datetime:
    """Coerce a timestamp to tz-aware UTC so naive and aware values compare
    safely. Naive timestamps are assumed to already be in UTC."""
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


def detect_conflicts(events: list) -> list:
    conflicts = []
    conflicts.extend(_out_of_order(events))
    conflicts.extend(_clock_skew(events))
    conflicts.extend(_duplicate_timestamps(events))
    conflicts.extend(_gap_anomalies(events))
    conflicts.extend(_dependency_violations(events))
    return conflicts


def _out_of_order(events: list) -> list:
    """Flag events whose file/line order contradicts timestamp order within one
    source: a later line carrying an earlier timestamp beyond the threshold."""
    threshold = _ws.temporal.out_of_order_threshold_seconds
    conflicts = []
    by_source: dict = {}
    for e in events:
        if e.source and e.timestamp:
            by_source.setdefault(e.source, []).append(e)
    for source, evs in by_source.items():
        ordered = sorted(evs, key=lambda x: x.source_line if x.source_line is not None else 0)
        for i in range(1, len(ordered)):
            prev, curr = ordered[i - 1], ordered[i]
            prev_ts, curr_ts = _as_utc(prev.timestamp), _as_utc(curr.timestamp)
            if curr_ts < prev_ts - timedelta(seconds=threshold):
                conflicts.append({
                    "type": "out_of_order",
                    "source": _basename(source),
                    "event_a_id": str(prev.id),
                    "event_b_id": str(curr.id),
                    "delta_seconds": (prev_ts - curr_ts).total_seconds(),
                    "description": (
                        f"[{_basename(source)}] Line {curr.source_line} is "
                        f"{_fmt_delta(prev_ts - curr_ts)} earlier in time than the "
                        f"preceding line {prev.source_line}"
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
        sorted_evs = sorted(evs, key=lambda x: _as_utc(x.timestamp))
        for i in range(1, len(sorted_evs)):
            prev, curr = sorted_evs[i - 1], sorted_evs[i]
            if prev.source == curr.source:
                continue
            skew = abs((_as_utc(curr.timestamp) - _as_utc(prev.timestamp)).total_seconds())
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
            key = _as_utc(e.timestamp).isoformat()
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
        sorted_evs = sorted(evs, key=lambda x: _as_utc(x.timestamp))
        gaps = []
        for i in range(len(sorted_evs) - 1):
            g = (_as_utc(sorted_evs[i + 1].timestamp) - _as_utc(sorted_evs[i].timestamp)).total_seconds()
            if g >= 0:
                gaps.append(g)
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


def _dependency_violations(events: list) -> list:
    """Detect violations of configured causal-dependency rules: an 'effect' event
    occurring with no preceding 'cause' in the same scope (e.g. a deploy with no
    prior build for that service), or later than an allowed lag after its cause."""
    rules = getattr(_ws.temporal, "dependency_rules", None) or []
    conflicts = []
    for rule in rules:
        name = rule.get("name", "dependency")
        cause_pred = rule.get("cause", {}) or {}
        effect_pred = rule.get("effect", {}) or {}
        scope = rule.get("scope", []) or []
        max_lag = rule.get("max_lag_seconds")

        effects = [e for e in events if e.timestamp and _matches(e, effect_pred)]
        if not effects:
            continue

        causes_by_scope: dict = {}
        for c in events:
            if c.timestamp and _matches(c, cause_pred):
                causes_by_scope.setdefault(_scope_key(c, scope), []).append(c)

        for ef in effects:
            group = causes_by_scope.get(_scope_key(ef, scope), [])
            prior = [c for c in group if _as_utc(c.timestamp) <= _as_utc(ef.timestamp)]
            if not prior:
                earliest = min(group, key=lambda c: _as_utc(c.timestamp)) if group else None
                delta = (
                    (_as_utc(earliest.timestamp) - _as_utc(ef.timestamp)).total_seconds()
                    if earliest else None
                )
                conflicts.append({
                    "type": "dependency_violation",
                    "rule": name,
                    "source": _basename(ef.source),
                    "event_a_id": str(earliest.id) if earliest else None,
                    "event_b_id": str(ef.id),
                    "delta_seconds": delta,
                    "description": _dependency_desc(name, ef, earliest, scope),
                })
            elif max_lag is not None:
                nearest = max(prior, key=lambda c: _as_utc(c.timestamp))
                lag = (_as_utc(ef.timestamp) - _as_utc(nearest.timestamp)).total_seconds()
                if lag > max_lag:
                    conflicts.append({
                        "type": "dependency_violation",
                        "rule": name,
                        "source": _basename(ef.source),
                        "event_a_id": str(nearest.id),
                        "event_b_id": str(ef.id),
                        "delta_seconds": lag,
                        "description": (
                            f"[{name}] '{_describe_event(ef)}' occurred "
                            f"{_fmt_delta(timedelta(seconds=lag))} after its cause "
                            f"(exceeds allowed {max_lag}s)"
                        ),
                    })
    return conflicts


def _matches(event, predicate: dict) -> bool:
    for key, expected in predicate.items():
        actual = getattr(event, key, None)
        if actual is None or str(actual).lower() != str(expected).lower():
            return False
    return True


def _scope_key(event, scope: list):
    return tuple(getattr(event, k, None) for k in scope)


def _describe_event(event) -> str:
    bits = [b for b in (getattr(event, "action", None), getattr(event, "object", None)) if b]
    return " ".join(str(b) for b in bits) or f"event {event.id}"


def _dependency_desc(name, effect, cause, scope) -> str:
    scope_str = ""
    if scope:
        vals = ", ".join(f"{k}={getattr(effect, k, '?')}" for k in scope)
        scope_str = f" ({vals})"
    if cause is None:
        return f"[{name}] '{_describe_event(effect)}'{scope_str} occurred with no preceding cause event"
    return (
        f"[{name}] '{_describe_event(effect)}'{scope_str} occurred before its "
        f"required cause '{_describe_event(cause)}'"
    )


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
