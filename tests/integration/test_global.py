"""Integration tests for global evidence library and workspaces endpoints."""
import pytest

CONTENT = '{"timestamp":"2026-11-20T10:00:00Z","user":"alice","action":"deploy","object":"svc"}\n'


@pytest.mark.anyio
async def test_global_evidence_empty(client):
    r = await client.get("/api/evidence")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.anyio
async def test_global_evidence_lists_across_investigations(client, make_investigation, upload_log):
    inv1 = await make_investigation("Inv 1")
    inv2 = await make_investigation("Inv 2")
    await upload_log(inv1["id"], CONTENT)
    await upload_log(inv2["id"], CONTENT)

    r = await client.get("/api/evidence")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    inv_ids = {item["investigation_id"] for item in items}
    assert inv1["id"] in inv_ids
    assert inv2["id"] in inv_ids


@pytest.mark.anyio
async def test_global_evidence_includes_investigation_title(client, make_investigation, upload_log):
    inv = await make_investigation("My Investigation")
    await upload_log(inv["id"], CONTENT)

    r = await client.get("/api/evidence")
    items = r.json()
    assert items[0]["investigation_title"] == "My Investigation"


@pytest.mark.anyio
async def test_global_evidence_item_has_required_fields(client, make_investigation, upload_log):
    inv = await make_investigation()
    await upload_log(inv["id"], CONTENT)

    item = (await client.get("/api/evidence")).json()[0]
    for key in ("id", "investigation_id", "investigation_title", "original_name",
                "file_type", "file_size", "sha256", "status", "uploaded_at"):
        assert key in item, f"Missing field: {key}"


@pytest.mark.anyio
async def test_workspaces_empty(client):
    r = await client.get("/api/workspaces")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.anyio
async def test_workspaces_lists_all_investigations(client, make_investigation):
    await make_investigation("Alpha")
    await make_investigation("Beta")
    r = await client.get("/api/workspaces")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    titles = {i["title"] for i in items}
    assert "Alpha" in titles
    assert "Beta" in titles


@pytest.mark.anyio
async def test_workspaces_includes_counts(client, make_investigation, upload_log):
    inv = await make_investigation()
    await upload_log(inv["id"], CONTENT)
    await client.post(
        f"/api/investigations/{inv['id']}/notes",
        json={"content": "A note"},
    )

    items = (await client.get("/api/workspaces")).json()
    ws = next(i for i in items if i["id"] == inv["id"])
    assert ws["evidence_count"] == 1
    assert ws["note_count"] == 1


@pytest.mark.anyio
async def test_workspaces_includes_notes_list(client, make_investigation):
    inv = await make_investigation()
    await client.post(
        f"/api/investigations/{inv['id']}/notes",
        json={"content": "Important note", "author": "alice"},
    )

    items = (await client.get("/api/workspaces")).json()
    ws = next(i for i in items if i["id"] == inv["id"])
    assert len(ws["notes"]) == 1
    assert ws["notes"][0]["content"] == "Important note"


@pytest.mark.anyio
async def test_workspaces_item_has_required_fields(client, make_investigation):
    await make_investigation("Field check")
    ws = (await client.get("/api/workspaces")).json()[0]
    for key in ("id", "title", "description", "status", "created_at",
                "note_count", "flag_count", "evidence_count", "notes"):
        assert key in ws, f"Missing field: {key}"
