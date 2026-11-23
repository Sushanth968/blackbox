import re

ACTOR_PATTERNS = [
    re.compile(r'\buser[=: ]+["\']?(\w[\w.@-]+)["\']?', re.IGNORECASE),
    re.compile(r'\bby[=: ]+["\']?(\w[\w.@-]+)["\']?', re.IGNORECASE),
    re.compile(r'\bfor[=: ]+["\']?(\w[\w.@-]+)["\']?', re.IGNORECASE),
    re.compile(r'\bactor[=: ]+["\']?(\w[\w.@-]+)["\']?', re.IGNORECASE),
    re.compile(r'\bauthor[=: ]+["\']?(\w[\w.@-]+)["\']?', re.IGNORECASE),
    re.compile(r'\bfor (\w[\w.-]+) from\b', re.IGNORECASE),
    re.compile(r'^(\w[\w.-]+)\s*:\s*TTY=', re.MULTILINE),
]

ACTION_PATTERNS = [
    re.compile(r'\b(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b'),
    re.compile(r'\b(login|logout|signin|signout|authenticate|authorize)\b', re.IGNORECASE),
    re.compile(r'\b(created?|deleted?|updated?|modified?|inserted?|removed?|deployed?|started?|stopped?|failed?|succeeded?|completed?)\b', re.IGNORECASE),
    re.compile(r'\b(connect(?:ed|ing)?|disconnect(?:ed|ing)?|accept(?:ed)?|reject(?:ed)?|block(?:ed)?)\b', re.IGNORECASE),
    re.compile(r'\b(push(?:ed)?|pull(?:ed)?|merge(?:d)?|commit(?:ted)?|deploy(?:ed)?|build|built|test(?:ed)?)\b', re.IGNORECASE),
]

OBJECT_PATTERNS = [
    re.compile(r'"(?:GET|POST|PUT|DELETE|PATCH)\s+(/[^\s"]*)', re.IGNORECASE),
    re.compile(r'\bpath[=: ]+["\']?(/[^\s"\']+)["\']?', re.IGNORECASE),
    re.compile(r'\bfile[=: ]+["\']?([^\s"\']+)["\']?', re.IGNORECASE),
    re.compile(r'\bresource[=: ]+["\']?([^\s"\']+)["\']?', re.IGNORECASE),
]

IP_PATTERN = re.compile(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b')

# HTTP status is matched only where it is unambiguous — in response position
# right after a quoted request (common/combined access-log format), or via an
# explicit ``status=``/``status:`` assignment. This avoids misreading IP octets
# (e.g. 127 in 127.0.0.1) or stray numbers (byte counts, path segments) as a
# status code.
RESPONSE_STATUS_PATTERN = re.compile(r'"[A-Z]{3,7}[^"]*"\s+(\d{3})\b')
EXPLICIT_STATUS_PATTERN = re.compile(r'\bstatus[=:\s]+(\d{3})\b', re.IGNORECASE)


def normalize_event(event: dict) -> dict:
    raw = event.get("raw") or ""
    if not raw:
        return event

    if not event.get("actor"):
        for pat in ACTOR_PATTERNS:
            m = pat.search(raw)
            if m:
                event["actor"] = m.group(1)
                break

    if not event.get("action"):
        for pat in ACTION_PATTERNS:
            m = pat.search(raw)
            if m:
                event["action"] = m.group(1).lower()
                break

    if not event.get("object"):
        for pat in OBJECT_PATTERNS:
            m = pat.search(raw)
            if m:
                event["object"] = m.group(1)
                break

    extra = event.get("extra") or {}
    ips = IP_PATTERN.findall(raw)
    if ips:
        extra["ips"] = list(dict.fromkeys(ips))

    code = _extract_http_status(raw)
    if code is not None:
        extra["http_status"] = code
        if not event.get("severity") or event["severity"] == "info":
            if code >= 500:
                event["severity"] = "error"
            elif code >= 400:
                event["severity"] = "warning"

    if extra:
        event["extra"] = extra

    return event


def _extract_http_status(raw: str):
    """Return an HTTP status code found in response position or an explicit
    ``status=`` form, else None. Deliberately conservative to avoid false
    positives from IP octets or unrelated 3-digit numbers."""
    m = RESPONSE_STATUS_PATTERN.search(raw)
    if not m:
        m = EXPLICIT_STATUS_PATTERN.search(raw)
    if not m:
        return None
    code = int(m.group(1))
    return code if 100 <= code <= 599 else None
