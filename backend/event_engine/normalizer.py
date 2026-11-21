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
HTTP_STATUS_PATTERN = re.compile(r'\b([1-5]\d{2})\b')


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
    status_m = HTTP_STATUS_PATTERN.search(raw)
    if status_m:
        code = int(status_m.group(1))
        if 100 <= code <= 599:
            extra["http_status"] = code
            if not event.get("severity") or event["severity"] == "info":
                if code >= 500:
                    event["severity"] = "error"
                elif code >= 400:
                    event["severity"] = "warning"
    if extra:
        event["extra"] = extra

    return event
