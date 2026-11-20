from typing import Optional
import re
from datetime import datetime, timezone

GIT_PRETTY_RE = re.compile(r'^([0-9a-f]{7,40})\|([^|]+)\|([^|]+)\|(.+)$')
GIT_COMMIT_RE = re.compile(r'^commit ([0-9a-f]{40})')
GIT_AUTHOR_RE = re.compile(r'^Author:\s+(.+?)\s+<([^>]+)>')
GIT_DATE_RE = re.compile(r'^Date:\s+(.+)')


def parse_git(file_path: str) -> list:
    with open(file_path, "r", errors="replace") as f:
        content = f.read()

    events = _parse_pretty(content, file_path)
    if events:
        return events
    return _parse_verbose(content, file_path)


def _parse_pretty(content: str, source: str) -> list:
    events = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        m = GIT_PRETTY_RE.match(line.strip())
        if not m:
            continue
        commit_hash, author_email, date_str, subject = m.groups()
        ts = _parse_git_date(date_str.strip())
        events.append({
            "timestamp": ts,
            "timestamp_confidence": 1.0 if ts else 0.5,
            "source": source,
            "actor": author_email.strip(),
            "action": "commit",
            "object": subject.strip(),
            "severity": _git_severity(subject),
            "raw": line.strip(),
            "source_line": lineno,
            "extra": {"commit": commit_hash},
        })
    return events


def _parse_verbose(content: str, source: str) -> list:
    events = []
    lines = content.splitlines()
    i = 0
    lineno = 0
    while i < len(lines):
        line = lines[i]
        lineno += 1
        cm = GIT_COMMIT_RE.match(line)
        if not cm:
            i += 1
            continue

        commit_hash = cm.group(1)
        author = None
        ts = None
        subject = ""
        start_line = lineno
        i += 1

        while i < len(lines) and not GIT_COMMIT_RE.match(lines[i]):
            l = lines[i]
            am = GIT_AUTHOR_RE.match(l)
            if am:
                author = am.group(2)
            dm = GIT_DATE_RE.match(l)
            if dm:
                ts = _parse_git_date(dm.group(1).strip())
            stripped = l.strip()
            if stripped and not l.startswith((' ', '\t', 'Author:', 'Date:', 'Merge:', 'commit')):
                subject = stripped
            elif l.startswith(('    ', '\t')) and not subject:
                subject = stripped
            i += 1

        events.append({
            "timestamp": ts,
            "timestamp_confidence": 1.0 if ts else 0.5,
            "source": source,
            "actor": author,
            "action": "commit",
            "object": subject,
            "severity": _git_severity(subject),
            "raw": f"commit {commit_hash} {subject}",
            "source_line": start_line,
            "extra": {"commit": commit_hash},
        })

    return events


def _parse_git_date(s: str) -> Optional[datetime]:
    formats = [
        "%Y-%m-%d %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a %b %d %H:%M:%S %Y %z",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _git_severity(subject: str) -> str:
    low = subject.lower()
    if any(w in low for w in ("fix", "bug", "hotfix", "patch", "revert")):
        return "warning"
    if any(w in low for w in ("security", "cve", "vuln", "critical")):
        return "critical"
    return "info"
