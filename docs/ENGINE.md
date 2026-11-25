# The BlackBox Analysis Engine

This document describes BlackBox's **deterministic analysis engine** — the
backend logic that turns scattered evidence into a reconstructed, trustworthy
account of what happened. The engine contains **no LLM / AI in its core path**:
every result is reproducible and explainable. (An optional AI assistant may sit
*on top* of these results, but the engine never depends on it.)

## 1. Common event model

Every parser converts its input into a uniform **event** so that a git commit,
a CI log line and an application error are all reasoned about the same way. Key
fields: `timestamp` (+ `timestamp_confidence`), `source`, `source_line`,
`actor`, `action`, `object`, `severity`, `raw`, and a flexible `extra` map.
The original `raw` line is always preserved.

## 2. Ingestion & parsers

Format-specific parsers (`parsers/`) cover JSON, JSONL, CSV, plain logs, git
logs, CI/CD output and syslog. Uploaded files are **size-limited and
extension-checked**, stored under a **sanitized** name, and **SHA-256 hashed**
at ingestion.

## 3. Event normalization (`event_engine/normalizer.py`)

Extracts `actor` / `action` / `object`, IP addresses, and the HTTP status from a
raw line. HTTP status is read only from an unambiguous position (after a quoted
request, or an explicit `status=`), so IP octets and stray numbers are not
misread as status codes.

## 4. Temporal reconciliation (`temporal_engine/temporal.py`)

Rather than just sorting by time, the engine looks for inconsistencies. All
comparisons are timezone-safe (naive timestamps treated as UTC). Detectors:

| Detector | Flags |
|---|---|
| `out_of_order` | a later source line carrying an earlier timestamp |
| `clock_skew` | the **same actor + same action** across two sources with a large gap (action-matched to avoid false positives from ordinary elapsed time) |
| `duplicate_timestamps` | many events sharing one exact timestamp |
| `gap_anomaly` | an unusually large gap vs the source's median |
| `dependency_violation` | a **configured causal rule** broken — e.g. a `deploy` with no preceding `build` for that service |

Dependency rules are declared per workspace (`cause` / `effect` predicates,
`scope`, optional `max_lag_seconds`), making the check domain-agnostic.

## 5. Entity & relationship resolution (`relationship_engine/resolver.py`)

Extracts entities (user / ip / email / path / url / hash) from events and links
them into a graph. Canonicalization is **type-aware and case-safe**: casing is
folded only where it is not significant (ip/email/hash), so distinct
identifiers (`John` vs `john`, `/Users/Foo` vs `/users/foo`) are never silently
merged. The set of extracted types is workspace-configurable.

## 6. Evidence provenance & integrity (`evidence/`)

- **Integrity:** `integrity.verify_evidence()` recomputes a stored file's
  SHA-256 and reports `verified` / `modified` / `missing` — tamper detection and
  chain-of-custody.
- **Secret safety:** `event_engine/secret_scanner.py` detects and redacts
  leaked credentials in ingested evidence (keys, tokens, private keys,
  passwords) without altering the hashed source file.
- **Provenance tiers:** findings are distinguished as fact / inference /
  hypothesis so inferred data never masquerades as source fact.

## 7. Configurability (`core/workspace.py`)

A workspace YAML drives parser selection, temporal thresholds and dependency
rules, entity extraction, and export options — so the same engine serves
different investigation domains without code changes.

## Design principles

- **Deterministic core** — same input, same output; no AI in the analysis path.
- **Preserve originals** — original timestamps and raw lines are never
  destructively rewritten.
- **Evidence-first** — every finding is traceable to a hashed source, and facts,
  inferences and hypotheses are kept distinct.
