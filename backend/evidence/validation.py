"""Validation helpers for evidence uploads.

Pure, dependency-free functions (stdlib only) so they are cheap to unit-test and
reuse. They guard the upload endpoint against the classic file-upload risks:
path traversal / unsafe stored names, and unsupported (e.g. binary) file types.
The size limit itself is enforced while streaming in the route.
"""
import os
import re

MAX_FILENAME_LEN = 200
_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def extract_extension(filename: str) -> str:
    """Return the lower-cased extension without the dot (``""`` if none)."""
    return os.path.splitext(filename or "")[1].lower().lstrip(".")


def is_allowed_extension(filename: str, allowed) -> bool:
    return extract_extension(filename) in {str(a).lower() for a in allowed}


def sanitize_filename(filename: str) -> str:
    """Reduce an untrusted upload name to a safe stored basename.

    Strips directory components (both ``/`` and ``\\``) and null bytes, replaces
    any character outside ``[A-Za-z0-9._-]`` with ``_``, and bounds the length
    while preserving a short extension. Never returns an empty string.
    """
    name = (filename or "").replace("\x00", "")
    # Defeat path traversal regardless of separator style, then keep only the leaf.
    name = name.replace("\\", "/").split("/")[-1]
    name = _UNSAFE_CHARS.sub("_", name).strip("._")
    if not name:
        return "evidence"
    if len(name) > MAX_FILENAME_LEN:
        root, dot, ext = name.rpartition(".")
        if dot and 0 < len(ext) <= 10:
            name = root[: MAX_FILENAME_LEN - len(ext) - 1] + "." + ext
        else:
            name = name[:MAX_FILENAME_LEN]
    return name
