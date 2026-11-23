"""Tests for evidence upload validation (backend/evidence/validation.py).

Lock the hardening behaviour: unsafe upload names are reduced to a safe stored
basename (no path traversal, no null bytes, bounded length) and only parseable
text extensions are accepted.
"""
from evidence.validation import extract_extension, is_allowed_extension, sanitize_filename

ALLOWED = ["json", "csv", "log", "txt", ""]


def test_extract_extension():
    assert extract_extension("evidence.JSON") == "json"
    assert extract_extension("archive.tar.gz") == "gz"
    assert extract_extension("noext") == ""
    assert extract_extension("") == ""


def test_is_allowed_extension():
    assert is_allowed_extension("a.json", ALLOWED)
    assert is_allowed_extension("server.log", ALLOWED)
    assert is_allowed_extension("noext", ALLOWED)       # "" is allowed
    assert not is_allowed_extension("malware.exe", ALLOWED)
    assert not is_allowed_extension("image.png", ALLOWED)


def test_sanitize_strips_path_traversal():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("/abs/path/to/app.log") == "app.log"
    assert sanitize_filename("..\\..\\windows\\system32\\cfg.ini") == "cfg.ini"


def test_sanitize_removes_null_bytes_and_unsafe_chars():
    assert "\x00" not in sanitize_filename("evil\x00.log")
    out = sanitize_filename("we ird name!$.csv")
    assert out == "we_ird_name__.csv"
    assert "/" not in out and " " not in out


def test_sanitize_never_empty():
    assert sanitize_filename("") == "evidence"
    assert sanitize_filename("...") == "evidence"
    assert sanitize_filename("///") == "evidence"


def test_sanitize_bounds_length_and_keeps_extension():
    long_name = "a" * 500 + ".log"
    out = sanitize_filename(long_name)
    assert len(out) <= 200
    assert out.endswith(".log")


def test_sanitize_keeps_reasonable_name():
    assert sanitize_filename("ci-run_42.jsonl") == "ci-run_42.jsonl"
