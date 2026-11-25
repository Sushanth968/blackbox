import uuid
import os
import importlib.util
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from models.evidence_file import EvidenceFile
from models.event import Event
from models.flagged_event import FlaggedEvent
from event_engine.normalizer import normalize_event
from event_engine.secret_scanner import scrub_event

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_PARSERS_DIR = os.path.join(_REPO_ROOT, "parsers")

# Load parsers directly by file path to avoid stdlib name collisions (json, csv)
def _load(rel: str):
    path = os.path.join(_PARSERS_DIR, rel)
    spec = importlib.util.spec_from_file_location(rel.replace(os.sep, ".").rstrip(".py"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_json_mod      = _load(os.path.join("json", "parser.py"))
_jsonl_mod     = _load(os.path.join("json", "jsonl_parser.py"))
_csv_mod       = _load(os.path.join("csv", "parser.py"))
_log_mod       = _load(os.path.join("logs", "log_parser.py"))
_git_mod       = _load(os.path.join("logs", "git_parser.py"))
_cicd_mod      = _load(os.path.join("logs", "cicd_parser.py"))
_syslog_mod    = _load(os.path.join("logs", "syslog_parser.py"))

parse_json    = _json_mod.parse_json
parse_jsonl   = _jsonl_mod.parse_jsonl
parse_csv     = _csv_mod.parse_csv
parse_log     = _log_mod.parse_log
parse_git     = _git_mod.parse_git
parse_cicd    = _cicd_mod.parse_cicd
parse_syslog  = _syslog_mod.parse_syslog

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
        flagged: list[tuple[Event, list[str]]] = []
        for raw in raw_events:
            raw = normalize_event(raw)
            detectors = scrub_event(raw)
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
            if detectors:
                flagged.append((event, detectors))

        # Auto-flag events in which secrets were detected. Flush first so the
        # newly added events have primary keys to reference.
        if flagged:
            await db.flush()
            for event, detectors in flagged:
                db.add(
                    FlaggedEvent(
                        investigation_id=investigation_id,
                        event_id=event.id,
                        label="secret: " + ", ".join(detectors),
                    )
                )

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
    # Remove flags attached to this file's events before the events themselves,
    # so auto-generated secret flags don't accumulate or dangle across reruns.
    event_ids = select(Event.id).where(Event.evidence_file_id == evidence_id)
    await db.execute(delete(FlaggedEvent).where(FlaggedEvent.event_id.in_(event_ids)))
    await db.execute(delete(Event).where(Event.evidence_file_id == evidence_id))
    await db.commit()
    await process_evidence_file(evidence_id, file_path, file_type, investigation_id, db)
