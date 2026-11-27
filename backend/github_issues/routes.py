import re
from typing import Optional
import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from core.config import settings

router = APIRouter()

GITHUB_API = "https://api.github.com"

_SLUG_PART = re.compile(r"[\w.\-]+")  # simple char class — no backtracking (ReDoS-safe)


class FetchRequest(BaseModel):
    repo_url: str
    github_token: Optional[str] = None


class AnalyzeRequest(BaseModel):
    issue_number: int
    issue_title: str
    issue_body: Optional[str] = None
    repo: str
    anthropic_key: Optional[str] = None


def _parse_repo(repo_url: str) -> str:
    """Extract 'owner/repo' from a GitHub URL, git remote, or plain slug.

    Uses linear string operations only (ReDoS-safe) and performs **no hostname
    substring check** (avoids the incomplete-URL-sanitization pitfall): the host
    segment is dropped structurally, then owner/repo are validated.
    """
    s = (repo_url or "").strip().rstrip("/")
    if s.endswith(".git"):
        s = s[:-4]
    if "://" in s:                       # drop any scheme (https://, git://, ssh://)
        s = s.split("://", 1)[1]
    head = s.split("/", 1)[0]
    if "@" in head and ":" in head:      # scp-style remote: git@host:owner/repo
        s = s.split(":", 1)[1]
    parts = [p for p in s.split("/") if p]
    if parts and "." in parts[0]:        # a leading host segment (e.g. github.com) has a dot — drop it
        parts = parts[1:]
    if len(parts) >= 2 and _SLUG_PART.fullmatch(parts[0]) and _SLUG_PART.fullmatch(parts[1]):
        return f"{parts[0]}/{parts[1]}"
    raise ValueError(f"Cannot parse GitHub repo from: {repo_url!r}")


def _map_issue(i: dict) -> dict:
    """Map a GitHub issue (from the search API) to our issue shape."""
    return {
        "number": i["number"],
        "title": i["title"],
        "body": i.get("body") or "",
        "state": i["state"],
        "html_url": i["html_url"],
        "user": i["user"]["login"] if i.get("user") else None,
        "created_at": i["created_at"],
        "labels": [l["name"] for l in i.get("labels", [])],
        "comments": i.get("comments", 0),
    }


@router.post("/fetch")
async def fetch_issues(body: FetchRequest):
    try:
        repo = _parse_repo(body.repo_url)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    token = body.github_token or settings.GITHUB_TOKEN
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Use the Search API with `type:issue` so pull requests are excluded at the
    # source. (The /repos/{repo}/issues endpoint returns issues AND PRs mixed,
    # so on PR-heavy repos the first page can be all PRs -> zero issues shown.)
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{GITHUB_API}/search/issues",
            headers=headers,
            params={
                "q": f"repo:{repo} type:issue state:open",
                "sort": "created",
                "order": "desc",
                "per_page": 30,
            },
        )

    if resp.status_code == 403:
        raise HTTPException(403, "GitHub rate limit exceeded or token missing for private repo.")
    if resp.status_code == 422:
        raise HTTPException(404, f"Repository '{repo}' not found or query invalid.")
    if resp.status_code != 200:
        raise HTTPException(502, f"GitHub API error {resp.status_code}.")

    data = resp.json()
    issues = [_map_issue(i) for i in data.get("items", [])]
    return {"repo": repo, "issues": issues, "total_count": data.get("total_count", len(issues))}


@router.post("/analyze")
async def analyze_issue(body: AnalyzeRequest):
    api_key = body.anthropic_key or settings.ANTHROPIC_API_KEY
    if not api_key:
        raise HTTPException(
            422,
            "No Anthropic API key provided. Set ANTHROPIC_API_KEY in .env or pass it in the request.",
        )

    base_url = settings.ANTHROPIC_BASE_URL.rstrip("/")
    model = settings.ANTHROPIC_MODEL

    issue_body_text = (body.issue_body or "").strip() or "(no description)"
    prompt = f"""You are an expert software engineer reviewing a GitHub issue.

Repository: {body.repo}
Issue #{body.issue_number}: {body.issue_title}

Description:
{issue_body_text}

Provide a concise, actionable solution:
1. Root cause analysis (2-3 sentences)
2. Step-by-step fix
3. Any caveats or follow-up items

Be direct and technical."""

    payload = {
        "model": model,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                f"{base_url}/v1/messages",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
            )
        except httpx.RequestError as exc:
            raise HTTPException(502, f"Could not reach LLM endpoint: {exc}")

    if resp.status_code == 401:
        raise HTTPException(401, "Invalid API key.")
    if resp.status_code == 429:
        raise HTTPException(429, "Rate limit exceeded.")
    if resp.status_code != 200:
        raise HTTPException(502, f"LLM API error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    solution = data["content"][0]["text"]
    return {"solution": solution}


@router.get("/search")
async def search_repos(
    q: str = Query(..., min_length=1),
    github_token: Optional[str] = Query(None),
):
    if not q.strip():
        return {"repos": []}

    token = github_token or settings.GITHUB_TOKEN
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{GITHUB_API}/search/repositories",
            headers=headers,
            params={"q": q, "sort": "stars", "order": "desc", "per_page": 10},
        )

    if resp.status_code == 403:
        raise HTTPException(403, "GitHub rate limit exceeded.")
    if resp.status_code != 200:
        raise HTTPException(502, f"GitHub API error {resp.status_code}.")

    items = resp.json().get("items", [])
    repos = [
        {
            "full_name": r["full_name"],
            "description": r.get("description") or "",
            "html_url": r["html_url"],
            "stars": r["stargazers_count"],
            "language": r.get("language") or "",
            "open_issues": r["open_issues_count"],
        }
        for r in items
    ]
    return {"repos": repos}
