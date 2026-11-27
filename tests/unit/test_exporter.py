"""Tests for the investigation report exporter (backend/reporting/exporter.py).

``render_text_report`` is a pure function: it takes a plain dict (the same
structure returned by ``build_export``) and returns a formatted string.
All tests here are synchronous and dependency-free.
"""
from reporting.exporter import render_text_report


def _base_data(**overrides) -> dict:
    """Minimal valid export dict — override individual top-level keys as needed."""
    data = {
        "meta": {"exported_at": "2026-11-20T10:00:00+00:00", "blackbox_version": "0.1.0"},
        "investigation": {
            "id": "00000000-0000-0000-0000-000000000001",
            "title": "Production API failure",
            "description": "Post-deploy outage on 2026-11-20",
            "status": "open",
            "created_at": "2026-11-20T08:00:00+00:00",
            "updated_at": "2026-11-20T10:00:00+00:00",
        },
        "summary": {
            "evidence_files": 0, "total_events": 0, "flagged_events": 0,
            "secret_events": 0, "secret_findings": 0, "entities": 0,
            "relationships": 0, "temporal_conflicts": 0, "notes": 0,
        },
        "evidence_files": [],
        "events": [],
        "temporal_conflicts": [],
        "entities": [],
        "relationships": [],
        "notes": [],
        "flagged_events": [],
    }
    data.update(overrides)
    return data


# ── Header / footer ───────────────────────────────────────────────────────────

def test_report_starts_with_header_rule():
    report = render_text_report(_base_data())
    assert report.startswith("=" * 72)


def test_report_ends_with_end_of_report():
    report = render_text_report(_base_data())
    assert "END OF REPORT" in report


def test_report_includes_investigation_title():
    report = render_text_report(_base_data())
    assert "Production API failure" in report


def test_report_includes_status():
    report = render_text_report(_base_data())
    assert "open" in report


def test_report_includes_exported_at_timestamp():
    report = render_text_report(_base_data())
    assert "2026-11-20T10:00:00" in report


# ── Evidence files section ────────────────────────────────────────────────────

def test_evidence_file_name_included():
    data = _base_data(evidence_files=[{
        "id": "f1", "name": "app.log", "type": "log", "size": 2048,
        "sha256": "deadbeef01234567", "status": "processed", "uploaded_at": None,
    }])
    assert "app.log" in render_text_report(data)


def test_evidence_file_sha256_included():
    data = _base_data(evidence_files=[{
        "id": "f1", "name": "app.log", "type": "log", "size": 2048,
        "sha256": "deadbeef01234567", "status": "processed", "uploaded_at": None,
    }])
    assert "deadbeef01234567" in render_text_report(data)


def test_evidence_file_without_sha256_does_not_crash():
    data = _base_data(evidence_files=[{
        "id": "f1", "name": "app.log", "type": "log", "size": 0,
        "sha256": None, "status": "uploaded", "uploaded_at": None,
    }])
    report = render_text_report(data)
    assert "app.log" in report


# ── Temporal conflicts section ───────────────────────────────────────────────

def test_temporal_conflicts_section_shown_when_present():
    data = _base_data(temporal_conflicts=[
        {"type": "clock_skew", "description": "Clock skew between git and CI"}
    ])
    assert "TEMPORAL CONFLICTS" in render_text_report(data)


def test_conflict_description_included():
    data = _base_data(temporal_conflicts=[
        {"type": "out_of_order", "description": "Event B precedes Event A"}
    ])
    assert "Event B precedes Event A" in render_text_report(data)


def test_no_temporal_conflicts_section_when_empty():
    report = render_text_report(_base_data())
    assert "TEMPORAL CONFLICTS" not in report


# ── Security findings section ─────────────────────────────────────────────────

def test_security_findings_section_shown_for_events_with_secrets():
    data = _base_data(events=[{
        "id": "e1",
        "timestamp": "2026-11-20T10:00:00+00:00",
        "source": "ci.log",
        "source_line": 42,
        "actor": "ci-bot",
        "action": "deploy",
        "object": "/svc",
        "severity": "info",
        "flagged": False,
        "raw": "...",
        "extra": {"secrets": [
            {"detector": "aws_access_key_id", "confidence": "high", "fingerprint": "abcdef01"}
        ]},
    }])
    report = render_text_report(data)
    assert "SECURITY FINDINGS" in report
    assert "aws_access_key_id" in report


def test_no_security_section_when_no_secrets():
    report = render_text_report(_base_data())
    assert "SECURITY FINDINGS" not in report


def test_secret_source_location_included():
    data = _base_data(events=[{
        "id": "e1",
        "timestamp": "2026-11-20T10:00:00+00:00",
        "source": "ci.log",
        "source_line": 99,
        "actor": None,
        "action": None,
        "object": None,
        "severity": "info",
        "flagged": False,
        "raw": "...",
        "extra": {"secrets": [
            {"detector": "github_token", "confidence": "high", "fingerprint": "ff001122"}
        ]},
    }])
    report = render_text_report(data)
    assert "ci.log:99" in report


# ── Flagged events section ────────────────────────────────────────────────────

def test_flagged_events_section_shown():
    data = _base_data(
        events=[{
            "id": "e1",
            "timestamp": "2026-11-20T10:00:00+00:00",
            "source": "app.log",
            "source_line": 1,
            "actor": "alice",
            "action": "deploy",
            "object": "/svc",
            "severity": "warning",
            "flagged": True,
            "raw": "...",
            "extra": {},
        }],
        flagged_events=[{"event_id": "e1", "label": "inference", "flagged_at": "2026-11-20T10:00:00+00:00"}],
    )
    report = render_text_report(data)
    assert "FLAGGED EVENTS" in report
    assert "inference" in report


def test_no_flagged_events_section_when_empty():
    report = render_text_report(_base_data())
    assert "FLAGGED EVENTS" not in report


def test_flagged_event_without_label_does_not_crash():
    data = _base_data(
        events=[{
            "id": "e1",
            "timestamp": "2026-11-20T10:00:00+00:00",
            "source": "app.log",
            "source_line": 1,
            "actor": "bob",
            "action": "login",
            "object": "/auth",
            "severity": "info",
            "flagged": True,
            "raw": "...",
            "extra": {},
        }],
        flagged_events=[{"event_id": "e1", "label": None, "flagged_at": None}],
    )
    report = render_text_report(data)
    assert "FLAGGED EVENTS" in report


# ── Notes section ─────────────────────────────────────────────────────────────

def test_notes_section_shown_when_present():
    data = _base_data(notes=[{
        "id": "n1",
        "content": "This deployment caused the incident",
        "author": "alice",
        "event_id": None,
        "created_at": "2026-11-20T09:00:00+00:00",
    }])
    report = render_text_report(data)
    assert "NOTES" in report
    assert "This deployment caused the incident" in report


def test_note_author_included():
    data = _base_data(notes=[{
        "id": "n1",
        "content": "Root cause confirmed",
        "author": "bob",
        "event_id": None,
        "created_at": "2026-11-20T09:00:00+00:00",
    }])
    assert "[bob]" in render_text_report(data)


def test_no_notes_section_when_empty():
    report = render_text_report(_base_data())
    assert "NOTES" not in report


def test_note_without_author_does_not_crash():
    data = _base_data(notes=[{
        "id": "n1",
        "content": "Anonymous note",
        "author": None,
        "event_id": None,
        "created_at": None,
    }])
    report = render_text_report(data)
    assert "Anonymous note" in report


# ── Entities section ──────────────────────────────────────────────────────────

def test_entities_section_shown():
    data = _base_data(entities=[
        {"id": "e1", "name": "alice", "type": "user", "canonical_name": "alice"},
    ])
    assert "ENTITIES" in render_text_report(data)


def test_entities_grouped_by_type():
    data = _base_data(entities=[
        {"id": "e1", "name": "alice", "type": "user", "canonical_name": "alice"},
        {"id": "e2", "name": "10.0.0.1", "type": "ip", "canonical_name": "10.0.0.1"},
    ])
    report = render_text_report(data)
    assert "user: alice" in report
    assert "ip: 10.0.0.1" in report


def test_no_entities_section_when_empty():
    report = render_text_report(_base_data())
    assert "ENTITIES" not in report


# ── Robustness ────────────────────────────────────────────────────────────────

def test_empty_dict_does_not_crash():
    report = render_text_report({})
    assert isinstance(report, str)


def test_none_description_renders_dash():
    data = _base_data()
    data["investigation"]["description"] = None
    report = render_text_report(data)
    assert "—" in report
