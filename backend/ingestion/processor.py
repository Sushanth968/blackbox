import uuid
import os
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from models.evidence_file import EvidenceFile
from models.event import Event
from event_engine.normalizer import normalize_event

# Make the repo-root `parsers` package importable without shadowing the stdlib.
# Importing the parsers as top-level `json` / `csv` modules (with parsers/ at the
# front of sys.path) shadows the standard library, which breaks both this module
# and the parsers' own `import json` / `import csv`. Putting the repo root on the
# path and importing them namespaced as `parsers.*` avoids the collision.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.append(_REPO_ROOT)

from parsers.json.parser import parse_json
from parsers.json.jsonl_parser import parse_jsonl
from parsers.csv.parser import parse_csv
from parsers.logs.log_parser import parse_log
from parsers.logs.git_parser import parse_git
from parsers.logs.cicd_parser import parse_cicd
from parsers.logs.syslog_parser import parse_syslog

PARSERS = {
    "json": parse_json,
    "jsonl": parse_jsonl,
    "ndjson": parse_jsonl,
    "csv": parse_csv,
    "log": parse_log,
    "txt": parse_log,
    "git": parse_git,
    "cicd": parse_cicd,
    "yml": parse_cicd,
    "syslog": parse_syslog,
}


def _detect_parser(file_path: str, file_type: str):
    if file_type in PARSERS:
        return PARSERS[file_type]
    try:
        with open(file_path, "r", errors="replace") as f:
            first = f.readline().strip()
        if first.startswith("{") or first.startswith("["):
            return parse_json
        if first.startswith("<") and first[1:4].isdigit():
            return parse_syslog
        if first.startswith("commit ") and len(first.split()[1]) == 40:
            return parse_git
    except Exception:
        pass
    return parse_log


async def process_evidence_file(
    evidence_id: uuid.UUID,
    file_path: str,
    file_type: str,
    investigation_id: uuid.UUID,
    db: AsyncSession,
):
    ev_file = await db.get(EvidenceFile, evidence_id)
    if not ev_file:
        return

    parser = _detect_parser(file_path, file_type)
    try:
        ev_file.status = "processing"
        await db.commit()

        raw_events = parser(file_path)
        for raw in raw_events:
            raw = normalize_event(raw)
            event = Event(
                investigation_id=investigation_id,
                evidence_file_id=evidence_id,
                timestamp=raw.get("timestamp"),
                timestamp_confidence=raw.get("timestamp_confidence", 1.0),
                source=raw.get("source"),
                actor=raw.get("actor"),
                action=raw.get("action"),
                object=raw.get("object"),
                severity=raw.get("severity", "info"),
                raw=raw.get("raw"),
                source_line=raw.get("source_line"),
                extra=raw.get("extra"),
            )
            db.add(event)

        ev_file.status = "processed"
        await db.commit()
    except Exception:
        ev_file.status = "failed"
        await db.commit()
        raise


async def reprocess_evidence_file(
    evidence_id: uuid.UUID,
    file_path: str,
    file_type: str,
    investigation_id: uuid.UUID,
    db: AsyncSession,
):
    await db.execute(delete(Event).where(Event.evidence_file_id == evidence_id))
    await db.commit()
    await process_evidence_file(evidence_id, file_path, file_type, investigation_id, db)
