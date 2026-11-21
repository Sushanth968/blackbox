from typing import Optional
import uuid
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from models.event import Event
from models.entity import Entity
from models.relationship import Relationship
from core.workspace import workspace as _ws

IP_RE = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
EMAIL_RE = re.compile(r'^[\w.+-]+@[\w.-]+\.[a-z]{2,}$', re.IGNORECASE)
HASH_RE = re.compile(r'^[0-9a-f]{7,64}$', re.IGNORECASE)
PATH_RE = re.compile(r'^/[\w./-]+')
URL_RE = re.compile(r'^https?://')


def _classify(name: str) -> str:
    if IP_RE.match(name):
        return "ip"
    if EMAIL_RE.match(name):
        return "email"
    if HASH_RE.match(name):
        return "hash"
    if PATH_RE.match(name):
        return "path"
    if URL_RE.match(name):
        return "url"
    return "user"


def _canonical(name: str) -> str:
    canon = name.strip().lower()
    return _ws.entities.aliases.get(canon, canon)


async def resolve_entities(investigation_id: uuid.UUID, db: AsyncSession) -> dict:
    await db.execute(
        delete(Relationship).where(Relationship.investigation_id == investigation_id)
    )
    await db.execute(
        delete(Entity).where(Entity.investigation_id == investigation_id)
    )
    await db.commit()

    result = await db.execute(
        select(Event).where(Event.investigation_id == investigation_id)
    )
    events = result.scalars().all()

    entity_map: dict = {}

    def get_or_create(name: str) -> Optional[Entity]:
        if not name or not name.strip():
            return None
        if name.strip().lower() in [i.lower() for i in _ws.entities.ignore]:
            return None
        canon = _canonical(name)
        if canon not in entity_map:
            ent = Entity(
                investigation_id=investigation_id,
                name=name.strip(),
                entity_type=_classify(name.strip()),
                canonical_name=canon,
            )
            db.add(ent)
            entity_map[canon] = ent
        return entity_map[canon]

    pending_rels: list = []

    for event in events:
        actor_canon = _canonical(event.actor) if event.actor else None
        if actor_canon:
            get_or_create(event.actor)

        object_canon = _canonical(event.object) if event.object else None
        if object_canon:
            get_or_create(event.object)

        if event.extra and "ips" in event.extra:
            for ip in (event.extra["ips"] or []):
                ip_canon = _canonical(ip)
                get_or_create(ip)
                if actor_canon and ip_canon and actor_canon != ip_canon:
                    pending_rels.append((actor_canon, ip_canon, "connected_from", event.id))

        if actor_canon and object_canon:
            rel = event.action or "interacted_with"
            pending_rels.append((actor_canon, object_canon, rel, event.id))

    await db.flush()

    for src_canon, tgt_canon, relation, event_id in pending_rels:
        src = entity_map.get(src_canon)
        tgt = entity_map.get(tgt_canon)
        if src and tgt:
            db.add(Relationship(
                investigation_id=investigation_id,
                source_entity_id=src.id,
                target_entity_id=tgt.id,
                relation=relation,
                event_id=event_id,
            ))

    await db.commit()

    return {
        "entities": len(entity_map),
        "relationships": len(pending_rels),
    }
