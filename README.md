# BlackBox

**From scattered evidence to a reconstructed, evidence-backed explanation of what happened.**

BlackBox is an open-source, **evidence-driven event reconstruction and investigation platform**. It collects information from multiple sources, normalizes it into a common event model, reconstructs the sequence of events, flags inconsistencies and relationships, and generates an investigation report where **every finding is traceable to its original evidence**.

The first supported use case is **software incident investigation** — reconstructing what happened across logs, commits, CI/CD runs, deployments, and tickets — but the engine is domain-agnostic and configurable through *workspaces*.

---

## Why BlackBox?

When something breaks, evidence is scattered across systems with different formats, identifiers, and timestamp conventions. Reconstructing *what actually happened* means manually gathering records and guessing the sequence. Timestamps conflict (timezones, clock drift, delayed ingestion), relationships are implicit, and conclusions are hard to prove.

**BlackBox is not** another log viewer, observability dashboard, or AI chatbot. Its defensible core is three things:

1. **Temporal reconciliation under uncertainty** — detects clock drift, timezone disagreement, duplicate-vs-distinct events, and *impossible ordering* against configured dependency rules. Preserves original timestamps and surfaces partial ordering explicitly instead of faking a clean line.
2. **Evidence-first provenance** — every event and finding links back to a **SHA-256-hashed original source**, with strict separation of *fact / extracted / inferred / AI-hypothesis / user-confirmed*.
3. **A configurable, domain-agnostic engine** — a *workspace* config defines event types, entities, relationship rules, and temporal constraints, keeping the core reusable across domains.

> An LLM gives a fast, plausible *story* — non-reproducible, unverifiable, and it smooths over contradictions. BlackBox produces a reproducible, evidence-backed *case file* that surfaces the conflicts an LLM would miss. The optional AI assistant runs *on top of* verified evidence, so its help becomes trustworthy.

---

## Features

- **Multi-source ingestion** — JSON, JSONL, CSV, plain logs, syslog, CI/CD output
- **Temporal reconciliation engine** — detects out-of-order events, clock skew, duplicate timestamps, gap anomalies, and dependency-rule violations
- **Reconstruction confidence scoring** — 5-dimension weighted score (timestamp coverage, evidence integrity, temporal consistency, evidence coverage, extraction confidence) with High/Medium/Low/Critical labels; gap timeline shows unaccounted intervals
- **Event label pinning** — classify any event as `fact`, `inference`, or `hypothesis` directly from the timeline; labels persist and feed the confidence score
- **Secret scanning & redaction** — deterministic (no AI), detects and redacts leaked credentials before they are persisted or exported; replaces secrets with `[REDACTED:<detector>:<fingerprint>]` so recurrence is still correlatable
- **Evidence integrity** — SHA-256 hash per uploaded source file; redaction never touches the original
- **Relationship mapping** — identifier-based entity and relationship extraction across sources
- **Interactive timeline** — filterable by severity, actor, and inferred category (deploy, CI/CD, auth, database, security, GitHub, API, cron, temporal) with live category counts
- **Entity graph** — interactive relationship graph
- **Investigation reports** — export as JSON or Markdown
- **Evidence library** — global table of all uploaded files across every investigation, searchable by name with status filters
- **Workspaces dashboard** — overview of all investigations with note/flag/evidence counts and inline note management
- **GitHub Issue Tracker** — browse open issues for any public repo; get AI-generated root-cause analysis and fix suggestions powered by Claude
- **Workspace configs** — domain-agnostic engine driven by YAML configs (`developer` and `custom` workspaces included)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript + Tailwind CSS + Vite |
| Backend | Python + FastAPI |
| Database | SQLite (dev default) / PostgreSQL (Docker) |
| ORM | SQLAlchemy (async) |
| Graph / temporal | networkx |
| Reports | JSON, Markdown |
| AI (optional) | Claude via Anthropic API (off by default) |
| Testing | Pytest, Vitest / React Testing Library |
| Deployment | Docker Compose |

---

## Getting Started

### Option 1 — Docker (recommended)

```bash
git clone https://github.com/Sushanth968/blackbox.git
cd blackbox
docker compose up
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

### Option 2 — Local development

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The backend defaults to SQLite (`blackbox.db` in `backend/`). To use PostgreSQL, set `DATABASE_URL` in a `.env` file:

```
DATABASE_URL=postgresql+asyncpg://blackbox:blackbox@localhost:5432/blackbox
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

**Optional — AI features**

Create `backend/.env` and add your keys:

```
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...        # for private repos or higher rate limits
```

---

## Repository Structure

```
blackbox/
├── backend/
│   ├── main.py                  FastAPI app + startup
│   ├── api/                     Investigation + global API routes
│   ├── investigation/           Investigation CRUD
│   ├── evidence/                Evidence upload & ingestion
│   ├── event_engine/            Event normalization, secret scanner
│   ├── temporal_engine/         Temporal reconciliation, confidence scoring, gap detection
│   ├── relationship_engine/     Entity & relationship resolver
│   ├── ingestion/               Multi-format ingestion processor
│   ├── reporting/               JSON / Markdown export
│   ├── github_issues/           GitHub issue fetcher + AI analysis
│   ├── models/                  SQLAlchemy ORM models
│   ├── schemas/                 Pydantic request/response schemas
│   └── core/                    Config, workspace loader
├── frontend/
│   └── src/
│       ├── pages/               Investigations, detail, evidence library, workspaces, GitHub issues
│       ├── components/          Evidence panel, confidence panel, export panel, workspace panel
│       ├── timeline/            Interactive event timeline with category filters
│       └── graph/               Entity relationship graph
├── parsers/                     JSON, JSONL, CSV, log, syslog, CI/CD parsers
├── workspaces/                  Domain workspace configs (developer, custom)
├── tests/                       Unit tests (temporal, parsers, normalizer, secret scanner)
└── docs/                        Architecture, event schema, API docs
```

---

## Roadmap

- [x] Project foundation — repo, schema, investigation creation, evidence upload
- [x] Parsers — JSON, JSONL, CSV, plain logs, syslog, CI/CD
- [x] Event normalization to a common event model
- [x] Temporal reconciliation engine (out-of-order, clock skew, duplicates, gap anomalies, dependency violations)
- [x] Secret scanning and redaction in ingested evidence
- [x] Entity & relationship extraction
- [x] Evidence provenance and SHA-256 integrity
- [x] Interactive timeline and entity graph
- [x] Investigation report export (JSON, Markdown)
- [x] Workspace configs (developer, custom)
- [x] Docker Compose one-command setup
- [x] GitHub Issue Tracker with AI-powered analysis
- [x] Reconstruction confidence scoring (5-dimension weighted score + gap timeline)
- [x] Event label pinning (fact / inference / hypothesis) from the timeline
- [x] Timeline category filters (deploy, CI/CD, auth, DB, security, API, cron, temporal, GitHub)
- [x] Evidence library and workspaces dashboard
- [ ] Direct GitHub / Jira / CI integrations (live event streaming)
- [ ] OpenTelemetry ingestion
- [ ] PDF report export
- [ ] Collaborative investigations (multi-user)
- [ ] In-investigation AI assistant (evidence-grounded)
- [ ] Custom anomaly rules UI

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and our [Code of Conduct](CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE).

## Authors

- Sushanth ([@Sushanth968](https://github.com/Sushanth968))
- Karthik ([@Karthik-0-8](https://github.com/Karthik-0-8))
