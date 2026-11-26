"""Integration tests for timeline, confidence, gaps, graph, and event-label endpoints."""
import pytest

MULTI_EVENT = (
    '{"timestamp":"2026-11-20T08:00:00Z","user":"alice","action":"build","object":"svc-api"}\n'
    '{"timestamp":"2026-11-20T09:00:00Z","user":"alice","action":"deploy","object":"svc-api"}\n'
    '{"timestamp":"2026-11-20T10:00:00Z","user":"bob","action":"rollback","object":"svc-api"}\n'
)


@pytest.mark.anyio
async def test_timeline_empty_investigation(client, make_investigation):
    inv = await make_investigation()
    r = await client.get(f"/api/investigations/{inv['id']}/timeline")
    assert r.status_code == 200
    data = r.json()
    assert data["events"] == []
    assert data["conflicts"] == []
    assert data["total"] == 0


@pytest.mark.anyio
async def test_timeline_returns_events_after_upload(client, make_investigation, upload_log):
    inv = await make_investigation()
    await upload_log(inv["id"], MULTI_EVENT)
    r = await client.get(f"/api/investigations/{inv['id']}/timeline")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert len(data["events"]) == 3


@pytest.mark.anyio
async def test_timeline_events_ordered_by_timestamp(client, make_investigation, upload_log):
    inv = await make_investigation()
    await upload_log(inv["id"], MULTI_EVENT)
    r = await client.get(f"/api/investigations/{inv['id']}/timeline")
    timestamps = [e["timestamp"] for e in r.json()["events"] if e["timestamp"]]
    assert timestamps == sorted(timestamps)


@pytest.mark.anyio
async def test_confidence_empty_investigation(client, make_investigation):
    inv = await make_investigation()
    r = await client.get(f"/api/investigations/{inv['id']}/confidence")
    assert r.status_code == 200
    data = r.json()
    assert "overall" in data
    assert "label" in data
    assert len(data["dimensions"]) == 5


@pytest.mark.anyio
async def test_confidence_improves_after_upload(client, make_investigation, upload_log):
    inv = await make_investigation()
    r_before = await client.get(f"/api/investigations/{inv['id']}/confidence")
    await upload_log(inv["id"], MULTI_EVENT)
    r_after = await client.get(f"/api/investigations/{inv['id']}/confidence")

    before_integrity = next(
        d for d in r_before.json()["dimensions"] if d["name"] == "Evidence integrity"
    )
    after_integrity = next(
        d for d in r_after.json()["dimensions"] if d["name"] == "Evidence integrity"
    )
    assert after_integrity["score"] >= before_integrity["score"]


@pytest.mark.anyio
async def test_gaps_empty_investigation(client, make_investigation):
    inv = await make_investigation()
    r = await client.get(f"/api/investigations/{inv['id']}/gaps")
    assert r.status_code == 200
    assert r.json()["gaps"] == []
    assert r.json()["total"] == 0


@pytest.mark.anyio
async def test_gaps_detected_for_large_window(client, make_investigation, upload_log):
    inv = await make_investigation()
    content = (
        '{"timestamp":"2026-11-20T00:00:00Z","user":"alice","action":"start","object":"svc"}\n'
        '{"timestamp":"2026-11-20T10:00:00Z","user":"alice","action":"end","object":"svc"}\n'
    )
    await upload_log(inv["id"], content)
    r = await client.get(f"/api/investigations/{inv['id']}/gaps")
    assert r.json()["total"] >= 1


@pytest.mark.anyio
async def test_graph_empty(client, make_investigation):
    inv = await make_investigation()
    r = await client.get(f"/api/investigations/{inv['id']}/graph")
    assert r.status_code == 200
    data = r.json()
    assert data["nodes"] == []
    assert data["edges"] == []


@pytest.mark.anyio
async def test_graph_has_nodes_after_resolve(client, make_investigation, upload_log):
    inv = await make_investigation()
    await upload_log(inv["id"], MULTI_EVENT)
    r = await client.post(f"/api/investigations/{inv['id']}/entities/resolve")
    assert r.status_code == 200
    r = await client.get(f"/api/investigations/{inv['id']}/graph")
    assert len(r.json()["nodes"]) > 0


@pytest.mark.anyio
async def test_event_label_patch(client, make_investigation, upload_log):
    inv = await make_investigation()
    await upload_log(inv["id"], MULTI_EVENT)
    events = (await client.get(f"/api/investigations/{inv['id']}/events")).json()
    event_id = events[0]["id"]

    r = await client.patch(
        f"/api/investigations/{inv['id']}/events/{event_id}/label",
        json={"label_type": "fact"},
    )
    assert r.status_code == 200
    assert r.json()["label_type"] == "fact"


@pytest.mark.anyio
async def test_event_label_invalid_value_rejected(client, make_investigation, upload_log):
    inv = await make_investigation()
    await upload_log(inv["id"])
    events = (await client.get(f"/api/investigations/{inv['id']}/events")).json()
    event_id = events[0]["id"]

    r = await client.patch(
        f"/api/investigations/{inv['id']}/events/{event_id}/label",
        json={"label_type": "bogus"},
    )
    assert r.status_code == 400


@pytest.mark.anyio
async def test_event_label_can_be_cleared(client, make_investigation, upload_log):
    inv = await make_investigation()
    await upload_log(inv["id"])
    events = (await client.get(f"/api/investigations/{inv['id']}/events")).json()
    event_id = events[0]["id"]

    await client.patch(
        f"/api/investigations/{inv['id']}/events/{event_id}/label",
        json={"label_type": "hypothesis"},
    )
    r = await client.patch(
        f"/api/investigations/{inv['id']}/events/{event_id}/label",
        json={"label_type": None},
    )
    assert r.status_code == 200
    assert r.json()["label_type"] is None
