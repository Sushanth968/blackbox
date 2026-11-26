"""Tests for the log-family parsers not covered by test_parsers.py.

Covers: plain log parser, syslog parser, CI/CD parser, and git log parser.
All parsers take a file path and return a list of event dicts with a common
structure (timestamp, actor, action, object, severity, source_line, raw).
"""
from parsers.logs.log_parser import parse_log
from parsers.logs.syslog_parser import parse_syslog
from parsers.logs.cicd_parser import parse_cicd
from parsers.logs.git_parser import parse_git


# ── Plain log parser ─────────────────────────────────────────────────────────

def test_log_parser_reads_iso8601_timestamp(tmp_path):
    f = tmp_path / "app.log"
    f.write_text("2026-11-20T10:00:00Z INFO user alice logged in\n")
    events = parse_log(str(f))
    assert len(events) == 1
    assert events[0]["timestamp"] is not None


def test_log_parser_extracts_severity(tmp_path):
    f = tmp_path / "app.log"
    f.write_text("2026-11-20T10:00:00Z ERROR database connection failed\n")
    events = parse_log(str(f))
    assert events[0]["severity"] == "error"


def test_log_parser_includes_source_line(tmp_path):
    f = tmp_path / "app.log"
    f.write_text("2026-11-20T10:00:00Z INFO first\n2026-11-20T10:00:01Z INFO second\n")
    events = parse_log(str(f))
    assert events[0]["source_line"] == 1
    assert events[1]["source_line"] == 2


def test_log_parser_skips_blank_lines(tmp_path):
    f = tmp_path / "app.log"
    f.write_text("\n2026-11-20T10:00:00Z INFO event\n\n")
    events = parse_log(str(f))
    assert len(events) == 1


def test_log_parser_handles_line_without_timestamp(tmp_path):
    f = tmp_path / "app.log"
    f.write_text("no timestamp here\n")
    events = parse_log(str(f))
    # Line is kept as an event with no timestamp
    assert len(events) == 1
    assert events[0]["timestamp"] is None


def test_log_parser_raw_field_preserved(tmp_path):
    f = tmp_path / "app.log"
    line = "2026-11-20T10:00:00Z WARN disk usage high"
    f.write_text(line + "\n")
    events = parse_log(str(f))
    assert events[0]["raw"] == line


def test_log_parser_empty_file_returns_empty_list(tmp_path):
    f = tmp_path / "empty.log"
    f.write_text("")
    assert parse_log(str(f)) == []


def test_log_parser_syslog_style_timestamp(tmp_path):
    f = tmp_path / "syslog.log"
    f.write_text("Nov 20 10:00:00 host sshd[1234]: Accepted password for alice\n")
    events = parse_log(str(f))
    assert len(events) == 1
    assert events[0]["timestamp"] is not None


# ── Syslog parser ─────────────────────────────────────────────────────────────

def test_syslog_parser_reads_rfc3164_line(tmp_path):
    f = tmp_path / "sys.log"
    f.write_text("<30>Nov 20 10:00:00 myhost sshd[1234]: Accepted publickey for alice\n")
    events = parse_syslog(str(f))
    assert len(events) == 1


def test_syslog_parser_extracts_actor_from_process(tmp_path):
    f = tmp_path / "sys.log"
    f.write_text("<30>Nov 20 10:00:00 myhost sshd[1234]: Accepted publickey for alice\n")
    events = parse_syslog(str(f))
    # actor should be the process name or the user name
    assert events[0]["actor"] is not None


def test_syslog_parser_severity_from_priority(tmp_path):
    # priority <3> = kern.error → severity error
    f = tmp_path / "sys.log"
    f.write_text("<3>Nov 20 10:00:00 myhost kernel: Oops: general protection fault\n")
    events = parse_syslog(str(f))
    assert len(events) == 1
    assert events[0]["severity"] in {"error", "critical"}


def test_syslog_parser_skips_blank_lines(tmp_path):
    f = tmp_path / "sys.log"
    f.write_text("\n<30>Nov 20 10:00:00 myhost sshd: session opened\n\n")
    events = parse_syslog(str(f))
    assert len(events) == 1


def test_syslog_parser_includes_source_line(tmp_path):
    f = tmp_path / "sys.log"
    f.write_text(
        "<30>Nov 20 10:00:00 host sshd: opened\n"
        "<30>Nov 20 10:00:01 host sshd: closed\n"
    )
    events = parse_syslog(str(f))
    assert events[0]["source_line"] == 1
    assert events[1]["source_line"] == 2


def test_syslog_parser_empty_file(tmp_path):
    f = tmp_path / "empty.log"
    f.write_text("")
    assert parse_syslog(str(f)) == []


def test_syslog_parser_unrecognised_line_does_not_crash(tmp_path):
    f = tmp_path / "sys.log"
    f.write_text("this is not syslog format at all\n")
    events = parse_syslog(str(f))
    assert isinstance(events, list)


# ── CI/CD parser ──────────────────────────────────────────────────────────────

def test_cicd_parser_reads_github_actions_line(tmp_path):
    f = tmp_path / "ci.log"
    f.write_text("2026-11-20T10:00:00.000Z ##[error]Build failed: missing dependency\n")
    events = parse_cicd(str(f))
    assert len(events) == 1
    assert events[0]["severity"] == "error"


def test_cicd_parser_extracts_timestamp(tmp_path):
    f = tmp_path / "ci.log"
    f.write_text("2026-11-20T10:00:00.000Z ##[section]Build started\n")
    events = parse_cicd(str(f))
    assert events[0]["timestamp"] is not None


def test_cicd_parser_handles_generic_ci_format(tmp_path):
    f = tmp_path / "ci.log"
    f.write_text("2026-11-20T10:00:00Z [INFO] Running tests\n")
    events = parse_cicd(str(f))
    assert len(events) >= 1
    assert events[0]["timestamp"] is not None


def test_cicd_parser_warning_level_maps_to_warning(tmp_path):
    f = tmp_path / "ci.log"
    f.write_text("2026-11-20T10:00:00.000Z ##[warning]Deprecated API usage\n")
    events = parse_cicd(str(f))
    assert events[0]["severity"] == "warning"


def test_cicd_parser_includes_source_line(tmp_path):
    f = tmp_path / "ci.log"
    f.write_text(
        "2026-11-20T10:00:00.000Z ##[section]Start\n"
        "2026-11-20T10:00:01.000Z ##[section]End\n"
    )
    events = parse_cicd(str(f))
    assert events[0]["source_line"] == 1


def test_cicd_parser_empty_file(tmp_path):
    f = tmp_path / "empty.log"
    f.write_text("")
    assert parse_cicd(str(f)) == []


# ── Git log parser ────────────────────────────────────────────────────────────

_PRETTY_LOG = (
    "abc1234|alice@example.com|2026-11-20 09:00:00 +0000|fix: resolve nil pointer dereference\n"
    "def5678|bob@example.com|2026-11-20 10:00:00 +0000|feat: add retry logic\n"
)

_VERBOSE_LOG = """\
commit abc1234567890abcdef1234567890abcdef123456
Author: Alice <alice@example.com>
Date:   2026-11-20 09:00:00 +0000

    fix: resolve nil pointer dereference

commit def5678901234defabc5678901234defabc567890
Author: Bob <bob@example.com>
Date:   2026-11-20 10:00:00 +0000

    feat: add retry logic
"""


def test_git_parser_reads_pretty_format(tmp_path):
    f = tmp_path / "git.log"
    f.write_text(_PRETTY_LOG)
    events = parse_git(str(f))
    assert len(events) == 2


def test_git_parser_pretty_extracts_actor(tmp_path):
    f = tmp_path / "git.log"
    f.write_text(_PRETTY_LOG)
    events = parse_git(str(f))
    actors = {e["actor"] for e in events}
    assert "alice@example.com" in actors
    assert "bob@example.com" in actors


def test_git_parser_pretty_action_is_commit(tmp_path):
    f = tmp_path / "git.log"
    f.write_text(_PRETTY_LOG)
    for ev in parse_git(str(f)):
        assert ev["action"] == "commit"


def test_git_parser_pretty_has_timestamp(tmp_path):
    f = tmp_path / "git.log"
    f.write_text(_PRETTY_LOG)
    for ev in parse_git(str(f)):
        assert ev["timestamp"] is not None


def test_git_parser_reads_verbose_format(tmp_path):
    f = tmp_path / "git.log"
    f.write_text(_VERBOSE_LOG)
    events = parse_git(str(f))
    assert len(events) == 2


def test_git_parser_verbose_extracts_actor_email(tmp_path):
    f = tmp_path / "git.log"
    f.write_text(_VERBOSE_LOG)
    events = parse_git(str(f))
    actors = {e["actor"] for e in events}
    assert "alice@example.com" in actors


def test_git_severity_fix_commit_is_warning(tmp_path):
    f = tmp_path / "git.log"
    f.write_text("abc1234|dev@x.com|2026-11-20 09:00:00 +0000|fix: null pointer bug\n")
    events = parse_git(str(f))
    assert events[0]["severity"] == "warning"


def test_git_severity_security_commit_is_critical(tmp_path):
    f = tmp_path / "git.log"
    f.write_text("abc1234|dev@x.com|2026-11-20 09:00:00 +0000|security: patch CVE-2026-1234\n")
    events = parse_git(str(f))
    assert events[0]["severity"] == "critical"


def test_git_severity_normal_commit_is_info(tmp_path):
    f = tmp_path / "git.log"
    f.write_text("abc1234|dev@x.com|2026-11-20 09:00:00 +0000|refactor: clean up module\n")
    events = parse_git(str(f))
    assert events[0]["severity"] == "info"


def test_git_parser_empty_file(tmp_path):
    f = tmp_path / "git.log"
    f.write_text("")
    assert parse_git(str(f)) == []


def test_git_parser_commit_hash_in_extra(tmp_path):
    f = tmp_path / "git.log"
    f.write_text("abc1234|dev@x.com|2026-11-20 09:00:00 +0000|initial commit\n")
    events = parse_git(str(f))
    assert events[0]["extra"]["commit"] == "abc1234"
