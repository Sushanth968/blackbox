"""Regression tests for parser module resolution (backend/ingestion/processor.py).

The parsers live in the repo-root ``parsers/`` package. A previous setup put
``parsers/`` at the front of ``sys.path`` and imported them as top-level
``json`` / ``csv`` modules, which shadowed the standard library and broke both
the processor import and the parsers' own ``import json`` / ``import csv``.
These tests lock in the namespaced ``parsers.*`` imports and verify the stdlib
is not shadowed.
"""
import csv
import json

from parsers.csv.parser import parse_csv
from parsers.json.jsonl_parser import parse_jsonl
from parsers.json.parser import parse_json


def test_stdlib_json_and_csv_not_shadowed():
    assert json.loads('{"a": 1}') == {"a": 1}
    assert hasattr(csv, "DictReader")


def test_json_parser_reads_events(tmp_path):
    f = tmp_path / "evidence.json"
    f.write_text('[{"timestamp": "2024-01-01T00:00:00Z", "action": "login", "user": "alice"}]')
    events = parse_json(str(f))
    assert len(events) == 1
    assert events[0]["actor"] == "alice"
    assert events[0]["action"] == "login"


def test_jsonl_parser_reads_events(tmp_path):
    f = tmp_path / "evidence.jsonl"
    f.write_text('{"ts": "2024-01-01T00:00:00Z", "user": "bob", "action": "deploy"}\n')
    events = parse_jsonl(str(f))
    assert len(events) == 1
    assert events[0]["actor"] == "bob"


def test_csv_parser_reads_events(tmp_path):
    f = tmp_path / "evidence.csv"
    f.write_text("timestamp,user,action\n2024-01-01T00:00:00Z,carol,deploy\n")
    events = parse_csv(str(f))
    assert len(events) == 1
    assert events[0]["actor"] == "carol"
    assert events[0]["action"] == "deploy"
