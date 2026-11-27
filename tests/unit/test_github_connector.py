"""Tests for the GitHub connector's pure mappers (no network)."""
from connectors.github import parse_repo, commits_to_events, issues_to_events


def test_parse_repo_from_url_remote_and_bare():
    assert parse_repo("https://github.com/Sushanth968/blackbox") == "Sushanth968/blackbox"
    assert parse_repo("https://github.com/Sushanth968/blackbox.git") == "Sushanth968/blackbox"
    assert parse_repo("git@github.com:owner/repo.git") == "owner/repo"
    assert parse_repo("owner/repo") == "owner/repo"


def test_parse_repo_rejects_garbage():
    import pytest
    with pytest.raises(ValueError):
        parse_repo("not a repo")


def test_commits_map_to_events():
    commits = [{
        "sha": "abcdef1234567",
        "commit": {"message": "fix checkout bug\n\nmore detail",
                   "author": {"name": "Alice", "date": "2026-11-20T10:00:00Z"}},
        "author": {"login": "alice"},
    }]
    evs = commits_to_events(commits, "o/r")
    assert evs[0]["action"] == "commit"
    assert evs[0]["user"] == "alice"
    assert evs[0]["timestamp"] == "2026-11-20T10:00:00Z"
    assert evs[0]["object"] == "o/r"
    assert "abcdef1" in evs[0]["message"] and "fix checkout bug" in evs[0]["message"]


def test_issues_map_to_events_and_distinguish_prs():
    issues = [
        {"number": 5, "state": "open", "title": "Bug", "user": {"login": "bob"},
         "created_at": "2026-11-20T11:00:00Z"},
        {"number": 6, "state": "closed", "title": "Add feature", "user": {"login": "carol"},
         "created_at": "2026-11-20T12:00:00Z", "pull_request": {"url": "x"}},
    ]
    evs = issues_to_events(issues, "o/r")
    assert evs[0]["action"] == "issue_open"
    assert evs[0]["object"] == "o/r#5"
    assert evs[1]["action"] == "pull_request_closed"
