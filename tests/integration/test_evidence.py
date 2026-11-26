"""Integration tests for evidence upload, ingestion, and deletion."""
import hashlib
import pytest

JSONL_CONTENT = (
    '{"timestamp":"2026-11-20T10:00:00Z","user":"alice","action":"deploy","object":"svc-api"}\n'
    '{"timestamp":"2026-11-20T10:01:00Z","user":"bob","action":"rollback","object":"svc-api"}\n'
)

LOG_CONTENT = (
    "2026-11-20T10:00:00Z INFO user alice deployed svc-api\n"
    "2026-11-20T10:01:00Z ERROR Rollback triggered\n"
)


@pytest.mark.anyio
async def test_upload_jsonl_evidence(client, make_investigation, upload_log):
    inv = await make_investigation()
    ev = await upload_log(inv["id"], JSONL_CONTENT)
    assert ev["original_name"] == "events.jsonl"
    assert ev["status"] == "processed"
    assert ev["sha256"] is not None
    assert ev["file_size"] > 0


@pytest.mark.anyio
async def test_upload_produces_events(client, make_investigation, upload_log):
    inv = await make_investigation()
    await upload_log(inv["id"], JSONL_CONTENT)
    r = await client.get(f"/api/investigations/{inv['id']}/events")
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.anyio
async def test_upload_log_file(client, make_investigation):
    inv = await make_investigation()
    r = await client.post(
        f"/api/investigations/{inv['id']}/evidence",
        files={"file": ("app.log", LOG_CONTENT.encode(), "text/plain")},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "processed"


@pytest.mark.anyio
async def test_upload_to_nonexistent_investigation(client):
    r = await client.post(
        "/api/investigations/00000000-0000-0000-0000-000000000099/evidence",
        files={"file": ("a.log", b"data", "text/plain")},
    )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_upload_unsupported_extension_rejected(client, make_investigation):
    inv = await make_investigation()
    r = await client.post(
        f"/api/investigations/{inv['id']}/evidence",
        files={"file": ("malware.exe", b"\x00\x01\x02", "application/octet-stream")},
    )
    assert r.status_code == 415


@pytest.mark.anyio
async def test_list_evidence_empty(client, make_investigation):
    inv = await make_investigation()
    r = await client.get(f"/api/investigations/{inv['id']}/evidence")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.anyio
async def test_list_evidence_after_upload(client, make_investigation, upload_log):
    inv = await make_investigation()
    await upload_log(inv["id"])
    r = await client.get(f"/api/investigations/{inv['id']}/evidence")
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.anyio
async def test_delete_evidence_removes_events(client, make_investigation, upload_log):
    inv = await make_investigation()
    ev = await upload_log(inv["id"], JSONL_CONTENT)
    r = await client.get(f"/api/investigations/{inv['id']}/events")
    assert len(r.json()) == 2

    r = await client.delete(f"/api/investigations/{inv['id']}/evidence/{ev['id']}")
    assert r.status_code == 204
    r = await client.get(f"/api/investigations/{inv['id']}/events")
    assert r.json() == []


@pytest.mark.anyio
async def test_delete_evidence_not_found(client, make_investigation):
    inv = await make_investigation()
    r = await client.delete(
        f"/api/investigations/{inv['id']}/evidence/00000000-0000-0000-0000-000000000099"
    )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_evidence_sha256_is_stable(client, make_investigation):
    inv = await make_investigation()
    content = b"stable content for sha256 test"
    r = await client.post(
        f"/api/investigations/{inv['id']}/evidence",
        files={"file": ("stable.log", content, "text/plain")},
    )
    assert r.status_code == 201
    expected = hashlib.sha256(content).hexdigest()
    assert r.json()["sha256"] == expected


@pytest.mark.anyio
async def test_secret_in_evidence_is_flagged(client, make_investigation, upload_log):
    inv = await make_investigation()
    content = '{"timestamp":"2026-11-20T10:00:00Z","user":"ci","action":"push","object":"AKIAIOSFODNN7EXAMPLE leaked"}\n'
    await upload_log(inv["id"], content)
    r = await client.get(f"/api/investigations/{inv['id']}/flags")
    assert r.status_code == 200
    flags = r.json()
    assert any("secret" in (f.get("label") or "") for f in flags)
