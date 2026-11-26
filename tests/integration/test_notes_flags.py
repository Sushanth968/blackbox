"""Integration tests for notes and flags CRUD endpoints."""
import pytest


@pytest.mark.anyio
async def test_create_note(client, make_investigation):
    inv = await make_investigation()
    r = await client.post(
        f"/api/investigations/{inv['id']}/notes",
        json={"content": "This is my note", "author": "alice"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["content"] == "This is my note"
    assert data["author"] == "alice"
    assert data["investigation_id"] == inv["id"]


@pytest.mark.anyio
async def test_create_note_without_author(client, make_investigation):
    inv = await make_investigation()
    r = await client.post(
        f"/api/investigations/{inv['id']}/notes",
        json={"content": "Anonymous note"},
    )
    assert r.status_code == 201
    assert r.json()["author"] is None


@pytest.mark.anyio
async def test_list_notes_empty(client, make_investigation):
    inv = await make_investigation()
    r = await client.get(f"/api/investigations/{inv['id']}/notes")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.anyio
async def test_list_notes_returns_all(client, make_investigation):
    inv = await make_investigation()
    await client.post(f"/api/investigations/{inv['id']}/notes", json={"content": "Note 1"})
    await client.post(f"/api/investigations/{inv['id']}/notes", json={"content": "Note 2"})
    r = await client.get(f"/api/investigations/{inv['id']}/notes")
    assert len(r.json()) == 2


@pytest.mark.anyio
async def test_update_note(client, make_investigation):
    inv = await make_investigation()
    note = (await client.post(
        f"/api/investigations/{inv['id']}/notes", json={"content": "Original"}
    )).json()
    r = await client.patch(
        f"/api/investigations/{inv['id']}/notes/{note['id']}",
        json={"content": "Updated"},
    )
    assert r.status_code == 200
    assert r.json()["content"] == "Updated"


@pytest.mark.anyio
async def test_delete_note(client, make_investigation):
    inv = await make_investigation()
    note = (await client.post(
        f"/api/investigations/{inv['id']}/notes", json={"content": "To delete"}
    )).json()
    r = await client.delete(f"/api/investigations/{inv['id']}/notes/{note['id']}")
    assert r.status_code == 204
    assert (await client.get(f"/api/investigations/{inv['id']}/notes")).json() == []


@pytest.mark.anyio
async def test_delete_note_not_found(client, make_investigation):
    inv = await make_investigation()
    r = await client.delete(
        f"/api/investigations/{inv['id']}/notes/00000000-0000-0000-0000-000000000099"
    )
    assert r.status_code == 404


# ── Flags ─────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_flag_event(client, make_investigation, upload_log):
    inv = await make_investigation()
    await upload_log(inv["id"])
    events = (await client.get(f"/api/investigations/{inv['id']}/events")).json()
    event_id = events[0]["id"]

    r = await client.post(
        f"/api/investigations/{inv['id']}/flags",
        json={"event_id": event_id, "label": "suspicious"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["event_id"] == event_id
    assert data["label"] == "suspicious"


@pytest.mark.anyio
async def test_list_flags_empty(client, make_investigation):
    inv = await make_investigation()
    r = await client.get(f"/api/investigations/{inv['id']}/flags")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.anyio
async def test_flag_same_event_twice_updates_label(client, make_investigation, upload_log):
    inv = await make_investigation()
    await upload_log(inv["id"])
    events = (await client.get(f"/api/investigations/{inv['id']}/events")).json()
    event_id = events[0]["id"]

    await client.post(
        f"/api/investigations/{inv['id']}/flags",
        json={"event_id": event_id, "label": "first"},
    )
    await client.post(
        f"/api/investigations/{inv['id']}/flags",
        json={"event_id": event_id, "label": "second"},
    )
    flags = (await client.get(f"/api/investigations/{inv['id']}/flags")).json()
    assert len(flags) == 1
    assert flags[0]["label"] == "second"


@pytest.mark.anyio
async def test_delete_flag(client, make_investigation, upload_log):
    inv = await make_investigation()
    await upload_log(inv["id"])
    events = (await client.get(f"/api/investigations/{inv['id']}/events")).json()
    event_id = events[0]["id"]

    flag = (await client.post(
        f"/api/investigations/{inv['id']}/flags",
        json={"event_id": event_id},
    )).json()

    r = await client.delete(f"/api/investigations/{inv['id']}/flags/{flag['id']}")
    assert r.status_code == 204
    assert (await client.get(f"/api/investigations/{inv['id']}/flags")).json() == []
