"""Integration tests for JSON and text-report export endpoints."""
import json
import pytest

CONTENT = (
    '{"timestamp":"2026-11-20T10:00:00Z","user":"alice","action":"deploy","object":"svc-api"}\n'
    '{"timestamp":"2026-11-20T10:01:00Z","user":"bob","action":"rollback","object":"svc-api"}\n'
)


@pytest.mark.anyio
async def test_export_json_empty_investigation(client, make_investigation):
    inv = await make_investigation("Export test")
    r = await client.get(f"/api/investigations/{inv['id']}/export/json")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/json"
    data = json.loads(r.content)
    assert data["investigation"]["title"] == "Export test"
    assert data["summary"]["total_events"] == 0


@pytest.mark.anyio
async def test_export_json_includes_events(client, make_investigation, upload_log):
    inv = await make_investigation()
    await upload_log(inv["id"], CONTENT)
    r = await client.get(f"/api/investigations/{inv['id']}/export/json")
    data = json.loads(r.content)
    assert data["summary"]["total_events"] == 2
    assert len(data["events"]) == 2


@pytest.mark.anyio
async def test_export_json_includes_evidence_files(client, make_investigation, upload_log):
    inv = await make_investigation()
    await upload_log(inv["id"], CONTENT)
    r = await client.get(f"/api/investigations/{inv['id']}/export/json")
    data = json.loads(r.content)
    assert data["summary"]["evidence_files"] == 1
    assert len(data["evidence_files"]) == 1
    assert data["evidence_files"][0]["sha256"] is not None


@pytest.mark.anyio
async def test_export_json_has_meta_block(client, make_investigation):
    inv = await make_investigation()
    r = await client.get(f"/api/investigations/{inv['id']}/export/json")
    data = json.loads(r.content)
    assert "exported_at" in data["meta"]
    assert data["meta"]["blackbox_version"] == "0.1.0"


@pytest.mark.anyio
async def test_export_json_content_disposition_header(client, make_investigation):
    inv = await make_investigation()
    r = await client.get(f"/api/investigations/{inv['id']}/export/json")
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert inv["id"] in cd


@pytest.mark.anyio
async def test_export_report_empty_investigation(client, make_investigation):
    inv = await make_investigation("Report test")
    r = await client.get(f"/api/investigations/{inv['id']}/export/report")
    assert r.status_code == 200
    text = r.text
    assert "BLACKBOX INVESTIGATION REPORT" in text
    assert "Report test" in text
    assert "END OF REPORT" in text


@pytest.mark.anyio
async def test_export_report_includes_events_summary(client, make_investigation, upload_log):
    inv = await make_investigation()
    await upload_log(inv["id"], CONTENT)
    r = await client.get(f"/api/investigations/{inv['id']}/export/report")
    assert "Total events" in r.text
    assert "2" in r.text


@pytest.mark.anyio
async def test_export_report_includes_evidence_sha256(client, make_investigation, upload_log):
    inv = await make_investigation()
    ev = await upload_log(inv["id"], CONTENT)
    r = await client.get(f"/api/investigations/{inv['id']}/export/report")
    assert ev["sha256"] in r.text


@pytest.mark.anyio
async def test_export_report_includes_notes(client, make_investigation):
    inv = await make_investigation()
    await client.post(
        f"/api/investigations/{inv['id']}/notes",
        json={"content": "Root cause identified", "author": "alice"},
    )
    r = await client.get(f"/api/investigations/{inv['id']}/export/report")
    assert "Root cause identified" in r.text


@pytest.mark.anyio
async def test_export_report_content_disposition(client, make_investigation):
    inv = await make_investigation()
    r = await client.get(f"/api/investigations/{inv['id']}/export/report")
    assert "attachment" in r.headers.get("content-disposition", "")
