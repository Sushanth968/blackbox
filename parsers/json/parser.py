import json
from datetime import datetime

def parse_json(file_path: str) -> list:
    with open(file_path, "r", errors="replace") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = [data]

    events = []
    for i, item in enumerate(data):
        ts = None
        for ts_key in ("timestamp", "time", "date", "@timestamp", "created_at"):
            if ts_key in item:
                try:
                    ts = datetime.fromisoformat(str(item[ts_key]).replace("Z", "+00:00"))
                except Exception:
                    pass
                break

        events.append({
            "timestamp": ts,
            "timestamp_confidence": 1.0 if ts else 0.0,
            "source": file_path,
            "actor": item.get("user") or item.get("actor") or item.get("author"),
            "action": item.get("action") or item.get("event") or item.get("type"),
            "object": item.get("object") or item.get("resource") or item.get("target"),
            "severity": item.get("severity") or item.get("level") or "info",
            "raw": json.dumps(item),
            "source_line": i + 1,
            "extra": {k: v for k, v in item.items() if k not in ("timestamp", "time", "user", "actor", "action", "event")},
        })
    return events
