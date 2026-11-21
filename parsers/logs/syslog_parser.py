from typing import Optional
import re
from datetime import datetime, timezone

RFC5424_RE = re.compile(
    r'^<(\d+)>(\d+)\s+'
    r'(\S+)\s+'
    r'(\S+)\s+'
    r'(\S+)\s+'
    r'(\S+)\s+'
    r'(\S+)\s+'
    r'(\[.*?\]|-)\s*'
    r'(.*)$'
)

RFC3164_RE = re.compile(
    r'^<(\d+)>'
    r'([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
    r'(\S+)\s+'
    r'(\S+?)(?:\[(\d+)\])?:\s*'
    r'(.*)$'
)

FACILITY_NAMES = {
    0: "kern", 1: "user", 2: "mail", 3: "daemon", 4: "auth",
    5: "syslog", 6: "lpr", 7: "news", 8: "uucp", 9: "cron",
    16: "local0", 17: "local1", 18: "local2", 19: "local3",
    20: "local4", 21: "local5", 22: "local6", 23: "local7",
}

SEVERITY_FROM_PRI = ["critical", "critical", "critical", "error", "warning", "warning", "info", "debug"]


def parse_syslog(file_path: str) -> list:
    events = []
    with open(file_path, "r", errors="replace") as f:
        for lineno, raw_line in enumerate(f, start=1):
            line = raw_line.rstrip()
            if not line:
                continue

            m = RFC5424_RE.match(line)
            if m:
                priority, version, ts_str, hostname, app, procid, msgid, sd, message = m.groups()
                ts = _parse_ts(ts_str)
                pri = int(priority)
                severity = SEVERITY_FROM_PRI[pri % 8]
                events.append({
                    "timestamp": ts,
                    "timestamp_confidence": 1.0 if ts else 0.5,
                    "source": file_path,
                    "actor": hostname if hostname != "-" else None,
                    "action": app if app != "-" else None,
                    "object": message.strip() or None,
                    "severity": severity,
                    "raw": line,
                    "source_line": lineno,
                    "extra": {
                        "hostname": hostname,
                        "app": app,
                        "procid": procid,
                        "facility": FACILITY_NAMES.get(pri >> 3, str(pri >> 3)),
                        "structured_data": sd if sd != "-" else None,
                    },
                })
                continue

            m2 = RFC3164_RE.match(line)
            if m2:
                priority, ts_str, hostname, app, pid, message = m2.groups()
                ts = _parse_ts_3164(ts_str)
                pri = int(priority)
                severity = SEVERITY_FROM_PRI[pri % 8]
                events.append({
                    "timestamp": ts,
                    "timestamp_confidence": 0.8 if ts else 0.3,
                    "source": file_path,
                    "actor": hostname,
                    "action": app,
                    "object": message.strip() or None,
                    "severity": severity,
                    "raw": line,
                    "source_line": lineno,
                    "extra": {"hostname": hostname, "app": app, "pid": pid},
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
    if s == "-":
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _parse_ts_3164(s: str) -> Optional[datetime]:
    from datetime import date
    try:
        dt = datetime.strptime(s.strip(), "%b %d %H:%M:%S")
        return dt.replace(year=date.today().year, tzinfo=timezone.utc)
    except Exception:
        return None
