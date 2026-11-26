"""Shared async fixtures for integration tests.

Each test function gets a fresh in-memory SQLite database and an HTTPX
AsyncClient wired directly to the ASGI app — no network required.

Helper coroutines are exposed as pytest fixtures (not direct imports) because
``--import-mode=importlib`` does not place conftest.py on sys.path.
"""
import os
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from main import app
from db.base import Base
from db.session import get_db
from core.config import settings


@pytest.fixture
async def test_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def client(test_engine, tmp_path):
    upload_dir = str(tmp_path / "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    original_upload_dir = settings.UPLOAD_DIR
    settings.UPLOAD_DIR = upload_dir

    AsyncSession = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with AsyncSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    settings.UPLOAD_DIR = original_upload_dir


# ── Helper fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def make_investigation(client):
    """Return a coroutine that creates an investigation and returns its JSON."""
    async def _create(title="Test investigation", description=None):
        r = await client.post(
            "/api/investigations/",
            json={"title": title, "description": description},
        )
        assert r.status_code == 201
        return r.json()
    return _create


@pytest.fixture
def upload_log(client):
    """Return a coroutine that uploads a JSONL file to an investigation."""
    async def _upload(
        inv_id,
        content='{"timestamp":"2026-11-20T10:00:00Z","user":"alice","action":"deploy","object":"svc"}\n',
    ):
        r = await client.post(
            f"/api/investigations/{inv_id}/evidence",
            files={"file": ("events.jsonl", content.encode(), "text/plain")},
        )
        assert r.status_code == 201
        return r.json()
    return _upload
