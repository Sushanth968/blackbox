# Contributing to BlackBox

Thanks for your interest in BlackBox! This document explains how we work.

## Ground rules

- Be respectful. See our [Code of Conduct](CODE_OF_CONDUCT.md).
- Every change goes through a **pull request** — nothing is pushed straight to `main`.
- **PRs are reviewed by another team member before merge.** Self-merged, unreviewed PRs are not acceptable (this is both good practice and an explicit requirement of our course evaluation).
- Each contributor commits under their **own** GitHub account so contributions are individually traceable.

## Development workflow

1. Create a branch off `main`: `git checkout -b <type>/<short-description>` (e.g. `feat/temporal-conflict-detector`).
2. Make focused commits (see commit style below).
3. Open a pull request describing **what** changed and **why**, and link any related issue.
4. A teammate reviews, requests changes if needed, and approves.
5. Squash-or-merge once approved and CI (when set up) is green.

## Issues

We track work as GitHub issues. Before starting, check for an existing issue or open one describing the problem/feature. Keep issues small and actionable.

## Commit style

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<optional scope>): <summary>

<optional body>
```

Common types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`.

## Code quality

- Backend (Python): keep functions small and testable; add `pytest` tests for new engine logic.
- Frontend (TypeScript): typed components; add tests for non-trivial logic.
- The deterministic core must not depend on any AI model. AI features are optional and isolated.

## Project layout

See the repository structure in the [README](README.md).

## Setting up locally

> Detailed setup will be documented as the backend and frontend scaffolding lands. The target is a one-command `docker compose up` environment plus separate dev servers for frontend and backend.
