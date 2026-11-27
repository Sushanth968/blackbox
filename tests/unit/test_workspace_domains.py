"""Proves the engine is domain-agnostic: a second, non-software workspace
(customer payment disputes) drives the *same* temporal engine via configuration
alone — no engine code changes.
"""
import contextlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from core.workspace import load_workspace_config, workspace as ws
from temporal_engine.temporal import detect_conflicts

DISPUTE_WS = "workspaces/dispute/workspace.yaml"  # relative to repo root (pytest cwd)
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


@contextlib.contextmanager
def _rules(rules):
    original = ws.temporal.dependency_rules
    ws.temporal.dependency_rules = rules
    try:
        yield
    finally:
        ws.temporal.dependency_rules = original


def test_dispute_workspace_loads_with_its_own_dependency_rules():
    cfg = load_workspace_config(DISPUTE_WS)
    assert cfg.name == "Customer Payment Dispute"
    names = {r["name"] for r in cfg.temporal.dependency_rules}
    assert {"refund-after-charge", "complaint-after-order"} <= names


def test_same_engine_flags_a_dispute_domain_violation_from_config():
    """A refund that precedes its charge (same transaction) is flagged by the
    SAME detector that catches 'deploy-before-build' — only the config differs."""
    cfg = load_workspace_config(DISPUTE_WS)
    with _rules(cfg.temporal.dependency_rules):
        events = [
            Ev("1", "ledger.csv", BASE, action="refund", object="txn-99", source_line=1),
            Ev("2", "ledger.csv", BASE + timedelta(hours=1), action="charge", object="txn-99", source_line=2),
        ]
        conflicts = detect_conflicts(events)
        assert any(c["type"] == "dependency_violation" for c in conflicts)
