import uuid, hashlib, os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import get_db
from models.evidence_file import EvidenceFile
from models.investigation import Investigation
from schemas.evidence import EvidenceFileOut
from core.config import settings
from ingestion.processor import process_evidence_file, reprocess_evidence_file
from relationship_engine.resolver import resolve_entities
from correlation_engine.correlator import correlate_events

router = APIRouter()

@router.post("/{investigation_id}/evidence", response_model=EvidenceFileOut, status_code=201)
async def upload_evidence(
    investigation_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(404, "Investigation not found")

    inv_dir = os.path.join(settings.UPLOAD_DIR, str(investigation_id))
    os.makedirs(inv_dir, exist_ok=True)

    stored_name = f"{uuid.uuid4()}_{file.filename}"
    dest = os.path.join(inv_dir, stored_name)

    sha256 = hashlib.sha256()
    size = 0
    with open(dest, "wb") as f:
        while chunk := await file.read(65536):
            f.write(chunk)
            sha256.update(chunk)
            size += len(chunk)

    ext = os.path.splitext(file.filename or "")[1].lower().lstrip(".")
    ev = EvidenceFile(
        investigation_id=investigation_id,
        filename=stored_name,
        original_name=file.filename or stored_name,
        file_type=ext or "unknown",
        file_size=size,
        sha256=sha256.hexdigest(),
        status="uploaded",
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)

    await process_evidence_file(ev.id, dest, ext, investigation_id, db)
    await db.refresh(ev)
    await resolve_entities(investigation_id, db)
    await correlate_events(investigation_id, db)
    return ev

@router.get("/{investigation_id}/evidence", response_model=list[EvidenceFileOut])
async def list_evidence(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EvidenceFile).where(EvidenceFile.investigation_id == investigation_id)
    )
    return result.scalars().all()

@router.delete("/{investigation_id}/evidence/{evidence_id}", status_code=204)
async def delete_evidence(investigation_id: uuid.UUID, evidence_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    ev = await db.get(EvidenceFile, evidence_id)
    if not ev or ev.investigation_id != investigation_id:
        raise HTTPException(404, "Evidence file not found")
    await db.delete(ev)
    await db.commit()

@router.post("/{investigation_id}/evidence/{evidence_id}/reprocess", response_model=EvidenceFileOut)
async def reprocess_evidence(investigation_id: uuid.UUID, evidence_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    ev = await db.get(EvidenceFile, evidence_id)
    if not ev or ev.investigation_id != investigation_id:
        raise HTTPException(404, "Evidence file not found")
    file_path = os.path.join(settings.UPLOAD_DIR, str(investigation_id), ev.filename)
    if not os.path.exists(file_path):
        raise HTTPException(422, "Uploaded file no longer exists on disk")
    await reprocess_evidence_file(evidence_id, file_path, ev.file_type or "log", investigation_id, db)
    await db.refresh(ev)
    await resolve_entities(investigation_id, db)
    await correlate_events(investigation_id, db)
    return ev
