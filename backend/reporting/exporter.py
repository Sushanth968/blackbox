from typing import Optional
import uuid
import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.investigation import Investigation
from models.evidence_file import EvidenceFile
from models.event import Event
from models.entity import Entity
from models.relationship import Relationship
from models.note import Note
from models.flagged_event import FlaggedEvent
from temporal_engine.temporal import detect_conflicts


async def build_export(investigation_id: uuid.UUID, db: AsyncSession) -> dict:
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        return {}

    ev_files = (await db.execute(select(EvidenceFile).where(EvidenceFile.investigation_id == investigation_id))).scalars().all()
    events   = (await db.execute(select(Event).where(Event.investigation_id == investigation_id).order_by(Event.timestamp.asc().nullslast()))).scalars().all()
    entities = (await db.execute(select(Entity).where(Entity.investigation_id == investigation_id))).scalars().all()
    rels     = (await db.execute(select(Relationship).where(Relationship.investigation_id == investigation_id))).scalars().all()
    notes    = (await db.execute(select(Note).where(Note.investigation_id == investigation_id).order_by(Note.created_at.asc()))).scalars().all()
    flags    = (await db.execute(select(FlaggedEvent).where(FlaggedEvent.investigation_id == investigation_id))).scalars().all()

    flagged_ids = {str(f.event_id) for f in flags}
    conflicts = detect_conflicts(events)

    def _ts(dt) -> Optional[str]:
        return dt.isoformat() if dt else None

    return {
        "meta": {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "blackbox_version": "0.1.0",
        },
        "investigation": {
            "id": str(inv.id),
            "title": inv.title,
            "description": inv.description,
            "status": inv.status,
            "created_at": _ts(inv.created_at),
            "updated_at": _ts(inv.updated_at),
        },
        "summary": {
            "evidence_files": len(ev_files),
            "total_events": len(events),
            "flagged_events": len(flags),
            "entities": len(entities),
            "relationships": len(rels),
            "temporal_conflicts": len(conflicts),
            "notes": len(notes),
        },
        "evidence_files": [
            {
                "id": str(f.id),
                "name": f.original_name,
                "type": f.file_type,
                "size": f.file_size,
                "sha256": f.sha256,
                "status": f.status,
                "uploaded_at": _ts(f.uploaded_at),
            }
            for f in ev_files
        ],
        "events": [
            {
                "id": str(e.id),
                "timestamp": _ts(e.timestamp),
                "timestamp_confidence": e.timestamp_confidence,
                "source": e.source,
                "source_line": e.source_line,
                "actor": e.actor,
                "action": e.action,
                "object": e.object,
                "severity": e.severity,
                "flagged": str(e.id) in flagged_ids,
                "raw": e.raw,
                "extra": e.extra,
            }
            for e in events
        ],
        "temporal_conflicts": conflicts,
        "entities": [
            {
                "id": str(e.id),
                "name": e.name,
                "type": e.entity_type,
                "canonical_name": e.canonical_name,
            }
            for e in entities
        ],
        "relationships": [
            {
                "source": str(r.source_entity_id),
                "target": str(r.target_entity_id),
                "relation": r.relation,
                "event_id": str(r.event_id) if r.event_id else None,
            }
            for r in rels
        ],
        "notes": [
            {
                "id": str(n.id),
                "content": n.content,
                "author": n.author,
                "event_id": str(n.event_id) if n.event_id else None,
                "created_at": _ts(n.created_at),
            }
            for n in notes
        ],
        "flagged_events": [
            {
                "event_id": str(f.event_id),
                "label": f.label,
                "flagged_at": _ts(f.flagged_at),
            }
            for f in flags
        ],
    }


def render_text_report(data: dict) -> str:
    inv = data.get("investigation", {})
    s   = data.get("summary", {})
    lines = [
        "=" * 72,
        "BLACKBOX INVESTIGATION REPORT",
        "=" * 72,
        f"Title       : {inv.get('title')}",
        f"Status      : {inv.get('status')}",
        f"Description : {inv.get('description') or '—'}",
        f"Created     : {inv.get('created_at')}",
        f"Exported    : {data.get('meta', {}).get('exported_at')}",
        "",
        "SUMMARY",
        "-" * 40,
        f"  Evidence files     : {s.get('evidence_files')}",
        f"  Total events       : {s.get('total_events')}",
        f"  Flagged events     : {s.get('flagged_events')}",
        f"  Entities           : {s.get('entities')}",
        f"  Relationships      : {s.get('relationships')}",
        f"  Temporal conflicts : {s.get('temporal_conflicts')}",
        f"  Notes              : {s.get('notes')}",
        "",
    ]

    lines += ["EVIDENCE FILES", "-" * 40]
    for f in data.get("evidence_files", []):
        lines.append(f"  [{f.get('status','?'):10s}] {f.get('name')}  ({f.get('type','?').upper()}, {(f.get('size') or 0)//1024} KB)")
        if f.get("sha256"):
            lines.append(f"             SHA-256: {f['sha256']}")
    lines.append("")

    conflicts = data.get("temporal_conflicts", [])
    if conflicts:
        lines += ["TEMPORAL CONFLICTS", "-" * 40]
        for c in conflicts:
            lines.append(f"  [{c.get('type','?'):22s}] {c.get('description')}")
        lines.append("")

    flagged = data.get("flagged_events", [])
    if flagged:
        flagged_ids = {f["event_id"] for f in flagged}
        flagged_map = {f["event_id"]: f.get("label") for f in flagged}
        lines += ["FLAGGED EVENTS", "-" * 40]
        for ev in data.get("events", []):
            if ev.get("id") in flagged_ids:
                label = flagged_map.get(ev["id"]) or ""
                ts = ev.get("timestamp") or "no-ts"
                actor = ev.get("actor") or ""
                action = ev.get("action") or ""
                obj = (ev.get("object") or "")[:60]
                lines.append(f"  {ts[:19]}  {ev.get('severity','?'):8s}  {actor:20s}  {action:15s}  {obj}")
                if label:
                    lines.append(f"    Label: {label}")
        lines.append("")

    notes = data.get("notes", [])
    if notes:
        lines += ["NOTES", "-" * 40]
        for n in notes:
            author = f" [{n.get('author')}]" if n.get("author") else ""
            lines.append(f"  {n.get('created_at','')[:19]}{author}")
            for note_line in n.get("content", "").splitlines():
                lines.append(f"    {note_line}")
        lines.append("")

    entities = data.get("entities", [])
    if entities:
        lines += ["ENTITIES", "-" * 40]
        by_type: dict = {}
        for e in entities:
            by_type.setdefault(e.get("type", "?"), []).append(e.get("name", ""))
        for t, names in sorted(by_type.items()):
            lines.append(f"  {t}: {', '.join(names[:10])}" + (" …" if len(names) > 10 else ""))
        lines.append("")

    lines += ["=" * 72, "END OF REPORT", "=" * 72]
    return "\n".join(lines)
