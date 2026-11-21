import re
from datetime import datetime, timezone

TIMESTAMP_PATTERNS = [
    (re.compile(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)'), "%Y-%m-%dT%H:%M:%S"),
    (re.compile(r'([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})'), "%b %d %H:%M:%S"),
    (re.compile(r'(\d{2}/[A-Z][a-z]{2}/\d{4}:\d{2}:\d{2}:\d{2})'), "%d/%b/%Y:%H:%M:%S"),
    (re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'), "%Y-%m-%d %H:%M:%S"),
]

SEVERITY_PATTERN = re.compile(r'\b(CRITICAL|ERROR|WARN(?:ING)?|INFO|DEBUG|TRACE|FATAL)\b', re.IGNORECASE)

def parse_log(file_path: str) -> list:
    events = []
    with open(file_path, "r", errors="replace") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.rstrip()
            if not line:
                continue

            ts = None
            for pattern, fmt in TIMESTAMP_PATTERNS:
                m = pattern.search(line)
                if m:
                    raw_ts = m.group(1)
                    try:
                        ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                    except Exception:
                        try:
                            ts = datetime.strptime(raw_ts, fmt)
                            ts = ts.replace(tzinfo=timezone.utc)
                        except Exception:
                            pass
                    break

            severity = "info"
            sm = SEVERITY_PATTERN.search(line)
            if sm:
                sev = sm.group(1).upper()
                if sev in ("CRITICAL", "FATAL"):
                    severity = "critical"
                elif sev == "ERROR":
                    severity = "error"
                elif sev in ("WARN", "WARNING"):
                    severity = "warning"
                elif sev == "DEBUG":
                    severity = "debug"

            events.append({
                "timestamp": ts,
                "timestamp_confidence": 1.0 if ts else 0.3,
                "source": file_path,
                "actor": None,
                "action": None,
                "object": None,
                "severity": severity,
                "raw": line,
                "source_line": lineno,
                "extra": None,
            })
    return events
