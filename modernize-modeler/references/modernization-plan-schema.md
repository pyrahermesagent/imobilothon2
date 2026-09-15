# modernization-plan.json — Schema (written by the Modernization Planner, consumed by all Modernizers, Critics and the Fixer)

Single file: `<MOD>/modernization-plan.json`. Valid JSON only (no comments, no trailing
commas). This file is the **single source of truth for every modernization decision and
for the closure of every assumption/issue** the codebase-modeler run left open. The
mechanical verifier (`scripts/verify.py`) enforces the structural rules at the bottom.

```json
{
  "repo_name": "notes-app",
  "source": {
    "dir": "output/notes-app",
    "repo_sha": "9f86d08...",
    "inputs_available": {"repo": true, "plan": true, "inventory": true, "evidence": true, "verification": true}
  },
  "directives": {
    "raw": "keep Python; Flask -> FastAPI; PostgreSQL; add pytest + CI; no frontend needed",
    "items": [
      {"id": "D-1", "kind": "keep",   "text": "keep Python",                    "disposition": "decision", "refs": ["M-1"]},
      {"id": "D-2", "kind": "change", "text": "Flask -> FastAPI",               "disposition": "decision", "refs": ["M-1", "M-2"]},
      {"id": "D-3", "kind": "add",    "text": "add pytest + CI",                "disposition": "decision", "refs": ["M-5"]},
      {"id": "D-4", "kind": "defer",  "text": "no frontend needed",             "disposition": "kept_unchanged", "refs": [], "reason": "source models no frontend; nothing to modernize"}
    ]
  },
  "stack": {
    "frontend": {"current": "none", "current_citations": ["`Specification.md:89`"],
                 "target": "none (per D-4)", "citations": []},
    "backend": {"current": "Python 3.12 + Flask 3.0.0", "current_citations": ["`requirements.txt:1`"],
                "target": "Python 3.13 + FastAPI 0.115 + Pydantic 2.x", "citations": ["`requirements.txt:1-2`", "`app.py:7`"]},
    "database": {"current": "SQLite via Flask-SQLAlchemy", "current_citations": ["`app.py:8-9`"],
                 "target": "PostgreSQL 16 + SQLAlchemy 2.x (async) + Alembic", "citations": ["`migrations/0001_init.sql:1`"]},
    "infrastructure": {"current": "none (dev server only)", "current_citations": ["`app.py:17-18`"],
                       "target": "Docker + uvicorn workers + GitHub Actions CI", "citations": ["`app.py:18`"]}
  },
  "decisions": [
    {
      "id": "M-1",
      "area": "tech_stack",
      "summary": "Replace Flask with FastAPI: async endpoints, Pydantic v2 request/response models, auto OpenAPI",
      "from": "Flask 3.0.0, manual request.get_json + jsonify, unhandled KeyError -> 500",
      "from_citations": ["`requirements.txt:1`", "`routes/notes.py:9-15`", "`routes/notes.py:13`"],
      "to": "FastAPI + Pydantic v2 models; declarative 422 error responses; OpenAPI docs at /docs",
      "why": "modern default framework; built-in validation kills the raw-500 error class; async for I/O-bound handlers",
      "directive_refs": ["D-2"],
      "artifacts": ["Specification.md", "ClassModel.md", "UseCaseModel.md", "ActivityDiagram.md"]
    }
  ],
  "kept": [
    {"id": "K-1", "element": "User/Note entities, 1:N ownership, email+password login semantics",
     "citations": ["`models.py:7-29`", "`routes/auth.py:9-15`"], "directive_ref": "D-1"}
  ],
  "assumptions": [
    {"id": "A-1", "source_doc": "Specification.md",
     "quote": "no test suite in repo - UNVERIFIED",
     "status": "resolved",
     "resolution": "Testing strategy added: pytest + httpx AsyncClient, 80% line coverage target (M-5)",
     "decision_refs": ["M-5"]},
    {"id": "A-2", "source_doc": "DatabaseModel.md",
     "quote": "deployment target UNVERIFIED (no hosting metadata)",
     "status": "deferred",
     "reason": "user gave no hosting directive; plan targets plain Docker, provider choice stays open"}
  ],
  "issues": [
    {"id": "I-1", "source_doc": "Specification.md",
     "quote": "debug=True in the entrypoint is an anti-pattern for any non-local deployment",
     "status": "resolved",
     "resolution": "Production entrypoint via uvicorn workers, debug disabled (M-6)",
     "decision_refs": ["M-6"]},
    {"id": "I-2", "source_doc": "Specification.md",
     "quote": "unhandled KeyError -> 500 on POST /api/notes",
     "status": "resolved",
     "resolution": "Pydantic request models turn the 500 into a 422 with field errors (M-1)",
     "decision_refs": ["M-1"]}
  ],
  "artifact_scopes": {
    "Specification.md": {"decisions": ["M-1", "M-5", "M-6"], "assumptions": ["A-1", "A-2"], "issues": ["I-1", "I-2"], "kept": ["K-1"]},
    "DatabaseModel.md": {"decisions": ["M-3"], "assumptions": ["A-2"], "issues": [], "kept": ["K-1"]},
    "ClassModel.md":    {"decisions": ["M-1", "M-2"], "assumptions": [], "issues": ["I-2"], "kept": ["K-1"]},
    "DomainModel.md":   {"decisions": [], "assumptions": [], "issues": [], "kept": ["K-1"]},
    "UseCaseModel.md":  {"decisions": ["M-1"], "assumptions": [], "issues": ["I-2"], "kept": ["K-1"]},
    "ActivityDiagram.md": {"decisions": ["M-1", "M-3"], "assumptions": [], "issues": [], "kept": []}
  }
}
```

## Key rules

### Reference ids (the modernization traceability contract)
- `M-n` — modernization decision (a change/keep/add of a technology or approach).
- `D-n` — user directive item (parsed from the free-text `directives` argument).
- `K-n` — explicitly kept element (identity preserved across modernization).
- `A-n` — assumption/UNVERIFIED item inherited from a source artifact.
- `I-n` — concrete issue (security hole, anti-pattern, defect) found in a source artifact.
Every one of these ids is referenced by the six modernized documents with backticks; the
mechanical verifier fails the document if a referenced id is not in this file.

### directives
- `raw` echoes the user's free text verbatim. `items` is the planner's parse: every
  sentence/clause that constrains the modernization gets an id. `kind` ∈
  `keep | change | add | defer`.
- A directive is *covered* when `disposition: "decision"` with non-empty `refs` (one or more
  M-ids that implement it), or `disposition: "deferred" | "kept_unchanged"` with a `reason`.
  The verifier rejects a plan where a directive is covered neither way. **A user request that
  silently disappears is a plan defect, not a judgment call.**

### decisions
- Every decision: unique `M-n` id, `area` (tech_stack | architecture | data_model | api |
  security | testing | deployment | error_handling | performance | other), `summary`,
  `from` + `from_citations` (what the source system has - citations into the repo or the
  source artifacts), `to` (concrete modern target: real package names, specific or
  major-pinned versions, named pattern), `why`, `directive_refs` (empty only for
  planner-initiated decisions), `artifacts` (which of the six documents must apply it).
- Never invent a target framework/package that does not exist. If the exact current version
  of a target is unknown, name the major line and set `"check_latest": true` on the decision.
- Two decisions must not assign incompatible targets to the same layer (the semantic verifier
  cross-checks this).

### kept
- Elements the user (or the planner) decided to carry over unchanged. `citations` point at
  the source code; `directive_ref` is the D-id that asked for it, or `"planner"`.
- Modernizers mark kept elements with `kept (K-n)`; Critics verify identity (name,
  responsibilities) is preserved in the modernized documents.

### assumptions / issues
- `assumptions`: one entry per UNVERIFIED marker (logical item) in the source artifacts.
  `source_doc` is the artifact it came from; `quote` is the marker text (≤ 120 chars).
- `issues`: one entry per concrete defect/anti-pattern/security problem the source artifacts
  flag (or the planner finds by re-reading the cited lines).
- Both use a **terminal** `status`:
  - `resolved` — the modernization fixes it; MUST carry `decision_refs` (the M-ids doing the
    fixing) and a `resolution` sentence.
  - `accepted` — consciously left as-is; MUST carry a `reason`.
  - `deferred` — out of scope for this modernization; MUST carry a `reason`.
- The verifier requires at least one ledger entry per source artifact that contains
  UNVERIFIED markers, and warns when total entries < total markers (the Critic does the
  item-by-item check).

### artifact_scopes
- One entry per artifact (all six keys always present, lists may be empty). Tells each
  Modernizer exactly which decisions to apply and which assumptions/issues to close in its
  document, and which kept elements to preserve. If a decision lists an artifact in
  `artifacts`, the scope entry for that artifact must include the decision id (verifier +
  Critic check consistency).

## Rules the orchestrator validates before dispatching Modernizers
- File parses as JSON; all top-level keys present.
- Every decision: `M-n` id, non-empty `summary`, ≥ 1 citation, non-empty `why`, `artifacts`
  ⊆ the six artifact names.
- Every directive item is covered (see above).
- Every assumption/issue has a terminal status with the required companion fields.
- Ledger coverage: ≥ 1 entry per source artifact with UNVERIFIED markers.
- `artifact_scopes` lists all six artifacts; scope entries consistent with decision
  `artifacts`.
On failure: recovery R3 (orchestrator builds a fallback plan) — never dispatch Modernizers
against a structurally invalid plan.
