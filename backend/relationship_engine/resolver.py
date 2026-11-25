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
# Require at least one hex LETTER so pure-decimal ids (e.g. "1234567") are not
# mistaken for commit hashes.
HASH_RE = re.compile(r'^(?=.*[a-f])[0-9a-f]{7,64}$', re.IGNORECASE)
PATH_RE = re.compile(r'^/[\w./-]+')
URL_RE = re.compile(r'^https?://')

# Types where letter-case is NOT significant and may be folded for de-duplication.
_CASE_INSENSITIVE_TYPES = {"ip", "email", "hash"}


def classify_entity(name: str) -> str:
    name = (name or "").strip()
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


def canonicalize(name: str, entity_type: str, aliases: Optional[dict] = None) -> str:
    """Canonical form used for de-duplication.

    Case is folded only for types where it is not significant (ip/email/hash).
    Paths, URLs and usernames keep their original case, so '/Users/Foo' vs
    '/users/foo', or 'John' vs 'john', are NOT silently merged.
    """
    canon = (name or "").strip()
    if entity_type in _CASE_INSENSITIVE_TYPES:
        canon = canon.lower()
    aliases = aliases or {}
    return aliases.get(canon, aliases.get(canon.lower(), canon))


def entity_key(name: str):
    """Return the ``(entity_type, canonical)`` key used to de-duplicate entities.

    Keying on the type as well as the canonical string prevents a path and a
    username that happen to share a string from collapsing into one entity.
    """
    etype = classify_entity(name)
    return etype, canonicalize(name, etype, _ws.entities.aliases)


async def resolve_entities(investigation_id: uuid.UUID, db: AsyncSession) -> dict:
    await db.execute(delete(Relationship).where(Relationship.investigation_id == investigation_id))
    await db.execute(delete(Entity).where(Entity.investigation_id == investigation_id))
    await db.commit()

    result = await db.execute(select(Event).where(Event.investigation_id == investigation_id))
    events = result.scalars().all()

    ignore = {i.strip().lower() for i in _ws.entities.ignore}
    enabled_types = set(_ws.entities.extract)  # workspace decides which types to extract

    entity_map: dict = {}

    def get_or_create(name: str):
        if not name or not name.strip():
            return None
        etype = classify_entity(name)
        if etype not in enabled_types:
            return None
        if name.strip().lower() in ignore:
            return None
        key = (etype, canonicalize(name, etype, _ws.entities.aliases))
        if key not in entity_map:
            ent = Entity(
                investigation_id=investigation_id,
                name=name.strip(),
                entity_type=etype,
                canonical_name=key[1],
            )
            db.add(ent)
            entity_map[key] = ent
        return entity_map[key]

    pending_rels: list = []

    for event in events:
        actor_ent = get_or_create(event.actor) if event.actor else None
        object_ent = get_or_create(event.object) if event.object else None

        if event.extra and "ips" in event.extra:
            for ip in (event.extra["ips"] or []):
                ip_ent = get_or_create(ip)
                if actor_ent and ip_ent and actor_ent is not ip_ent:
                    pending_rels.append((actor_ent, ip_ent, "connected_from", event.id))

        if actor_ent and object_ent and actor_ent is not object_ent:
            rel = event.action or "interacted_with"
            pending_rels.append((actor_ent, object_ent, rel, event.id))

    await db.flush()

    for src, tgt, relation, event_id in pending_rels:
        db.add(Relationship(
            investigation_id=investigation_id,
            source_entity_id=src.id,
            target_entity_id=tgt.id,
            relation=relation,
            event_id=event_id,
        ))

    await db.commit()
    return {"entities": len(entity_map), "relationships": len(pending_rels)}
