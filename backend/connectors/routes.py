"""Endpoints to link a GitHub repo to an investigation and manually sync it.

Sync fetches recent repo activity, writes it as a hashed JSON evidence file, and
runs it through the existing ingestion pipeline — so synced data gets the same
normalization, secret-scanning, provenance and timeline treatment as any upload.
No scheduler: sync is triggered manually ("Sync now").
"""
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.session import get_db
from models.investigation import Investigation
from models.linked_repo import LinkedRepo
from models.evidence_file import EvidenceFile
from ingestion.processor import process_evidence_file
from relationship_engine.resolver import resolve_entities
from connectors.github import parse_repo, fetch_repo_activity, commits_to_events, issues_to_events

router = APIRouter()


class LinkBody(BaseModel):
    repo_url: str


async def _get_link(investigation_id: uuid.UUID, db: AsyncSession) -> LinkedRepo | None:
    res = await db.execute(select(LinkedRepo).where(LinkedRepo.investigation_id == investigation_id))
    return res.scalars().first()


@router.post("/{investigation_id}/github/link")
async def link_repo(investigation_id: uuid.UUID, body: LinkBody, db: AsyncSession = Depends(get_db)):
    if not await db.get(Investigation, investigation_id):
        raise HTTPException(404, "Investigation not found")
    try:
        repo = parse_repo(body.repo_url)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    link = await _get_link(investigation_id, db)
    if link:
        link.repo_full_name = repo
        link.html_url = f"https://github.com/{repo}"
    else:
        link = LinkedRepo(investigation_id=investigation_id, repo_full_name=repo,
                          html_url=f"https://github.com/{repo}")
        db.add(link)
    await db.commit()
    await db.refresh(link)
    return {"linked": True, "repo_full_name": link.repo_full_name,
            "html_url": link.html_url, "last_synced_at": link.last_synced_at}


@router.get("/{investigation_id}/github")
async def get_linked_repo(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    link = await _get_link(investigation_id, db)
    if not link:
        return {"linked": False}
    return {"linked": True, "repo_full_name": link.repo_full_name,
            "html_url": link.html_url, "last_synced_at": link.last_synced_at}


@router.post("/{investigation_id}/github/sync")
async def sync_repo(investigation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    link = await _get_link(investigation_id, db)
    if not link:
        raise HTTPException(400, "No repo linked to this investigation")

    token = settings.GITHUB_TOKEN or None
    data = await fetch_repo_activity(link.repo_full_name, token)
    events = (commits_to_events(data["commits"], link.repo_full_name)
              + issues_to_events(data["issues"], link.repo_full_name))
    if not events:
        raise HTTPException(502, f"GitHub returned no activity for {link.repo_full_name} "
                                 f"(check the repo name / GITHUB_TOKEN; statuses: {data.get('errors')})")

    # Persist the fetched activity as a hashed JSON evidence file, then ingest it
    # through the normal pipeline (keeps evidence-first integrity).
    payload = json.dumps(events, indent=2).encode()
    base_upload_dir = os.path.realpath(settings.UPLOAD_DIR)
    inv_dir = os.path.realpath(os.path.join(base_upload_dir, str(investigation_id)))
    if os.path.commonpath([base_upload_dir, inv_dir]) != base_upload_dir:
        raise HTTPException(400, "Invalid investigation path")
    os.makedirs(inv_dir, exist_ok=True)
    stored = f"{uuid.uuid4()}_github-sync.json"
    dest = os.path.join(inv_dir, stored)
    with open(dest, "wb") as fh:
        fh.write(payload)

    ev = EvidenceFile(
        investigation_id=investigation_id,
        filename=stored,
        original_name=f"github-sync-{link.repo_full_name.replace('/', '-')}.json",
        file_type="json",
        file_size=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        status="uploaded",
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)

    await process_evidence_file(ev.id, dest, "json", investigation_id, db)
    try:
        await resolve_entities(investigation_id, db)
    except Exception:
        pass  # entity resolution is best-effort; ingestion already succeeded

    link.last_synced_at = datetime.now(timezone.utc)
    await db.commit()
    return {"synced": True, "events_ingested": len(events),
            "evidence_id": str(ev.id), "last_synced_at": link.last_synced_at}
