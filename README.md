# BlackBox

**From scattered evidence to a reconstructed, evidence-backed explanation of what happened.**

BlackBox is an open-source, **evidence-driven event reconstruction and investigation platform**. It collects information from multiple sources, converts it into a standardized event model, reconstructs the sequence of events, flags inconsistencies and relationships, and generates an investigation report in which **every finding is traceable to its original evidence**.

The first supported use case is **software incident investigation** for developers — reconstructing what happened across logs, commits, CI/CD runs, deployments and tickets — but the engine is domain-agnostic and configurable through *workspaces*.

> Status: early development (project scaffold). See the [roadmap](#roadmap).

---

## The problem

When something breaks, the evidence is scattered across systems that each use different formats, identifiers and timestamp conventions — git history, CI logs, application logs, deployment records, issue trackers. Reconstructing *what actually happened* means manually gathering those records and guessing the sequence. Timestamps conflict (timezones, clock drift, delayed ingestion), relationships are implicit, and conclusions are hard to prove.

## What makes BlackBox different

BlackBox is **not** another log viewer, observability dashboard, or AI chatbot. Its defensible core is three things:

1. **Temporal reconciliation under uncertainty** — it does not just sort by timestamp. It detects clock drift, timezone disagreement, duplicate-vs-distinct events and *impossible ordering* against configured dependency rules, **preserves the original timestamps**, and represents uncertain/partial ordering explicitly instead of faking a clean line.
2. **Evidence-first provenance** — every event and finding links back to a **SHA-256-hashed original source**, with strict separation of *fact / extracted / inferred / AI-hypothesis / user-confirmed*.
3. **A configurable, domain-agnostic engine** — the same core serves different domains; a *workspace* config defines event types, entities, relationship rules and temporal constraints.

### Why not just ask an LLM to investigate?

For a quick solo bug, asking an LLM is fine. But an LLM gives a fast, plausible **story** — non-reproducible, unverifiable, limited to what fits in a prompt, and it *smooths over* contradictions in the data. BlackBox produces a reproducible, evidence-backed **case file**: deterministic, with every claim provable from a hashed source, and it **surfaces** the timestamp conflicts an LLM would miss. BlackBox doesn't compete with an LLM — its optional assistant runs *on top of* the verified evidence, so the LLM's help becomes trustworthy.

### Honest prior art

Related tools exist — [Horus](https://horus.sh/) and [SerOps](https://serops.ai/) (developer incident investigation), NetForensicAI (forensics), Evidence Board (evidence organization), OpenTelemetry (telemetry infrastructure). BlackBox's contribution is the specific combination above: a *configurable* reconstruction engine centered on *temporal reconciliation* and *evidence provenance*, rather than a domain-locked incident tool.

## Core features

- Multi-source evidence ingestion (JSON, CSV, log files to start)
- Event extraction and normalization to a common event model
- Interactive, filterable event timeline
- Temporal conflict & anomaly detection (drift, timezone, duplicates, impossible ordering)
- Entity & relationship mapping (interactive graph)
- Evidence provenance, integrity (SHA-256) and confidence tracking
- Investigation report generation (JSON, Markdown, PDF)
- Optional, pluggable, off-by-default AI assistant (grounded, evidence-cited)

## MVP scope (this assignment)

Developer workspace only: create investigation → upload JSON/CSV/log evidence → parse & normalize → interactive timeline → **temporal reconciliation engine** → evidence provenance + integrity → basic identifier-based relationships → report export. A tiny second-workspace config demonstrates that the engine is not hardcoded. The AI assistant and direct integrations are deferred (see [roadmap](#roadmap)).

## Architecture

Modular monolith. See [docs/architecture](docs/architecture/README.md) for the module breakdown and data flow, and [docs/event-schema](docs/event-schema/README.md) for the common event model.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript + Tailwind CSS |
| Backend | Python + FastAPI |
| Database | PostgreSQL + SQLAlchemy (+ Alembic) |
| Graph/temporal | networkx |
| Reports | WeasyPrint (PDF), JSON, Markdown |
| AI (optional) | Pluggable LLM provider (off by default) |
| Testing | Pytest, Vitest / React Testing Library |
| Deployment | Docker Compose |

## Repository structure

```
blackbox/
├── frontend/     React + TS investigation UI (timeline, graph, evidence, reports)
├── backend/      FastAPI app + engines (ingestion, event, temporal, relationship, evidence, investigation, reporting)
├── workspaces/   Domain configs (developer, custom)
├── parsers/      Format parsers (json, csv, logs)
├── tests/        unit / integration / datasets
└── docs/         architecture, api, event-schema, user-guide
```

## Getting started

> Setup instructions will land with the first backend and frontend scaffolding. Planned: `docker compose up` for a one-command local environment.

## Roadmap

- [ ] Phase 1 — Project foundation (repo, schema, investigation creation, evidence upload)
- [ ] Phase 2 — Event processing (JSON/CSV/log parsers, normalization)
- [ ] Phase 3 — Timeline & temporal analysis (the core differentiator)
- [ ] Phase 4 — Relationships & evidence provenance
- [ ] Phase 5 — Investigation findings & reporting
- [ ] Phase 6 — Extensibility (workspace configs), tests, Docker, release

Future: direct GitHub/Jira/CI integrations, OpenTelemetry ingestion, the AI assistant, custom anomaly rules, collaborative investigations.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and our [Code of Conduct](CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE).

## Authors

- Sushanth ([@Sushanth968](https://github.com/Sushanth968))
- Karthik
