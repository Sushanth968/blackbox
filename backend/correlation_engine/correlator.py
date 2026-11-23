"""Persistence wrapper for the correlation engine.

Recomputes and stores causal links for an investigation. The link-inference and
root-cause ranking logic is pure and lives in ``correlation_engine.linking``.
"""
from __future__ import annotations

import uuid as _uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.event import Event
from models.causal_link import CausalLink
from core.workspace import workspace as _ws
from correlation_engine.linking import build_links, rank_root_causes

__all__ = ["build_links", "rank_root_causes", "correlate_events"]


async def correlate_events(investigation_id: _uuid.UUID, db: AsyncSession) -> dict:
    """Recompute causal links for an investigation from scratch and persist them."""
    await db.execute(delete(CausalLink).where(CausalLink.investigation_id == investigation_id))
    await db.commit()

    cfg = _ws.correlation
    if not getattr(cfg, "enabled", True):
        return {"causal_links": 0, "root_causes": []}

    events = (await db.execute(
        select(Event).where(Event.investigation_id == investigation_id)
    )).scalars().all()

    links = build_links(events, cfg)
    for l in links:
        db.add(CausalLink(
            investigation_id=investigation_id,
            source_event_id=l["source_event_id"],
            target_event_id=l["target_event_id"],
            relation=l["relation"],
            link_type=l["link_type"],
            confidence=l["confidence"],
            basis=l["basis"],
        ))
    await db.commit()

    roots = rank_root_causes(events, links)
    return {
        "causal_links": len(links),
        "root_causes": [
            {"event_id": str(r["event_id"]), "reach": r["reach"], "summary": r["summary"]}
            for r in roots
        ],
    }
