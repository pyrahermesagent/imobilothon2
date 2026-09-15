# Domain Model — notes-app (modernized)

> Source: tests/fixture-source (notes-app) — modernize-modeler output; every id below resolves to modernization-plan.json.
> No modernization decision re-shapes this document; the model is kept as-is per K-1.

## Scope

The domain of the modernized system is unchanged: users authenticate and own notes
(`models.py:7-29`). The transport and persistence modernizations (M-1, M-2) change how the
domain is served and stored, not the domain concepts themselves.

## Ubiquitous Language

| term | meaning |
| :-- | :-- |
| User | an account identified by a unique email (`models.py:7-14`) |
| Note | a titled body of text owned by one User (`models.py:23-29`) |
| Ownership | the 1:N User-to-Note relationship (`models.py:14`) |
| Credential | the email + password pair verified at login (`routes/auth.py:9-15`) |

## Bounded Context

A single bounded context (the notes context) with no subdomains. The context boundary is the
public HTTP API; modernization exposes it as FastAPI OpenAPI (M-1) without moving the boundary.

## Entities

- **User** — email, password_hash, is_active, created_at (`models.py:7-14`).
- **Note** — title, body, created_at, owner reference (`models.py:23-29`).

## Value Objects

- **Email** — unique, case-normalized at login (`routes/auth.py:9-15`).
- **NoteBody** — the text payload with a non-empty title; since M-4 the non-emptiness is
  machine-checked by the request schema instead of a raw dict access.

## Aggregates

- **UserAggregate** — root User with its Notes as members; invariants are held at the root (K-1).
- **NoteAggregate** — a single-entity aggregate; its membership in a User is the ownership link.

## Relationships

User owns Note (1:N) (`models.py:14`); Note references User through `user_id`
(`migrations/0001_init.sql:11`). Both relationships are kept unchanged (K-1).

## Invariants

1. A User's email is unique (`migrations/0001_init.sql:3`).
2. Every Note has exactly one owning User (`migrations/0001_init.sql:11`).
3. A Note's title is non-empty — enforced by the Pydantic request schema since M-4, not by an
   ad-hoc check in the handler.

## Domain Events

- **UserCreated** — emitted on registration (`models.py:7-14`).
- **NoteCreated** — emitted on a successful note insert (`routes/notes.py:9-15`).
- **NoteRead** — read-model event emitted by the get-note path (`routes/notes.py:18-21`).

## Domain Services

- **PasswordVerification** — the hash check moves off the model into a domain service
  (legacy `check_password` on the model, `models.py:16-20`). Semantics stay email + password
  (K-2); only the location and the async call path change (M-1).

## Modernization Decisions (this document)

| id | decision | effect on this document |
| :-- | :-- | :-- |
| K-1 | keep entity shape | entities, aggregates and relationships kept as-is |
| K-2 | keep login semantics | password-verification semantics unchanged |
| M-4 | typed request schemas | invariant 3 becomes machine-checked |

## Resolved Assumptions & Issues

The plan scopes no assumption or issue to this document (`artifact_scopes.DomainModel.md` is
empty in modernization-plan.json), and the source artifact carried no open assumption markers.
Nothing to resolve here; the model is closed as kept (K-1).
