"""Integration tests for the GitHub connector sync path.

Regression coverage for the bug where `sync_repo` passed a `Path` object into
`process_evidence_file`, which the JSON parser embedded as each event's
``source`` — SQLite then refused to bind a ``PosixPath`` ("type 'PosixPath'
is not supported"), 500-ing every "Sync now".
"""
from pathlib import Path

import pytest

from models.investigation import Investigation
from models.evidence_file import EvidenceFile
from models.event import Event
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from ingestion.processor import process_evidence_file


# Canned repo activity in the shape connectors.github.fetch_repo_activity returns.
_FAKE_ACTIVITY = {
    "commits": [
        {
            "sha": "abcdef1234567",
            "commit": {"message": "fix checkout bug", "author": {"name": "Alice", "date": "2026-11-20T10:00:00Z"}},
            "author": {"login": "alice"},
        }
    ],
    "issues": [
        {"number": 5, "state": "open", "title": "Bug", "user": {"login": "bob"}, "created_at": "2026-11-20T11:00:00Z"},
    ],
    "errors": {},
}


@pytest.mark.anyio
async def test_sync_now_ingests_activity_as_events(client, make_investigation, monkeypatch):
    """Link a repo, Sync now, and confirm activity lands as events (no PosixPath crash)."""
    async def fake_fetch(repo, token):
        return _FAKE_ACTIVITY
    monkeypatch.setattr("connectors.routes.fetch_repo_activity", fake_fetch)

    inv = await make_investigation()
    inv_id = inv["id"]

    r = await client.post(f"/api/investigations/{inv_id}/github/link",
                          json={"repo_url": "https://github.com/octocat/Hello-World"})
    assert r.status_code == 200
    assert r.json()["repo_full_name"] == "octocat/Hello-World"

    r = await client.post(f"/api/investigations/{inv_id}/github/sync")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["synced"] is True
    assert body["events_ingested"] == 2
    assert body["last_synced_at"] is not None

    # The synced activity is now queryable as timeline events.
    r = await client.get(f"/api/investigations/{inv_id}/events")
    assert r.status_code == 200
    events = r.json()
    assert len(events) == 2


@pytest.mark.anyio
async def test_process_evidence_file_accepts_path_source(test_engine, tmp_path):
    """process_evidence_file must accept a Path file_path and store ``source`` as a str."""
    AsyncSession = async_sessionmaker(test_engine, expire_on_commit=False)
    async with AsyncSession() as db:
        inv = Investigation(title="P")
        db.add(inv)
        await db.flush()
        ev = EvidenceFile(investigation_id=inv.id, filename="x.json", original_name="x.json",
                          file_type="json", file_size=1, sha256="0" * 64, status="uploaded")
        db.add(ev)
        await db.commit()
        await db.refresh(ev)
        await db.refresh(inv)

        json_file = tmp_path / "activity.json"
        json_file.write_text('[{"timestamp":"2026-11-20T10:00:00Z","user":"alice","action":"commit","object":"o/r"}]')

        # Pass a Path (not str) — this is exactly what sync_repo does.
        await process_evidence_file(ev.id, Path(json_file), "json", inv.id, db)

        rows = (await db.execute(select(Event).where(Event.evidence_file_id == ev.id))).scalars().all()
        assert len(rows) == 1
        assert isinstance(rows[0].source, str)
