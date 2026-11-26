"""Tests for the entity resolver's classification and canonicalization.

These are the pure, deterministic helpers the async ``resolve_entities`` relies
on — including the regression guard for the case-folding wrong-merge bug.
"""
from relationship_engine.resolver import classify_entity, canonicalize, entity_key


def test_classifies_common_entity_types():
    assert classify_entity("10.0.0.1") == "ip"
    assert classify_entity("alice@example.com") == "email"
    assert classify_entity("/var/log/app.log") == "path"
    assert classify_entity("https://example.com/x") == "url"
    assert classify_entity("alice") == "user"


def test_usernames_are_case_sensitive_and_not_merged():
    # Regression: 'John' and 'john' must stay distinct entities.
    assert entity_key("John") != entity_key("john")


def test_paths_are_case_sensitive_and_not_merged():
    assert entity_key("/Users/Foo") != entity_key("/users/foo")


def test_emails_are_case_folded_and_merged():
    assert entity_key("Alice@Example.COM") == entity_key("alice@example.com")


def test_pure_decimal_is_not_mistaken_for_a_hash():
    assert classify_entity("1234567") == "user"   # was wrongly "hash" before
    assert classify_entity("deadbeef") == "hash"   # genuine hex still detected


def test_aliases_are_applied_in_canonicalization():
    assert canonicalize("bob", "user", {"bob": "robert"}) == "robert"
