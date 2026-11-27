"""GitHub repository connector.

Pure mappers turn GitHub API payloads into BlackBox's common event shape
(``{timestamp, user, action, object, message}``) — the same shape the JSON
parser already understands — so synced repo activity flows through the normal
ingestion pipeline. The network fetch is isolated in ``fetch_repo_activity``.
"""
import re
from typing import Optional

import httpx

GITHUB_API = "https://api.github.com"


def parse_repo(repo_url: str) -> str:
    """Extract ``owner/repo`` from a URL, git remote, or bare ``owner/repo``."""
    s = (repo_url or "").strip()
    m = re.search(r"github\.com[/:]([^/\s]+/[^/\s]+?)(?:\.git)?/?$", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"[^/\s]+/[^/\s]+", s):
        return s
    raise ValueError(f"Could not parse a GitHub owner/repo from: {repo_url!r}")


def commits_to_events(commits: list, repo: str) -> list[dict]:
    events = []
    for c in commits or []:
        commit = c.get("commit") or {}
        author = commit.get("author") or {}
        login = (c.get("author") or {}).get("login") or author.get("name")
        msg = commit.get("message") or ""
        first_line = msg.splitlines()[0] if msg else ""
        sha = (c.get("sha") or "")[:7]
        events.append({
            "timestamp": author.get("date"),
            "user": login,
            "action": "commit",
            "object": repo,
            "message": f"{sha} {first_line}".strip(),
        })
    return events


def issues_to_events(issues: list, repo: str) -> list[dict]:
    events = []
    for it in issues or []:
        kind = "pull_request" if "pull_request" in it else "issue"
        state = it.get("state", "open")
        events.append({
            "timestamp": it.get("created_at"),
            "user": (it.get("user") or {}).get("login"),
            "action": f"{kind}_{state}",
            "object": f"{repo}#{it.get('number')}",
            "message": it.get("title", ""),
        })
    return events


async def fetch_repo_activity(repo: str, token: Optional[str], per_page: int = 30) -> dict:
    """Fetch recent commits and issues/PRs for ``repo``. Network-only; mapping is
    done by the pure functions above so it stays testable."""
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=20) as client:
        commits = await client.get(f"{GITHUB_API}/repos/{repo}/commits",
                                   headers=headers, params={"per_page": per_page})
        issues = await client.get(f"{GITHUB_API}/repos/{repo}/issues",
                                  headers=headers, params={"per_page": per_page, "state": "all"})
    cj = commits.json() if commits.status_code == 200 else []
    ij = issues.json() if issues.status_code == 200 else []
    return {
        "commits": cj if isinstance(cj, list) else [],
        "issues": ij if isinstance(ij, list) else [],
        "errors": [r.status_code for r in (commits, issues) if r.status_code != 200],
    }
