import re
from typing import Optional
import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from core.config import settings

router = APIRouter()

GITHUB_API = "https://api.github.com"


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
    """Extract 'owner/repo' from a GitHub URL or plain slug."""
    repo_url = repo_url.strip().rstrip("/")
    match = re.search(r"github\.com[/:]([^/]+/[^/]+?)(?:\.git)?$", repo_url)
    if match:
        return match.group(1)
    if re.match(r"^[\w.\-]+/[\w.\-]+$", repo_url):
        return repo_url
    raise ValueError(f"Cannot parse GitHub repo from: {repo_url!r}")


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

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{GITHUB_API}/repos/{repo}/issues",
            headers=headers,
            params={"state": "open", "per_page": 30},
        )

    if resp.status_code == 404:
        raise HTTPException(404, f"Repository '{repo}' not found or not accessible.")
    if resp.status_code == 403:
        raise HTTPException(403, "GitHub rate limit exceeded or token missing for private repo.")
    if resp.status_code != 200:
        raise HTTPException(502, f"GitHub API error {resp.status_code}.")

    raw = resp.json()
    issues = [
        {
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
        for i in raw
        if not i.get("pull_request")
    ]

    return {"repo": repo, "issues": issues}


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
