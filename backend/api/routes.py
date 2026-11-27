from typing import Optional
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import get_db
from models.event import Event
from models.entity import Entity
from models.relationship import Relationship
from models.note import Note
from models.flagged_event import FlaggedEvent
from models.evidence_file import EvidenceFile
from models.investigation import Investigation
from schemas.event import EventOut, TimelineOut, ConfidenceOut, EventLabelUpdate
from schemas.entity import EntityOut, GraphOut, RelationshipOut
from schemas.workspace import NoteCreate, NoteOut, FlagCreate, FlagOut
from temporal_engine.temporal import detect_conflicts
from temporal_engine.gaps import detect_gaps
from temporal_engine.confidence import compute_confidence
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

# ── Confidence score ─────────────────────────────────────────────────────────

@router.get("/{investigation_id}/confidence", response_model=ConfidenceOut)
async def get_confidence(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    events_result = await db.execute(
        select(Event)
        .where(Event.investigation_id == investigation_id)
        .order_by(Event.timestamp.asc().nullslast())
    )
    events = events_result.scalars().all()

    files_result = await db.execute(
        select(EvidenceFile).where(EvidenceFile.investigation_id == investigation_id)
    )
    evidence_files = files_result.scalars().all()

    conflicts = detect_conflicts(events)
    gaps = detect_gaps(events)
    result = compute_confidence(events, evidence_files, conflicts, gaps)

    return ConfidenceOut(
        overall=result.overall,
        label=result.label,
        summary=result.summary,
        dimensions=[
            {"name": d.name, "score": d.score, "weight": d.weight, "detail": d.detail, "penalty": d.penalty}
            for d in result.dimensions
        ],
        gaps=result.gaps,
    )

# ── Evidence gaps ─────────────────────────────────────────────────────────────

@router.get("/{investigation_id}/gaps")
async def get_gaps(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Event)
        .where(Event.investigation_id == investigation_id)
        .order_by(Event.timestamp.asc().nullslast())
    )
    events = result.scalars().all()
    gaps = detect_gaps(events)
    return {"gaps": gaps, "total": len(gaps)}

# ── Event label (hypothesis pinning) ─────────────────────────────────────────

@router.patch("/{investigation_id}/events/{event_id}/label", response_model=EventOut)
async def label_event(
    investigation_id: uuid.UUID,
    event_id: uuid.UUID,
    payload: EventLabelUpdate,
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(Event, event_id)
    if not event or event.investigation_id != investigation_id:
        raise HTTPException(404, "Event not found")
    valid = {None, "fact", "inference", "hypothesis"}
    if payload.label_type not in valid:
        raise HTTPException(400, f"label_type must be one of: {valid - {None}}")
    event.label_type = payload.label_type
    await db.commit()
    await db.refresh(event)
    return event

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

# ── Global evidence library ──────────────────────────────────────────────────

global_router = APIRouter()

@global_router.get("/evidence", response_model=list[dict])
async def list_all_evidence(
    db: AsyncSession = Depends(get_db),
    x_user_email: Optional[str] = Header(default=None),
):
    q = (
        select(EvidenceFile, Investigation.title)
        .join(Investigation, EvidenceFile.investigation_id == Investigation.id)
        .order_by(EvidenceFile.uploaded_at.desc())
    )
    if x_user_email:
        q = q.where(Investigation.owner_email == x_user_email)
    result = await db.execute(q)
    rows = result.all()
    return [
        {
            "id": str(ev.id),
            "investigation_id": str(ev.investigation_id),
            "investigation_title": title,
            "original_name": ev.original_name,
            "file_type": ev.file_type,
            "file_size": ev.file_size,
            "sha256": ev.sha256,
            "status": ev.status,
            "uploaded_at": ev.uploaded_at.isoformat() if ev.uploaded_at else None,
        }
        for ev, title in rows
    ]

@global_router.get("/workspaces", response_model=list[dict])
async def list_all_workspaces(
    db: AsyncSession = Depends(get_db),
    x_user_email: Optional[str] = Header(default=None),
):
    q = select(Investigation).order_by(Investigation.created_at.desc())
    if x_user_email:
        q = q.where(Investigation.owner_email == x_user_email)
    result = await db.execute(q)
    investigations = result.scalars().all()

    out = []
    for inv in investigations:
        notes_result = await db.execute(
            select(Note).where(Note.investigation_id == inv.id).order_by(Note.created_at.asc())
        )
        notes = notes_result.scalars().all()

        flags_result = await db.execute(
            select(FlaggedEvent).where(FlaggedEvent.investigation_id == inv.id)
        )
        flags = flags_result.scalars().all()

        evidence_result = await db.execute(
            select(EvidenceFile).where(EvidenceFile.investigation_id == inv.id)
        )
        evidence = evidence_result.scalars().all()

        out.append({
            "id": str(inv.id),
            "title": inv.title,
            "description": inv.description,
            "status": inv.status,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
            "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
            "note_count": len(notes),
            "flag_count": len(flags),
            "evidence_count": len(evidence),
            "notes": [
                {
                    "id": str(n.id),
                    "content": n.content,
                    "author": n.author,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in notes
            ],
        })
    return out
