import json
from datetime import datetime

def parse_jsonl(file_path: str) -> list:
    events = []
    with open(file_path, "r", errors="replace") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
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
                continue

            ts = None
            for ts_key in ("timestamp", "time", "date", "@timestamp", "created_at", "ts"):
                if ts_key in item:
                    try:
                        ts = datetime.fromisoformat(str(item[ts_key]).replace("Z", "+00:00"))
                    except Exception:
                        pass
                    break

            severity = str(item.get("severity") or item.get("level") or item.get("lvl") or "info").lower()
            severity_map = {
                "critical": "critical", "fatal": "critical",
                "error": "error", "err": "error",
                "warn": "warning", "warning": "warning",
                "info": "info", "information": "info",
                "debug": "debug", "trace": "debug",
            }
            severity = severity_map.get(severity, "info")

            events.append({
                "timestamp": ts,
                "timestamp_confidence": 1.0 if ts else 0.0,
                "source": file_path,
                "actor": item.get("user") or item.get("actor") or item.get("author") or item.get("username"),
                "action": item.get("action") or item.get("event") or item.get("type") or item.get("msg"),
                "object": item.get("object") or item.get("resource") or item.get("target") or item.get("path"),
                "severity": severity,
                "raw": line,
                "source_line": lineno,
                "extra": {k: v for k, v in item.items()},
            })
    return events
