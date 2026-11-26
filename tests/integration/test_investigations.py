"""Integration tests for investigation CRUD endpoints."""
import pytest


@pytest.mark.anyio
async def test_health_endpoint(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.anyio
async def test_create_investigation(client):
    r = await client.post("/api/investigations/", json={"title": "Prod outage", "description": "Nov 20"})
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Prod outage"
    assert data["description"] == "Nov 20"
    assert data["status"] == "open"
    assert "id" in data


@pytest.mark.anyio
async def test_create_investigation_without_description(client):
    r = await client.post("/api/investigations/", json={"title": "Minimal"})
    assert r.status_code == 201
    assert r.json()["description"] is None


@pytest.mark.anyio
async def test_list_investigations_empty(client):
    r = await client.get("/api/investigations/")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.anyio
async def test_list_investigations_returns_all(client, make_investigation):
    await make_investigation("First")
    await make_investigation("Second")
    r = await client.get("/api/investigations/")
    assert r.status_code == 200
    titles = [i["title"] for i in r.json()]
    assert "First" in titles
    assert "Second" in titles


@pytest.mark.anyio
async def test_get_investigation(client, make_investigation):
    inv = await make_investigation("Get me")
    r = await client.get(f"/api/investigations/{inv['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == inv["id"]


@pytest.mark.anyio
async def test_get_investigation_not_found(client):
    r = await client.get("/api/investigations/00000000-0000-0000-0000-000000000099")
    assert r.status_code == 404


@pytest.mark.anyio
async def test_update_investigation_title(client, make_investigation):
    inv = await make_investigation("Old title")
    r = await client.patch(f"/api/investigations/{inv['id']}", json={"title": "New title"})
    assert r.status_code == 200
    assert r.json()["title"] == "New title"


@pytest.mark.anyio
async def test_update_investigation_status(client, make_investigation):
    inv = await make_investigation()
    r = await client.patch(f"/api/investigations/{inv['id']}", json={"status": "closed"})
    assert r.status_code == 200
    assert r.json()["status"] == "closed"


@pytest.mark.anyio
async def test_delete_investigation(client, make_investigation):
    inv = await make_investigation()
    r = await client.delete(f"/api/investigations/{inv['id']}")
    assert r.status_code == 204
    r2 = await client.get(f"/api/investigations/{inv['id']}")
    assert r2.status_code == 404


@pytest.mark.anyio
async def test_delete_investigation_not_found(client):
    r = await client.delete("/api/investigations/00000000-0000-0000-0000-000000000099")
    assert r.status_code == 404


@pytest.mark.anyio
async def test_list_investigations_ordered_by_created_desc(client, make_investigation):
    await make_investigation("Alpha")
    await make_investigation("Beta")
    r = await client.get("/api/investigations/")
    items = r.json()
    # Route orders by created_at DESC; timestamps may tie in SQLite in-memory
    # so we verify the list is non-ascending rather than a fixed head element.
    timestamps = [i["created_at"] for i in items]
    assert timestamps == sorted(timestamps, reverse=True)
