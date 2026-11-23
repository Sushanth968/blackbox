"""Tests for the correlation engine's pure logic (backend/correlation_engine/linking.py).

Covers causal-rule linking, shared-identifier chaining, de-duplication, and
root-cause ranking. Uses lightweight event-like stand-ins so no DB is required.
"""
from datetime import datetime, timedelta
from types import SimpleNamespace

from correlation_engine.linking import build_links, rank_root_causes

BASE = datetime(2024, 1, 1, 10, 0, 0)


def ev(eid, mins=0, **kw):
    kw.setdefault("actor", None)
    kw.setdefault("action", None)
    kw.setdefault("object", None)
    kw.setdefault("severity", "info")
    kw.setdefault("extra", None)
    kw.setdefault("raw", None)
    return SimpleNamespace(id=eid, timestamp=BASE + timedelta(minutes=mins), **kw)


class Cfg(SimpleNamespace):
    def __init__(self, **kw):
        kw.setdefault("max_window_seconds", 3600.0)
        kw.setdefault("shared_identifier_confidence", 0.75)
        kw.setdefault("causal_rule_confidence", 0.85)
        kw.setdefault("identifier_fields", [])
        kw.setdefault("rules", [])
        super().__init__(**kw)


def test_causal_rule_links_effect_to_nearest_prior_cause():
    events = [
        ev("build", 0, action="build", object="svc-a"),
        ev("deploy", 5, action="deploy", object="svc-a"),
    ]
    cfg = Cfg(rules=[{
        "name": "build-caused-deploy",
        "cause": {"action": "build"},
        "effect": {"action": "deploy"},
        "scope": ["object"],
        "max_lag_seconds": 1800,
    }])
    links = build_links(events, cfg)
    assert len(links) == 1
    assert links[0]["source_event_id"] == "build"
    assert links[0]["target_event_id"] == "deploy"
    assert links[0]["link_type"] == "causal_rule"
    assert links[0]["relation"] == "build-caused-deploy"


def test_causal_rule_respects_scope():
    # A build for svc-a must not be linked to a deploy of svc-b.
    events = [
        ev("build-a", 0, action="build", object="svc-a"),
        ev("deploy-b", 5, action="deploy", object="svc-b"),
    ]
    cfg = Cfg(rules=[{
        "name": "build-caused-deploy",
        "cause": {"action": "build"},
        "effect": {"action": "deploy"},
        "scope": ["object"],
        "max_lag_seconds": 1800,
    }])
    assert build_links(events, cfg) == []


def test_causal_rule_respects_max_lag():
    events = [
        ev("build", 0, action="build", object="svc-a"),
        ev("deploy", 60, action="deploy", object="svc-a"),  # 3600s > 1800s max
    ]
    cfg = Cfg(rules=[{
        "name": "build-caused-deploy",
        "cause": {"action": "build"},
        "effect": {"action": "deploy"},
        "scope": ["object"],
        "max_lag_seconds": 1800,
    }])
    assert build_links(events, cfg) == []


def test_cause_never_after_effect():
    # Effect occurs before the candidate cause -> no link.
    events = [
        ev("deploy", 0, action="deploy", object="svc-a"),
        ev("build", 5, action="build", object="svc-a"),
    ]
    cfg = Cfg(rules=[{
        "name": "build-caused-deploy",
        "cause": {"action": "build"},
        "effect": {"action": "deploy"},
        "scope": ["object"],
    }])
    assert build_links(events, cfg) == []


def test_shared_identifier_chains_in_time_order():
    events = [
        ev("e1", 0, object="/checkout"),
        ev("e2", 1, object="/checkout"),
        ev("e3", 2, object="/checkout"),
    ]
    cfg = Cfg(identifier_fields=["object"])
    links = build_links(events, cfg)
    pairs = {(l["source_event_id"], l["target_event_id"]) for l in links}
    assert pairs == {("e1", "e2"), ("e2", "e3")}
    assert all(l["link_type"] == "shared_identifier" for l in links)


def test_shared_identifier_respects_window():
    events = [
        ev("e1", 0, object="/checkout"),
        ev("e2", 120, object="/checkout"),  # 2h gap > 1h window
    ]
    cfg = Cfg(identifier_fields=["object"], max_window_seconds=3600)
    assert build_links(events, cfg) == []


def test_ip_chaining_from_extra():
    events = [
        ev("e1", 0, extra={"ips": ["10.0.0.1"]}),
        ev("e2", 1, extra={"ips": ["10.0.0.1"]}),
    ]
    cfg = Cfg(identifier_fields=["ip"])
    links = build_links(events, cfg)
    assert len(links) == 1
    assert links[0]["relation"] == "same_ip"


def test_dedupe_prefers_causal_rule_over_shared_identifier():
    # Same (build -> deploy) pair also shares object; must appear once as the rule.
    events = [
        ev("build", 0, action="build", object="svc-a"),
        ev("deploy", 5, action="deploy", object="svc-a"),
    ]
    cfg = Cfg(
        identifier_fields=["object"],
        rules=[{
            "name": "build-caused-deploy",
            "cause": {"action": "build"},
            "effect": {"action": "deploy"},
            "scope": ["object"],
            "max_lag_seconds": 1800,
        }],
    )
    links = build_links(events, cfg)
    assert len(links) == 1
    assert links[0]["link_type"] == "causal_rule"


def test_events_without_timestamp_are_skipped():
    events = [ev("e1", 0, object="/x"), SimpleNamespace(id="e2", timestamp=None, object="/x", extra=None)]
    cfg = Cfg(identifier_fields=["object"])
    assert build_links(events, cfg) == []


def test_rank_root_causes_by_downstream_reach():
    events = [ev(x) for x in ("a", "b", "c", "d")]
    # chain a -> b -> c, and a separate d with nothing downstream
    links = [
        {"source_event_id": "a", "target_event_id": "b", "link_type": "causal_rule", "confidence": 0.9},
        {"source_event_id": "b", "target_event_id": "c", "link_type": "causal_rule", "confidence": 0.9},
    ]
    roots = rank_root_causes(events, links)
    assert roots[0]["event_id"] == "a"
    assert roots[0]["reach"] == 2  # reaches b and c
    # b and c are targets, so only 'a' qualifies as an origin
    assert [r["event_id"] for r in roots] == ["a"]
