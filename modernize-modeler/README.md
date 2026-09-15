# Modernize Modeler — Multi-Agent Orchestration Skill

The downstream companion of the **codebase-modeler** skill. Where codebase-modeler turns a
repository into six line-traceable architecture artifacts, modernize-modeler takes that
run's output and rewrites it into a **modernized** set of the same six artifacts:

| Artifact | Template | What modernization changes |
|---|---|---|
| `Specification.md` | `templates/Specification.md` | target stack, NFRs, testing & deployment strategy |
| `ClassModel.md` | `templates/ClassModel.md` | modern framework/ORM layering, typed DTOs, new services |
| `DatabaseModel.md` | `templates/DatabaseModel.md` | modern DBMS/ORM/migrations, schema hardening |
| `DomainModel.md` | `templates/DomainModel.md` | mostly kept (business semantics), modern event/service patterns |
| `UseCaseModel.md` | `templates/UseCaseModel.md` | mostly kept; error flows modernized (typed errors, status codes) |
| `ActivityDiagram.md` | `templates/ActivityDiagram.md` | flows re-drawn for the modern runtime (async, workers, new services) |

**Where they land:** `modernized/<repo-name>/` — same filenames, same template structure,
modernized content. Nothing in `output/` is touched.

## What makes it different from "rewrite the docs"

1. **A binding plan.** Before any writing, a Modernization Planner agent produces
   `modernization-plan.json`: the current→target stack, one `M-n` decision per change
   (real package names, concrete versions, rationale), the kept elements (`K-n`), and a
   **ledger that closes every `UNVERIFIED` assumption and every flagged issue** from the
   source run — each `resolved` (by a decision), `accepted` (reason), or `deferred`
   (reason). A modernized artifact may not contain an open `UNVERIFIED` marker: the whole
   point is that the old unknowns are now decided.
2. **Your directives are enforced.** Pass free text — "keep Python; Flask -> FastAPI;
   PostgreSQL; add pytest and CI; no frontend needed" — and every clause is parsed into a
   `D-n` directive item. The plan must implement each one (or explicitly defer it with a
   reason); the Critics audit per-document compliance and the Semantic Verifier sweeps the
   whole set. A silently dropped request is a plan defect.
3. **Three-way traceability.** Every element in a modernized document carries:
   - a **legacy citation** (`routes/notes.py:9-15`) for what the code *was*,
   - a **source-artifact citation** (`Specification.md:33`) for the claim being transformed,
   - a **plan reference** (`(M-3)`) for the decision that changed it.
   Tables gain a `Modernization` column (`kept` / `M-n` / `added (M-n)` / `replaced (M-n)`).
4. **Mechanical verification.** `scripts/verify.py` re-checks the modernization contract
   end to end: template sections, plan references (every `M/A/I/D/K-n` must exist in the
   plan), citations (legacy against the pinned `.repo`, source-artifact against the source
   output), Mermaid + node maps, no open `UNVERIFIED`, and the plan's own ledger coverage.

## How it works: the agent network

```
              +----------------+
 Phase 0     |    intake      |  (host, deterministic: intake.py)
             +-------+--------+
                     |
 Phase 1     +-------v--------+
             | modernization  |  1 agent -> modernization-plan.json
             | planner        |
             +-------+--------+
                     |
 Phase 2     +-------v--------+
             |  modernizers   |  6 agents in parallel (one per doc)
             +-------+--------+
                     |
 Phase 3     +-------v--------+     +---------------+
             | critic <->     | <-> |  up to 3 rounds |
             | fixer debate   |     |  (1 in lite)    |
             +-------+--------+     +---------------+
                     |
 Phase 4     +-------v--------+
             |  verifier      |  verify.py (mechanical) + 1 semantic agent
             +-------+--------+
                     |
 Phase 5     +-------v--------+
             |  deliver       |  SUMMARY.md + final report
             +----------------+
```

The orchestration mechanics (flat staged dispatch, file hand-offs, critic-fixer
adjudication, recovery policies R1–R7 including plan-conflict escalation) mirror the
codebase-modeler skill; see `SKILL.md` for the full playbook.

## Usage

Run codebase-modeler first, then:

```
/modernize-modeler output/notes-app
```

With directives and options (order: source, then any mix of mode / dirs / directives):

```
/modernize-modeler output/notes-app full "keep Python; Flask -> FastAPI; PostgreSQL; add pytest and CI"
```

- **`<source>`** — the codebase-modeler output directory (a bare repo name works when
  `output/<name>/` exists).
- **`directives`** — optional free text; any non-flag argument is treated as directives.
  Without it, the default policy applies (keep language + business semantics, modernize
  stack/approaches, close every flagged issue).
- **`[full|lite]`** — `full` (default): 3 critic-fixer rounds. `lite`: 1 round.
- **`[templates_dir]`** — default `templates/`.
- **`[out_root]`** — default `modernized/`.

### Output layout

```
modernized/<REPO_NAME>/
├── intake.json                      # what inputs were available + UNVERIFIED counts
├── modernization-plan.json          # decisions M-n, directives D-n, kept K-n,
│                                    # assumptions A-n, issues I-n, per-doc scopes
├── DatabaseModel.md  ClassModel.md  DomainModel.md
├── UseCaseModel.md   ActivityDiagram.md  Specification.md
├── critique/<doc>-r<r>.json  <doc>-r<r>-fixer.json
├── verification/report.json  verification-report.md
└── SUMMARY.md                     # scorecard + orchestration log + verdicts
```

### Verifying the results yourself

```sh
python3 scripts/verify.py modernized/<REPO_NAME> output/<REPO_NAME>
```

Exit `0` = every document PASS (and the plan ledger is covered); exit `1` = at least one
FAIL, with the defect list in `verification/report.json` / `verification-report.md`.
If the source run's `.repo` clone is gone, legacy citations are reported as *skipped*
(docs-only mode) instead of failing — everything else is still checked.

### Viewing

The bundled `viewer/` + `server.py` serve `output/`. To browse modernized artifacts with
the same viewer, link the run into place, e.g. `ln -s ../../modernized/notes-app
output/notes-app-modernized` (or point the server's `OUTPUT_DIR` at `modernized/`).

### Self-test

```sh
bash scripts/selftest.sh
```

It exercises the deterministic contract end to end against the bundled fixtures: intake
accepts a complete source output and rejects one with a missing artifact; verify PASSes on
the hand-written modernized fixture; verify **FAILs** on an unknown plan reference
(`M-99`) and on a broken legacy citation; and verify runs in docs-only mode (no repo) with
legacy citations skipped.

## What is and is not automated

- **Automated and self-tested:** intake validation, plan-ledger coverage, reference/citation
  resolution, section/diagram/node-map checks, docs-only mode, self-test suite.
- **Not covered by the self-test:** the LLM phases (planner, modernizers, critics, fixer,
  semantic verifier) — running them needs a real codebase-modeler output and sub-agent
  dispatch by the host.
- **Honesty:** modernization targets are the plan's decisions, not the verifier's opinion.
  If a decision names a wrong or non-existent package, the Critics flag it as
  `modern_claim` — but the mechanical verifier cannot know the future of any framework.

## Installation

Copy (or symlink) this `modernize-modeler/` folder into your skills directory, alongside
`codebase-modeler/`:

```sh
cp -r modernize-modeler ~/.agents/skills/        # Kimi Code (user scope)
cp -r modernize-modeler .claude/skills/          # Claude Code (project scope)
```

Python 3 standard library only; no third-party packages.
