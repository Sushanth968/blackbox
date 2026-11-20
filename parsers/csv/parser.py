import csv
from datetime import datetime

def parse_csv(file_path: str) -> list:
    events = []
    with open(file_path, "r", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            ts = None
            for ts_key in ("timestamp", "time", "date", "datetime"):
                if ts_key in row and row[ts_key]:
                    try:
                        ts = datetime.fromisoformat(row[ts_key].replace("Z", "+00:00"))
                    except Exception:
                        pass
                    break

            events.append({
                "timestamp": ts,
                "timestamp_confidence": 1.0 if ts else 0.0,
                "source": file_path,
                "actor": row.get("user") or row.get("actor") or row.get("author"),
                "action": row.get("action") or row.get("event") or row.get("type"),
                "object": row.get("object") or row.get("resource") or row.get("target"),
                "severity": row.get("severity") or row.get("level") or "info",
                "raw": str(dict(row)),
                "source_line": i + 2,
                "extra": dict(row),
            })
    return events
