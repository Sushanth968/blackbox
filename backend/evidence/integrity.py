"""Evidence integrity — SHA-256 hashing and tamper detection.

Every evidence file is hashed at upload. These helpers recompute that hash on
demand so an investigator can prove a stored file has not been altered since it
was ingested — the integrity foundation of BlackBox's evidence-first provenance.

Pure and deterministic (stdlib only); the uploaded file is read, never modified.
"""
import hashlib
import os
from typing import Optional, TypedDict

_CHUNK = 65536  # 64 KiB — stream large evidence files


class IntegrityResult(TypedDict):
    status: str  # "verified" | "modified" | "missing"
    expected: str
    actual: Optional[str]


def sha256_file(path: str) -> str:
    """Return the hex SHA-256 digest of the file at ``path`` (streamed)."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_evidence(path: str, expected_sha256: str) -> IntegrityResult:
    """Recompute the file's SHA-256 and compare to the recorded hash.

    Returns a result whose ``status`` is:
      * ``"missing"``  — the stored file no longer exists,
      * ``"verified"`` — the recomputed hash matches ``expected_sha256``,
      * ``"modified"`` — the file exists but its hash differs (tampering/corruption).
    """
    if not os.path.isfile(path):
        return {"status": "missing", "expected": expected_sha256, "actual": None}
    actual = sha256_file(path)
    status = "verified" if actual == expected_sha256 else "modified"
    return {"status": status, "expected": expected_sha256, "actual": actual}
