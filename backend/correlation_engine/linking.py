"""Pure correlation logic: infer causal links among events and rank root causes.

Dependency-free (stdlib only) so it is cheap to unit-test in isolation. The
persistence wrapper lives in ``correlation_engine.correlator``.

Two complementary signals, both honouring temporal direction (a cause never
comes after its effect):

  * causal rules (Phase 2) — workspace-configured cause/effect predicates link
    each effect to its nearest preceding cause within an allowed lag; and
  * shared identifiers (Phase 1) — events sharing a strong identifier (an
    object/resource, or an IP from ``extra.ips``) are chained in time order
    within a bounded window.

Every link carries a confidence score and a human-readable ``basis``, and links
are de-duplicated per (source, target), preferring the higher-signal causal rule.
"""
from __future__ import annotations

from datetime import datetime, timezone


def _as_utc(ts: datetime) -> datetime:
    return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts


def _matches(event, predicate: dict) -> bool:
    if not predicate:
        return False
    for key, expected in predicate.items():
        actual = getattr(event, key, None)
        if actual is None or str(actual).lower() != str(expected).lower():
            return False
    return True


def _scope_key(event, scope: list):
    return tuple(getattr(event, k, None) for k in (scope or []))


def _summ(event) -> str:
    if event is None:
        return "event"
    parts = [p for p in (getattr(event, "action", None), getattr(event, "object", None)) if p]
    label = " ".join(str(p) for p in parts) or (getattr(event, "raw", None) or "event")
    return str(label)[:60]


def _link(cause, effect, relation: str, link_type: str, confidence: float, basis: str) -> dict:
    return {
        "source_event_id": cause.id,
        "target_event_id": effect.id,
        "relation": relation,
        "link_type": link_type,
        "confidence": confidence,
        "basis": basis,
    }


def _rule_links(events: list, rule: dict, cfg) -> list:
    cause_pred = rule.get("cause", {}) or {}
    effect_pred = rule.get("effect", {}) or {}
    if not cause_pred or not effect_pred:
        return []
    name = rule.get("name", "causal")
    scope = rule.get("scope", []) or []
    max_lag = rule.get("max_lag_seconds")

    causes_by_scope: dict = {}
    for c in events:
        if _matches(c, cause_pred):
            causes_by_scope.setdefault(_scope_key(c, scope), []).append(c)
    if not causes_by_scope:
        return []

    links = []
    for ef in events:
        if not _matches(ef, effect_pred):
            continue
        group = causes_by_scope.get(_scope_key(ef, scope), [])
        prior = [c for c in group if c.id != ef.id and _as_utc(c.timestamp) <= _as_utc(ef.timestamp)]
        if not prior:
            continue
        nearest = max(prior, key=lambda c: _as_utc(c.timestamp))
        lag = (_as_utc(ef.timestamp) - _as_utc(nearest.timestamp)).total_seconds()
        if max_lag is not None and lag > max_lag:
            continue
        confidence = cfg.causal_rule_confidence
        if max_lag:
            confidence = round(confidence * (1 - 0.4 * min(lag / max_lag, 1.0)), 3)
        basis = f"rule '{name}': '{_summ(nearest)}' → '{_summ(ef)}' (lag {int(lag)}s)"
        links.append(_link(nearest, ef, name, "causal_rule", confidence, basis))
    return links


def _chain(events: list, relation: str, basis_label: str, cfg) -> list:
    if len(events) < 2:
        return []
    ordered = sorted(events, key=lambda x: _as_utc(x.timestamp))
    links = []
    for i in range(1, len(ordered)):
        a, b = ordered[i - 1], ordered[i]
        if a.id == b.id:
            continue
        gap = (_as_utc(b.timestamp) - _as_utc(a.timestamp)).total_seconds()
        if gap > cfg.max_window_seconds:
            continue
        links.append(_link(a, b, relation, "shared_identifier", cfg.shared_identifier_confidence, basis_label))
    return links


def _identifier_links(events: list, field: str, cfg) -> list:
    groups: dict = {}
    for e in events:
        val = getattr(e, field, None)
        if isinstance(val, str) and val.strip():
            groups.setdefault(val.strip(), []).append(e)
    links = []
    for val, evs in groups.items():
        links.extend(_chain(evs, f"same_{field}", f"shared {field}={val}", cfg))
    return links


def _ip_links(events: list, cfg) -> list:
    groups: dict = {}
    for e in events:
        extra = getattr(e, "extra", None) or {}
        for ip in (extra.get("ips") or []):
            groups.setdefault(ip, []).append(e)
    links = []
    for ip, evs in groups.items():
        links.extend(_chain(evs, "same_ip", f"shared ip={ip}", cfg))
    return links


def _dedupe(links: list) -> list:
    def rank(l):
        return (1 if l["link_type"] == "causal_rule" else 0, l["confidence"])

    best: dict = {}
    for l in links:
        key = (l["source_event_id"], l["target_event_id"])
        if key[0] == key[1]:
            continue
        if key not in best or rank(l) > rank(best[key]):
            best[key] = l
    return list(best.values())


def build_links(events: list, cfg) -> list:
    """Infer causal links among ``events`` using ``cfg``.

    ``events`` are event-like objects exposing id/timestamp/actor/action/object/
    extra. Returns a de-duplicated list of link dicts. Events without a
    timestamp are skipped (causal ordering is undefined without time).
    """
    ordered = [e for e in events if getattr(e, "timestamp", None) is not None]
    links: list = []
    for rule in (getattr(cfg, "rules", None) or []):
        links.extend(_rule_links(ordered, rule, cfg))
    for field in (getattr(cfg, "identifier_fields", None) or []):
        if field == "ip":
            links.extend(_ip_links(ordered, cfg))
        else:
            links.extend(_identifier_links(ordered, field, cfg))
    return _dedupe(links)


def rank_root_causes(events: list, links: list, limit: int = 5) -> list:
    """Rank candidate root causes: chain origins (events that cause links but are
    caused by none), by downstream reach (how many events they ultimately lead
    to). Returns up to ``limit`` entries, most impactful first."""
    by_id = {e.id: e for e in events}
    adj: dict = {}
    sources: set = set()
    targets: set = set()
    for l in links:
        adj.setdefault(l["source_event_id"], []).append(l["target_event_id"])
        sources.add(l["source_event_id"])
        targets.add(l["target_event_id"])

    origins = [s for s in sources if s not in targets]
    results = []
    for origin in origins:
        seen: set = set()
        stack = list(adj.get(origin, []))
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(adj.get(node, []))
        results.append({"event_id": origin, "reach": len(seen), "summary": _summ(by_id.get(origin))})

    results.sort(key=lambda r: (r["reach"], str(r["event_id"])), reverse=True)
    return results[:limit]
