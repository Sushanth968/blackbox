"""Deterministic secret / credential scanner for ingested evidence.

Evidence that BlackBox ingests — application logs, CI/CD output, git history,
JSON/CSV exports — is a common place for secrets to leak (cloud keys, access
tokens, private keys, passwords in connection strings). This module detects
those secrets in normalized events so they can be:

  * flagged as security findings (via the existing FlaggedEvent model), and
  * redacted before they are persisted, displayed in the UI, or written into an
    exported report — so BlackBox never re-leaks a secret it discovered.

Design constraints (see CONTRIBUTING.md):
  * Deterministic and dependency-free (stdlib ``re`` / ``hashlib`` only); no AI.
  * Small, pure, testable functions.

Provenance note: only the *derived* event fields (``raw``, ``object``, ``extra``)
are redacted. The uploaded source file on disk is never modified, so its
SHA-256 integrity hash still verifies against the untouched original.

Each detected secret is replaced with ``[REDACTED:<detector>:<fingerprint>]``.
The fingerprint is the first 8 hex chars of ``sha256(secret)`` — it never
reveals the secret, but it is stable, so an investigator can still tell that the
*same* secret recurs across several events (a useful correlation signal)
without ever seeing its value.
"""
from __future__ import annotations

import hashlib
import re
from typing import TypedDict


class Finding(TypedDict):
    detector: str
    confidence: str  # "high" | "medium"
    match: str
    start: int
    end: int
    fingerprint: str


# ── Detectors ─────────────────────────────────────────────────────────────────
# Each entry: (name, confidence, compiled regex, group holding the secret value).
# Group 0 means the whole match is the indicator (no inner value to isolate).
# All patterns use bounded quantifiers and no nested repetition, so matching is
# linear in input length (no catastrophic backtracking / ReDoS).
_PATTERNS: list[tuple[str, str, re.Pattern[str], int]] = [
    # AWS access key id (AKIA/ASIA + 16 uppercase alphanumerics).
    ("aws_access_key_id", "high", re.compile(r"\b((?:AKIA|ASIA)[0-9A-Z]{16})\b"), 1),
    # AWS secret access key — only detectable via an explicit assignment.
    (
        "aws_secret_access_key",
        "high",
        re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*[\"']?([A-Za-z0-9/+]{40})"),
        1,
    ),
    # GitHub tokens (classic PATs, OAuth, app, and fine-grained ``github_pat_``).
    (
        "github_token",
        "high",
        re.compile(r"\b((?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,250})\b"),
        1,
    ),
    # Slack tokens (xoxb-/xoxp-/xoxa-/xoxr-/xoxs-).
    ("slack_token", "high", re.compile(r"\b(xox[baprs]-[A-Za-z0-9-]{10,250})\b"), 1),
    # Google API key.
    ("google_api_key", "high", re.compile(r"\b(AIza[0-9A-Za-z_\-]{35})\b"), 1),
    # JSON Web Token (three base64url segments; header starts with ``eyJ``).
    (
        "jwt",
        "high",
        re.compile(r"\b(eyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,})"),
        1,
    ),
    # PEM private-key header line (RSA/EC/OpenSSH/DSA/PGP or generic).
    (
        "private_key",
        "high",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
        0,
    ),
    # Credentials embedded in a URL: scheme://user:PASSWORD@host.
    (
        "basic_auth_url",
        "high",
        re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.\-]*://[^\s:/@]+:([^\s:/@]{3,})@"),
        1,
    ),
    # Generic ``password=`` / ``api_key:`` / ``token=`` assignments. Lower
    # confidence (favours recall); obvious placeholders are filtered out below.
    (
        "generic_secret",
        "medium",
        re.compile(
            r"(?i)\b(?:password|passwd|pwd|secret|api[_\-]?key|access[_\-]?key|token)\b"
            r"\s*[=:]\s*[\"']?([^\s\"']{6,})"
        ),
        1,
    ),
]

# Values that look like a secret assignment but are clearly not a real secret.
_PLACEHOLDER_RE = re.compile(r"^[*x<>.\-_/]+$", re.IGNORECASE)
_PLACEHOLDER_WORDS = {
    "null", "none", "nil", "true", "false",
    "changeme", "example", "redacted", "password", "secret",
}


def _is_placeholder(value: str) -> bool:
    v = value.strip().strip("\"'")
    if len(v) < 6:
        return True
    if v.lower() in _PLACEHOLDER_WORDS:
        return True
    if _PLACEHOLDER_RE.match(v):
        return True
    return False


def _fingerprint(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8", "replace")).hexdigest()[:8]


def _dedupe(findings: list[Finding]) -> list[Finding]:
    """Drop overlapping matches, preferring high confidence then longer spans.

    A single substring can match several detectors (e.g. an AWS key inside a
    ``access_key=`` assignment). Keeping both would double-redact and double-
    count, so we keep one match per span region.
    """
    ranked = sorted(
        findings,
        key=lambda f: (f["start"], 0 if f["confidence"] == "high" else 1, -(f["end"] - f["start"])),
    )
    kept: list[Finding] = []
    covered_until = -1
    for f in ranked:
        if f["start"] >= covered_until:
            kept.append(f)
            covered_until = f["end"]
    return kept


def scan_text(text: str) -> list[Finding]:
    """Return the secrets detected in ``text`` (de-overlapped, left to right)."""
    if not text:
        return []
    found: list[Finding] = []
    for name, confidence, regex, group in _PATTERNS:
        for m in regex.finditer(text):
            start, end = m.span(group)
            if start < 0 or end <= start:
                continue
            secret = text[start:end]
            if name == "generic_secret" and _is_placeholder(secret):
                continue
            found.append(
                Finding(
                    detector=name,
                    confidence=confidence,
                    match=secret,
                    start=start,
                    end=end,
                    fingerprint=_fingerprint(secret),
                )
            )
    return _dedupe(found)


def _apply(text: str, findings: list[Finding]) -> str:
    for f in sorted(findings, key=lambda x: x["start"], reverse=True):
        token = f"[REDACTED:{f['detector']}:{f['fingerprint']}]"
        text = text[: f["start"]] + token + text[f["end"] :]
    return text


def redact_text(text: str) -> str:
    """Return ``text`` with every detected secret replaced by a redaction tag."""
    return _apply(text, scan_text(text))


# Derived string fields that may carry a secret and are safe to redact.
_SCAN_FIELDS = ("raw", "object")


def scrub_event(event: dict) -> list[str]:
    """Detect and redact secrets in a normalized event, in place.

    Scans ``raw`` and ``object`` plus the top-level string values of ``extra``.
    When secrets are found, those fields are redacted and a non-sensitive
    summary (detector + confidence + fingerprint) is stored under
    ``event["extra"]["secrets"]``.

    Returns the sorted list of distinct detector names (empty if the event is
    clean), which the ingestion pipeline uses as the security flag label.
    """
    summary: list[dict] = []
    detectors: set[str] = set()

    for field in _SCAN_FIELDS:
        value = event.get(field)
        if isinstance(value, str) and value:
            findings = scan_text(value)
            if findings:
                event[field] = _apply(value, findings)
                for f in findings:
                    detectors.add(f["detector"])
                    summary.append(
                        {
                            "detector": f["detector"],
                            "confidence": f["confidence"],
                            "fingerprint": f["fingerprint"],
                        }
                    )

    extra = event.get("extra")
    if isinstance(extra, dict):
        for key, value in list(extra.items()):
            if isinstance(value, str) and value:
                findings = scan_text(value)
                if findings:
                    extra[key] = _apply(value, findings)
                    for f in findings:
                        detectors.add(f["detector"])
                        summary.append(
                            {
                                "detector": f["detector"],
                                "confidence": f["confidence"],
                                "fingerprint": f["fingerprint"],
                            }
                        )

    if not detectors:
        return []

    # Deduplicate the summary by (detector, fingerprint) while preserving order.
    seen: set[tuple[str, str]] = set()
    unique_summary = []
    for item in summary:
        key = (item["detector"], item["fingerprint"])
        if key not in seen:
            seen.add(key)
            unique_summary.append(item)

    extra = event.get("extra")
    if not isinstance(extra, dict):
        extra = {}
    extra["secrets"] = unique_summary
    event["extra"] = extra

    return sorted(detectors)
