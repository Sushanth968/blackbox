from typing import Optional
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import get_db
from models.event import Event
from models.entity import Entity
from models.relationship import Relationship
from models.note import Note
from models.flagged_event import FlaggedEvent
from schemas.event import EventOut, TimelineOut
from schemas.entity import EntityOut, GraphOut, RelationshipOut
from schemas.workspace import NoteCreate, NoteOut, FlagCreate, FlagOut
from temporal_engine.temporal import detect_conflicts
from relationship_engine.resolver import resolve_entities
from reporting.exporter import build_export, render_text_report

router = APIRouter()

# ── Events ──────────────────────────────────────────────────────────────────

@router.get("/{investigation_id}/events", response_model=list[EventOut])
async def list_events(
    investigation_id: uuid.UUID,
    source: Optional[str] = None,
    actor: Optional[str] = None,
    severity: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    q = select(Event).where(Event.investigation_id == investigation_id)
    if source:
        q = q.where(Event.source == source)
    if actor:
        q = q.where(Event.actor == actor)
    if severity:
        q = q.where(Event.severity == severity)
    q = q.order_by(Event.timestamp.asc().nullslast())
    result = await db.execute(q)
    return result.scalars().all()

# ── Timeline ────────────────────────────────────────────────────────────────

@router.get("/{investigation_id}/timeline", response_model=TimelineOut)
async def get_timeline(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Event)
        .where(Event.investigation_id == investigation_id)
        .order_by(Event.timestamp.asc().nullslast())
    )
    events = result.scalars().all()
    conflicts = detect_conflicts(events)
    return TimelineOut(events=events, conflicts=conflicts, total=len(events))

# ── Entities & Graph ────────────────────────────────────────────────────────

@router.post("/{investigation_id}/entities/resolve", response_model=dict)
async def trigger_resolve(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await resolve_entities(investigation_id, db)


@router.get("/{investigation_id}/graph", response_model=GraphOut)
async def get_graph(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    nodes_result = await db.execute(
        select(Entity).where(Entity.investigation_id == investigation_id)
    )
    edges_result = await db.execute(
        select(Relationship).where(Relationship.investigation_id == investigation_id)
    )
    return GraphOut(
        nodes=nodes_result.scalars().all(),
        edges=edges_result.scalars().all(),
    )

# ── Notes ───────────────────────────────────────────────────────────────────

@router.post("/{investigation_id}/notes", response_model=NoteOut, status_code=201)
async def create_note(investigation_id: uuid.UUID, payload: NoteCreate, db: AsyncSession = Depends(get_db)):
    note = Note(investigation_id=investigation_id, **payload.model_dump())
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note

@router.get("/{investigation_id}/notes", response_model=list[NoteOut])
async def list_notes(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Note).where(Note.investigation_id == investigation_id).order_by(Note.created_at.asc())
    )
    return result.scalars().all()

@router.patch("/{investigation_id}/notes/{note_id}", response_model=NoteOut)
async def update_note(investigation_id: uuid.UUID, note_id: uuid.UUID, payload: NoteCreate, db: AsyncSession = Depends(get_db)):
    note = await db.get(Note, note_id)
    if not note or note.investigation_id != investigation_id:
        raise HTTPException(404, "Note not found")
    note.content = payload.content
    await db.commit()
    await db.refresh(note)
    return note

@router.delete("/{investigation_id}/notes/{note_id}", status_code=204)
async def delete_note(investigation_id: uuid.UUID, note_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    note = await db.get(Note, note_id)
    if not note or note.investigation_id != investigation_id:
        raise HTTPException(404, "Note not found")
    await db.delete(note)
    await db.commit()

# ── Flags ───────────────────────────────────────────────────────────────────

@router.post("/{investigation_id}/flags", response_model=FlagOut, status_code=201)
async def flag_event(investigation_id: uuid.UUID, payload: FlagCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FlaggedEvent).where(
            FlaggedEvent.investigation_id == investigation_id,
            FlaggedEvent.event_id == payload.event_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.label = payload.label
        await db.commit()
        await db.refresh(existing)
        return existing
    flag = FlaggedEvent(investigation_id=investigation_id, **payload.model_dump())
    db.add(flag)
    await db.commit()
    await db.refresh(flag)
    return flag

@router.get("/{investigation_id}/flags", response_model=list[FlagOut])
async def list_flags(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FlaggedEvent).where(FlaggedEvent.investigation_id == investigation_id).order_by(FlaggedEvent.flagged_at.asc())
    )
    return result.scalars().all()

@router.delete("/{investigation_id}/flags/{flag_id}", status_code=204)
async def delete_flag(investigation_id: uuid.UUID, flag_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    flag = await db.get(FlaggedEvent, flag_id)
    if not flag or flag.investigation_id != investigation_id:
        raise HTTPException(404, "Flag not found")
    await db.delete(flag)
    await db.commit()

# ── Export ──────────────────────────────────────────────────────────────────

@router.get("/{investigation_id}/export/json")
async def export_json(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    data = await build_export(investigation_id, db)
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="blackbox-{investigation_id}.json"'},
    )

@router.get("/{investigation_id}/export/report")
async def export_report(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    data = await build_export(investigation_id, db)
    report = render_text_report(data)
    return Response(
        content=report,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="blackbox-report-{investigation_id}.txt"'},
    )
