"""Tests for the GitHub-issues helpers (pure, no network)."""
import pytest

from github_issues.routes import _parse_repo, _map_issue


def test_parse_repo_url_remote_slug_and_trailing_path():
    assert _parse_repo("https://github.com/n8n-io/n8n") == "n8n-io/n8n"
    assert _parse_repo("https://github.com/owner/repo/issues") == "owner/repo"
    assert _parse_repo("git@github.com:owner/repo.git") == "owner/repo"
    assert _parse_repo("owner/repo") == "owner/repo"


def test_parse_repo_rejects_non_repo_input():
    with pytest.raises(ValueError):
        _parse_repo("hello world")


def test_map_issue_produces_expected_shape():
    item = {
        "number": 5, "title": "Bug", "body": "desc", "state": "open",
        "html_url": "https://github.com/o/r/issues/5",
        "user": {"login": "alice"}, "created_at": "2026-11-20T10:00:00Z",
        "labels": [{"name": "bug"}, {"name": "p1"}], "comments": 3,
    }
    m = _map_issue(item)
    assert m["number"] == 5
    assert m["user"] == "alice"
    assert m["labels"] == ["bug", "p1"]
    assert m["comments"] == 3


def test_map_issue_tolerates_missing_optional_fields():
    item = {"number": 7, "title": "x", "state": "open",
            "html_url": "u", "created_at": "t"}
    m = _map_issue(item)
    assert m["body"] == "" and m["user"] is None and m["labels"] == []
