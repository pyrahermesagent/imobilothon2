# Specification — notes-app (modernized)

> Source: tests/fixture-source (notes-app) — produced by modernize-modeler against modernization-plan.json + intake.json.
> All citations point at the repo snapshot unless a `*.md` source artifact is cited; every decision/assumption id resolves to modernization-plan.json.

## Executive Summary

notes-app is a small single-user notes service: a user authenticates with login and password, then creates and reads notes. The source implementation is Python 3.12 on Flask 3.0.0 with Flask-SQLAlchemy on a SQLite file, a single hand-written SQL migration, no tests, and a `debug=True` entrypoint (`requirements.txt:1`, `app.py:17-18`). This modernized specification keeps the feature set and the two-table schema shape **kept (K-1, K-2)** and changes the implementation: FastAPI + Pydantic v2 replaces Flask (M-1), SQLAlchemy 2.x async + Alembic replaces Flask-SQLAlchemy (M-2), PostgreSQL 16 replaces SQLite (M-3), typed request models make invalid input fail with 422 instead of 500 (M-4), and pytest + CI replaces the absent test suite (M-5, M-6).

## Project Scope

In scope: the three REST endpoints (login, create note, read notes), the two-table persistence model, and the deployment entrypoint. Out of scope: any frontend (directive D-5 — no frontend is modeled, A-1), multi-user permissions beyond the existing owner filter, and background jobs. The endpoints and their ownership semantics are unchanged from the source: `routes/auth.py:9-15` and `routes/notes.py:9-21`.

## Technology Stack

| Layer | Source (cited) | Modernized target | Decision |
|---|---|---|---|
| Language | Python 3.12 (`requirements.txt:1`) | Python 3.13 | D-1 (keep Python) |
| Web framework | Flask 3.0.0, sync handlers (`app.py:7`) | FastAPI 0.115 + Pydantic v2, async handlers | M-1 |
| ORM / data | Flask-SQLAlchemy 3.1.1, SQLite at `./notes.db` (`app.py:8-9`, `db.py:1-4`) | SQLAlchemy 2.x async + Alembic on PostgreSQL 16, `DATABASE_URL` from environment | M-2, M-3 |
| Validation | manual `get_json` + dict access (`routes/notes.py:9-15`) | Pydantic v2 request/response models, declarative 422 | M-4 |
| Tests | none (`requirements.txt:1-2` contains no test tooling) | pytest 8.x + httpx AsyncClient, 80% coverage gate, GitHub Actions on every push | M-5 |
| Deployment | `app.run(debug=True)` dev server (`app.py:18`) | Docker image, uvicorn + gunicorn workers, debug disabled by construction | M-6 |

## Functional Requirements

- **FR-1 Login.** `POST /api/login` validates `login`/`password` against the `users` table and returns a session token; failure returns 401. Source behavior kept verbatim **kept (K-2)** (`routes/auth.py:9-15`).
- **FR-2 Create note.** `POST /api/notes` requires a valid token and a `title`; it stores a `notes` row owned by the user and returns the created record with 201. Modernized: a missing `title` key now yields 422 with field errors instead of an unhandled `KeyError` → 500 (M-4, `routes/notes.py:9-15`).
- **FR-3 Read notes.** `GET /api/notes` requires a valid token and returns the notes owned by that user only (`routes/notes.py:18-21`).
- **FR-4 Schema.** The `users` and `notes` tables and their 1:N ownership are **kept (K-1)** and re-issued as the Alembic baseline revision (`migrations/0001_init.sql:2-16`).

## Non-Functional Requirements

- **NFR-1 Input safety.** Invalid input must produce a structured 4xx (422 with field errors, 400 for an empty title), never a 500 — the source's raw-500 error class is closed by Pydantic request models (M-4).
- **NFR-2 Production entrypoint.** The service runs with debug disabled by construction; environment-driven configuration (`DATABASE_URL`, `SECRET_KEY`) replaces hardcoded local paths (M-6, `app.py:17-18`).
- **NFR-3 Verifiability.** A pytest + httpx suite with an 80% line-coverage gate runs in GitHub Actions on every push (M-5). The source had no tests (A-2).
- **NFR-4 Concurrency.** Handlers are async and the database is PostgreSQL, so multiple uvicorn workers share one safe backend (M-1, M-3). Deep concurrency modeling is deferred per A-6.

## Data Model

The two-table shape is **kept (K-1)**: `users` (id, login, password hash, email) and `notes` (id, owner id, title) with a 1:N ownership index (`migrations/0001_init.sql:2-16`, `migrations/0001_init.sql:18`). The ORM mapping keeps the same attributes (`models.py:7-29`) and the modernized stack issues the schema through Alembic migrations instead of a hand-edited file (M-2). The User mapping is defined at `models.py:7-20`.

## API Specification

Base path `/api`; JSON bodies; `Authorization: Bearer <token>` on note endpoints.

- `POST /api/login` — body `{login, password}`; 200 with `{token}` on success; 401 on bad credentials (K-2, `routes/auth.py:9-15`).
- `POST /api/notes` — body `{title}`; 401 with missing/invalid token; 422 with field errors when `title` is absent (M-4, `routes/notes.py:9-15`); 400 when `title` is empty; 201 with the created note.
- `GET /api/notes` — 401 with missing/invalid token; 200 with the list of the caller's notes (`routes/notes.py:18-21`).
- OpenAPI document served automatically at `/docs` (M-1).

## UI/UX

No frontend: the source models none (A-1) and directive D-5 defers any UI work. The consumer surface is the OpenAPI page (`/docs`) generated by FastAPI (M-1), which documents every endpoint, schema, and error code above.

## Testing Strategy

pytest 8.x with httpx `AsyncClient` against the FastAPI app (M-5): one test module per router — auth (`routes/auth.py:9-15`) and notes (`routes/notes.py:9-21`). Coverage gate at 80% lines; GitHub Actions runs the suite on every push (CI workflow per M-5). This replaces the absent suite flagged in the source (A-2, `Specification.md:67`) and makes the 422 behavior (M-4) and the async handlers (M-1) explicitly verifiable.

## Deployment

Docker image exposing uvicorn with gunicorn workers; `DATABASE_URL` and `SECRET_KEY` injected from the environment (M-6, `app.py:18`). Debug mode is unavailable in the production entrypoint by construction (I-1). CI (M-5) gates every push before deployment.

## Modernization Decisions (this document)

| Decision | Source evidence | Modernized effect |
|---|---|---|
| M-1 Flask -> FastAPI | `requirements.txt:1`, `app.py:7` | async endpoints, Pydantic models, auto OpenAPI |
| M-2 ORM/migrations | `requirements.txt:2`, `migrations/0001_init.sql:1` | SQLAlchemy 2.x async + Alembic baseline |
| M-3 SQLite -> PostgreSQL | `app.py:8-9` | PostgreSQL 16, `DATABASE_URL` from environment |
| M-4 typed schemas | `routes/notes.py:9-15` | 422 with field errors instead of 500 |
| M-5 pytest + CI | `requirements.txt:1-2` | 80% coverage gate, GitHub Actions on push |
| M-6 deployment | `app.py:17-18` | Docker + uvicorn workers, debug off by construction |

## Resolved Assumptions & Issues

| Id | Source artifact | Disposition | Closed by |
|---|---|---|---|
| A-1 | `Specification.md:21` | accepted (directive D-5: no frontend) | — |
| A-2 | `Specification.md:67` | resolved | M-5 |
| I-1 | `Specification.md:67` | resolved | M-6 |
| I-2 | `Specification.md:21` | resolved | M-4 |

Kept elements: **K-1** two-table schema and 1:N ownership (`migrations/0001_init.sql:2-16`); **K-2** email+password login semantics (`routes/auth.py:9-15`).
