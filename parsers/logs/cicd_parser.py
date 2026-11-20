from typing import Optional
import re
from datetime import datetime

GHA_LINE_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)\s+(##\[(\w+)\])?(.*)$'
)
GHA_SECTION_RE = re.compile(r'^##\[(\w+)\](.*)$')
GENERIC_CI_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+'
    r'(?:\[(\w+)\]\s+)?(.+)$'
)

SEVERITY_MAP = {
    "error": "error",
    "warning": "warning",
    "notice": "info",
    "group": "info",
    "endgroup": "info",
    "debug": "debug",
    "command": "info",
    "section": "info",
}


def parse_cicd(file_path: str) -> list:
    events = []
    with open(file_path, "r", errors="replace") as f:
        lines = f.readlines()

    current_section = None
    for lineno, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        if not line:
            continue

        m = GHA_LINE_RE.match(line)
        if m:
            ts_str, _, gha_level, message = m.groups()
            ts = _parse_ts(ts_str)
            message = message.strip()

            sm = GHA_SECTION_RE.match(message)
            if sm:
                gha_level = sm.group(1)
                message = sm.group(2).strip()
                if gha_level == "group":
                    current_section = message
                elif gha_level == "endgroup":
                    current_section = None

            severity = SEVERITY_MAP.get((gha_level or "").lower(), "info")
            if not message:
                continue

            events.append({
                "timestamp": ts,
                "timestamp_confidence": 1.0,
                "source": file_path,
                "actor": None,
                "action": gha_level or "log",
                "object": current_section,
                "severity": severity,
                "raw": line,
                "source_line": lineno,
                "extra": {"section": current_section, "message": message},
            })
            continue

        m2 = GENERIC_CI_RE.match(line)
        if m2:
            ts_str, level, message = m2.groups()
            ts = _parse_ts(ts_str)
            severity = SEVERITY_MAP.get((level or "").lower(), "info")
            events.append({
                "timestamp": ts,
                "timestamp_confidence": 1.0 if ts else 0.3,
                "source": file_path,
                "actor": None,
                "action": level or "log",
                "object": None,
                "severity": severity,
                "raw": line,
                "source_line": lineno,
                "extra": {"message": message},
            })
            continue

        events.append({
            "timestamp": None,
            "timestamp_confidence": 0.0,
            "source": file_path,
            "actor": None,
            "action": None,
            "object": None,
            "severity": "info",
            "raw": line,
            "source_line": lineno,
            "extra": None,
        })

    return events


def _parse_ts(s: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None
