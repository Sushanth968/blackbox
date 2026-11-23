"""Tests for the secret/credential scanner (backend/event_engine/secret_scanner.py).

The scanner detects leaked secrets in ingested evidence, redacts them before
they are persisted, and records a non-sensitive summary so the ingestion
pipeline can flag the event. These tests lock detection, redaction and the
in-place event scrub behaviour.
"""
from event_engine.secret_scanner import redact_text, scan_text, scrub_event


def _detectors(text):
    return {f["detector"] for f in scan_text(text)}


def test_detects_aws_access_key_id():
    assert "aws_access_key_id" in _detectors("key AKIAIOSFODNN7EXAMPLE used")


def test_detects_github_token():
    assert "github_token" in _detectors("token=ghp_abcdefghijklmnopqrstuvwxyz0123456789")


def test_detects_jwt():
    jwt = "eyJhbGciOiJIUzI1Ni9.eyJzdWIiOiIxMjM0NTY3ODk0.SflKxwRJSMeKKF2QT4"
    assert "jwt" in _detectors(f"Authorization: Bearer {jwt}")


def test_detects_private_key_header():
    assert "private_key" in _detectors("-----BEGIN RSA PRIVATE KEY-----")


def test_detects_password_in_url_and_redacts_only_password():
    url = "postgres://admin:S3cretP4ss@db.internal:5432/app"
    findings = scan_text(url)
    assert any(f["detector"] == "basic_auth_url" for f in findings)
    redacted = redact_text(url)
    assert "S3cretP4ss" not in redacted
    # Host and username context are preserved for the investigator.
    assert "admin" in redacted and "db.internal" in redacted


def test_detects_generic_secret_assignment():
    assert "generic_secret" in _detectors('api_key = "a1b2c3d4e5f6g7h8"')


def test_ignores_obvious_placeholders():
    assert scan_text("password=******") == []
    assert scan_text("token: null") == []
    assert scan_text("secret = changeme") == []


def test_clean_text_has_no_findings():
    assert scan_text("user alice deployed build 42 successfully") == []


def test_redaction_tags_include_detector_and_stable_fingerprint():
    text = "aws key AKIAIOSFODNN7EXAMPLE"
    once = redact_text(text)
    assert "AKIAIOSFODNN7EXAMPLE" not in once
    assert "[REDACTED:aws_access_key_id:" in once
    # The fingerprint is deterministic: the same secret yields the same tag,
    # so recurring secrets can be correlated without ever being revealed.
    assert redact_text(text) == once


def test_same_secret_shares_fingerprint_across_occurrences():
    [a] = scan_text("AKIAIOSFODNN7EXAMPLE")
    [b] = scan_text("second line AKIAIOSFODNN7EXAMPLE again")
    assert a["fingerprint"] == b["fingerprint"]


def test_overlapping_matches_are_deduped_to_highest_confidence():
    # An AWS key inside an access_key= assignment must be reported once, as the
    # specific high-confidence detector, not also as generic_secret.
    findings = scan_text("access_key=AKIAIOSFODNN7EXAMPLE")
    assert len(findings) == 1
    assert findings[0]["detector"] == "aws_access_key_id"
    assert findings[0]["confidence"] == "high"


def test_scrub_event_redacts_raw_and_records_summary():
    event = {
        "raw": "login by user=bob with password=Hunter2Hunter",
        "extra": {"msg": "password=Hunter2Hunter"},
    }
    detectors = scrub_event(event)
    assert "generic_secret" in detectors
    assert "Hunter2Hunter" not in event["raw"]
    assert "Hunter2Hunter" not in event["extra"]["msg"]
    secrets = event["extra"]["secrets"]
    assert secrets and secrets[0]["detector"] == "generic_secret"
    # The summary stores a fingerprint, never the secret itself.
    assert all("Hunter2Hunter" not in str(s.values()) for s in secrets)


def test_scrub_event_returns_empty_for_clean_event():
    event = {"raw": "service started on port 8080", "extra": {"port": "8080"}}
    assert scrub_event(event) == []
    assert "secrets" not in (event.get("extra") or {})
