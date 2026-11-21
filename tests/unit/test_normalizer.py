"""Tests for the event normalizer (backend/event_engine/normalizer.py).

The normalizer extracts actor / action / object / IPs / HTTP status from a raw
log line into the common event structure. These tests document and lock that
behavior; cases marked xfail record known imprecisions to fix in a follow-up.
"""
import pytest

from event_engine.normalizer import normalize_event


def test_extracts_actor_from_user_field():
    event = normalize_event({"raw": "user=alice opened a session"})
    assert event["actor"] == "alice"


def test_extracts_http_method_as_action():
    event = normalize_event({"raw": '"GET /api/orders HTTP/1.1"'})
    assert event["action"] == "get"


def test_extracts_request_path_as_object():
    event = normalize_event({"raw": '"GET /api/orders HTTP/1.1" 200'})
    assert event["object"] == "/api/orders"


def test_flags_error_severity_on_5xx_status():
    event = normalize_event({"raw": "deployment failed with status 500"})
    assert event["extra"]["http_status"] == 500
    assert event["severity"] == "error"


def test_collects_ip_addresses_into_extra():
    event = normalize_event({"raw": "connection from 10.0.0.1 to 10.0.0.2"})
    assert event["extra"]["ips"] == ["10.0.0.1", "10.0.0.2"]


def test_returns_event_unchanged_when_no_raw():
    event = normalize_event({"actor": "bob"})
    assert event == {"actor": "bob"}


@pytest.mark.xfail(
    strict=True,
    reason="Known bug: HTTP_STATUS_PATTERN matches an IP octet (e.g. 127) before the "
    "real status code. Fix tracked as a follow-up PR.",
)
def test_ip_octet_not_misread_as_http_status():
    """An IP like 127.0.0.1 should not have '127' picked up as an HTTP status."""
    event = normalize_event({"raw": '127.0.0.1 "GET /api/orders HTTP/1.1" 200'})
    assert event.get("extra", {}).get("http_status") == 200
