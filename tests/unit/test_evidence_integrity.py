"""Tests for evidence integrity verification (SHA-256 tamper detection).

SHA-256 is recorded at upload; this lets an investigator later prove the stored
evidence file has not been altered since — the integrity half of BlackBox's
evidence-first provenance.
"""
from pathlib import Path

from evidence.integrity import sha256_file, verify_evidence

# sha256 of b"hello", computed independently
HELLO_SHA256 = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_sha256_file_matches_known_digest(tmp_path: Path):
    f = tmp_path / "evidence.log"
    f.write_bytes(b"hello")
    assert sha256_file(str(f)) == HELLO_SHA256


def test_verify_reports_verified_when_unchanged(tmp_path: Path):
    f = tmp_path / "evidence.log"
    f.write_bytes(b"hello")
    result = verify_evidence(str(f), HELLO_SHA256)
    assert result["status"] == "verified"
    assert result["actual"] == HELLO_SHA256
    assert result["expected"] == HELLO_SHA256


def test_verify_reports_modified_when_tampered(tmp_path: Path):
    f = tmp_path / "evidence.log"
    f.write_bytes(b"hello")
    expected = sha256_file(str(f))
    f.write_bytes(b"hello!")  # tamper after ingestion
    result = verify_evidence(str(f), expected)
    assert result["status"] == "modified"
    assert result["actual"] != expected
    assert result["expected"] == expected


def test_verify_reports_missing_when_file_gone(tmp_path: Path):
    result = verify_evidence(str(tmp_path / "gone.log"), HELLO_SHA256)
    assert result["status"] == "missing"
    assert result["actual"] is None
