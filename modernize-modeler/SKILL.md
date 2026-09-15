---
name: modernize-modeler
description: Multi-agent orchestration that takes the six line-traceable artifacts produced by the codebase-modeler skill and rewrites them into a modernized set under ./modernized/<repo-name> - same template structure, updated to modern packages and approaches, with every UNVERIFIED assumption and flagged issue from the source run resolved, accepted, or explicitly deferred, and every change traced to a modernization decision (M-n) in a plan the user's keep/change directives bind.
whenToUse: When the user wants to modernize a codebase-modeler output (the six architecture models / specification), update the tech stack or packages of the modeled system, or close the assumptions and issues the modeling run flagged - optionally with free-text directives naming languages, techstacks, or features to keep or change.
arguments:
  - source
  - directives
  - mode
  - templates_dir
  - out_root
---

# Modernize Modeler - Multi-Agent Orchestration Network

You are the **Orchestrator**. Do NOT do the planning, writing, or critique work yourself.
Your job is to run a network of specialized micro-agents (a Modernization Planner, six
Modernizer writers, Critics, a Fixer, and a Semantic Verifier), hand off their work through
files on disk, and enforce a verification loop until the modernized artifacts pass - or to
honestly report what is unresolved.

SKILL_DIR = the directory containing this SKILL.md (in Kimi Code, `${KIMI_SKILL_DIR}` expands
to it; in Claude Code, use the skill's base directory; in other hosts, the folder this file
lives in).

## 0. Inputs

- `$source` (or `$0` / first token of `$ARGUMENTS`): the codebase-modeler output directory
  to modernize, e.g. `output/notes-app` (must contain the six artifacts). A bare repo name
  is accepted when `output/<name>/` exists.
- `$directives`: the user's free-text modernization instructions - which languages,
  techstacks, and functionalities to KEEP or CHANGE (e.g. "keep Python; Flask -> FastAPI;
  PostgreSQL; add pytest and CI; no frontend needed"). **Optional.** When absent, the
  DEFAULT POLICY applies and must be used as the directive text everywhere:
  > "Default policy (no user directives provided): keep the primary programming language
  > and the business semantics (entities, actors, use cases); modernize the framework,
  > libraries, data access, error handling, security, testing, and deployment to current
  > best practice; resolve every issue and assumption flagged by the codebase-modeler
  > output."
- `$mode`: `full` (default) or `lite`. Lite = 1 critic-fixer round, for small source runs.
- `$templates_dir`: where the six templates live. Default: `templates/` in the project root.
  Required files: `ActivityDiagram.md`, `ClassModel.md`, `DatabaseModel.md`, `DomainModel.md`,
  `Specification.md`, `UseCaseModel.md`. **If any is missing, STOP and tell the user which
  file is missing.**
- `$out_root`: output root. Default: `modernized/` in the project root.

**Argument parsing (do this first, then act):**
1. `SRC` = the first argument. It is an existing directory, or a name for which
   `output/<name>/` exists. Neither exists → STOP and ask the user for the path to the
   codebase-modeler output.
2. Walk the remaining arguments in order: `full`/`lite` → MODE; an existing directory →
   TEMPLATES_DIR (if still unset), else OUT_ROOT; text after a `directives:` prefix, or any
   other non-empty text → append to DIRECTIVES. Defaults: MODE=`full`,
   TEMPLATES_DIR=`templates/`, OUT_ROOT=`modernized/`.

Derived values (compute once, reuse everywhere):

```
REPO_NAME  = basename of SRC          (e.g. notes-app)
MOD        = <out_root>/<REPO_NAME>   (e.g. modernized/notes-app)
TPL        = <templates_dir>
REPO       = <SRC>/.repo if that directory exists, else n/a
REPO_SHA   = git -C $REPO rev-parse HEAD (or "n/a (no .repo)")
MODE       = full | lite
MAX_ROUNDS = 3 (full) | 1 (lite)
```

## 1. The Modernization Traceability Contract (applies to EVERY artifact)

The codebase-modeler contract (citations to code) is extended, not replaced. Every agent
prompt you send restates it:

1. **Legacy citations** `` `rel/path/to/file.ext:42` `` / `` `rel/path:42-58` `` - point at
   the pinned legacy code (`REPO`) and document the "was" state. Same format and rules as
   codebase-modeler (backticked in prose/tables; bare inside Mermaid labels; node maps after
   every Mermaid block).
2. **Source-artifact citations** `` `Specification.md:33` `` - point at a line in the
   codebase-modeler output under `SRC`; used when transforming a claim the legacy run made.
3. **Plan references** `M-n` (decision), `A-n` (assumption), `I-n` (issue), `D-n` (user
   directive), `K-n` (kept element) - point at entries in `$MOD/modernization-plan.json`,
   the single source of truth for every modernization decision and every closed ledger item.
4. **No open unknowns.** A modernized artifact must contain no `UNVERIFIED` marker outside
   its `Resolved Assumptions & Issues` section: every assumption/issue the source run left
   open is `resolved` (by a decision), `accepted` (reason), or `deferred` (reason).
5. **Directives are binding.** User `keep` items survive as-is; `change`/`add` items are
   applied exactly as the plan's decisions implement them. Contradicting a directive is a
   major defect, not a taste call.
6. **Verification is mechanical:** `scripts/verify.py` (SKILL_DIR) re-checks sections,
   references, citations, Mermaid, node maps, and the plan ledger. A document with an
   unresolvable reference/citation is FAILED.

## 2. Phase 0 - Intake (deterministic, you do this directly)

1. Parse arguments per §0. If `SRC` or a template is missing: STOP, show what is missing,
   ask the user.
2. `mkdir -p $MOD` and run:
   `python3 <SKILL_DIR>/scripts/intake.py $SRC $MOD $TPL`
   - Exit 0 → continue; read `$MOD/intake.json` (inputs available, UNVERIFIED counts).
   - Exit 2 → show the missing-file list and STOP.
   - `REPO` absent (no `.repo`) → **docs-only mode**: the six source artifacts are the
     ground truth; legacy citations in the output are still written (from the source
     artifacts) but are mechanically SKIPPED in verification. Note this in the final
     SUMMARY and message. Never fake a sha.
3. Confirm `$TPL` contains all six templates (intake already checked).

## 3. The Orchestration Network

```
  Phase 0         Phase 1            Phase 2 (parallel x6)          Phase 3 (per doc, rounds)
+----------+     +-------------+     +---+ +---+ +---+ +---+ +---+ +---+   +-----------------+
| INTAKE   | --> | MODERNIZ.   | --> |W | |W | |W | |W | |W | |W | |W |   | CRITIC <-> FIXER |
| (script) |     | PLANNER     |     |SP| |CL| |DB| |DO| |UC| |AC| |    |   | debate loop      |
+----------+     +-------------+     +---+ +---+ +---+ +---+ +---+ +---+ +---+   | up to 3 rds |
                                                                                   +-----------------+
     |                                                                              |
     |        +-----------------------------------------------+                    v
     |        v                                                 +----------> +-----------------+
     +----> | PHASE 4 (xN docs): verify.py mechanical  <------- |            | PHASE 5         |
            | on exit 1 -> targeted Fixer, max 2 loops |         |            | SEMANTIC VERIF  |
            +-----------------------------------------------+                    | (advisory)   |
                                                                                   +---------+---------+
                                                                                         |
                                                              pass -> Phase 6 (DELIVER: SUMMARY.md + final message)
```

**Dispatch rules (all hosts):**
- YOU are the only dispatcher. Sub-agents cannot spawn sub-agents. The network is **flat and
  staged**; "communication" between agents is strictly through the hand-off files in `$MOD`
  (and the read-only inputs `SRC`/`REPO`).
- Dispatch = one `Agent`/`Task` call per agent, with a **fully self-contained prompt**:
  read the role template from `<SKILL_DIR>/agents/<file>.md`, fill its `{{placeholders}}`,
  and send the whole thing as the sub-agent's task. Sub-agents start with ZERO context.
- Where a phase says "parallel", issue all dispatches in a single turn. Do not poll.
- Sub-agent type mapping (see §7 Host mapping):
  Planner/Modernizers/Fixer → `coder`-style (must write files); Critics/Semantic Verifier →
  `explore`-style (must NOT modify artifacts; they return findings as text). If the host's
  plan-type agent can write exactly one file, it may serve as Planner; otherwise use
  coder-style and rely on the template's single-file constraint.

### Phase 1 - Modernization Planner (1 agent, role template `agents/01-modernization-planner.md`)

Placeholder fill: `{{SRC}} {{OUT}} {{REPO}} {{REPO_SHA}} {{DIRECTIVES}} {{SCHEMA}}`
(`{{OUT}}` = `$MOD`; `{{SCHEMA}}` = `<SKILL_DIR>/references/modernization-plan-schema.md`;
`{{DIRECTIVES}}` = the user's text or the DEFAULT POLICY from §0).
Output: `$MOD/modernization-plan.json`. You MUST validate it before dispatching writers:
- parses as JSON; top-level keys `source`, `directives`, `stack`, `decisions`, `kept`,
  `assumptions`, `issues`, `artifact_scopes` all present;
- every decision: `M-n` id, non-empty `summary`, ≥ 1 citation, non-empty `why`,
  `artifacts` ⊆ the six artifact names;
- every directive item covered (decision refs, or deferred/kept_unchanged with a reason);
- every assumption/issue has a terminal status (`resolved` + decision refs, or
  `accepted`/`deferred` + reason);
- ledger coverage: ≥ 1 entry per source artifact whose `unverified_counts` (intake.json)
  is > 0; `artifact_scopes` lists all six artifacts.
If invalid → recovery R3 (fallback plan). If the planner returns `failed` twice → R3.

### Phase 2 - Modernizer writers (6 agents in parallel, role template `agents/02-modernizer.md`)

One writer per artifact: `SP → Specification.md`, `CL → ClassModel.md`, `DB →
DatabaseModel.md`, `DO → DomainModel.md`, `UC → UseCaseModel.md`, `AC → ActivityDiagram.md`.
Fill: `{{DOC}}` (= `$MOD/<name>`) `{{DOC_NAME}}` `{{TEMPLATE}}` (path in TPL)
`{{SRC_DOC}}` (= `$SRC/<name>`) `{{PLAN}}` (= `$MOD/modernization-plan.json`) `{{REPO}}`
`{{REPO_SHA}}` `{{OUT}}` `{{SRC}}` `{{DIRECTIVES}}`.
Each writer reads its template + source artifact + plan and produces `$MOD/<DOC>` mirroring
the template, with a Modernization column in every table, Mermaid + node maps, the
modernization header block, and the two honesty sections.
**plan_gaps:** collect `plan_gaps` from all returns. If any are non-empty → R7 (single
planner re-dispatch with the gaps; then re-dispatch only the writers whose gaps changed
their scope). Failure/timeout of a writer → R2 (re-dispatch once; then mark `PARTIAL`).

### Phase 3 - Critic-Fixer debate loop (rounds r = 1..MAX_ROUNDS)

For each artifact with open defects (initially: all six), in parallel:
1. Dispatch a Critic (`agents/03-critic.md`, fill `{{DOC}} {{DOC_NAME}} {{TEMPLATE}}
   {{PLAN}} {{SRC}} {{REPO}} {{REPO_SHA}} {{DIRECTIVES}} {{ROUND}} {{REFUTED}}`). The
   critic verifies by reading actual lines: sample ≥ 30% of citations (all if fewer),
   checks every plan reference, directive compliance, ledger closure, modern-claim
   soundness, node maps, Mermaid, semantics. It returns a defect list (JSON, ≤ 25 items);
   you write it to `$MOD/critique/<doc>-r<r>.json`.
2. Defects with `severity: major` → dispatch a Fixer (`agents/04-fixer.md`, fill `{{DOC}}`
   `{{TEMPLATE}} {{PLAN}} {{SRC}} {{REPO}} {{REPO_SHA}} {{DEFECTS}} {{ROUND}}`). The fixer
   edits ONLY `$MOD/<DOC>` and returns a verdict per defect: `fixed` / `refuted`
   (counter-evidence) / `unresolvable` (category `plan_conflict` when only a plan change
   would fix it). You append verdicts to `$MOD/critique/<doc>-r<r>-fixer.json`.
3. `refuted` majors go back to the same doc's Critic for one adjudication (round r+1 prompt
   carries the refutation evidence - confirm or stand down). Survivors move to Unresolved.
4. `unresolvable` with `plan_conflict` → R6. `minor` defects: fixed in the final round only,
   verdicts logged.
Loop exits when a doc has zero open majors, or after MAX_ROUNDS.

### Phase 4 - Tester (deterministic + semantic)

1. Mechanical tester: `python3 <SKILL_DIR>/scripts/verify.py $MOD $SRC`
   (add `$REPO` as a third argument when it exists - otherwise verify auto-detects or skips).
   → `$MOD/verification/report.json` + `verification-report.md`.
   Exit 0 = every document PASSes (sections, references, citations, Mermaid, node maps,
   plan ledger). Exit 1 = hard failures.
2. On exit 1 → dispatch a targeted Fixer with the exact failure list from `report.json`
   (`{{DEFECTS}}` = the failing citation/reference/section list). Re-run verify. Max 2 such
   loops. Never end Phase 4 while verify exits 1 without reporting the failures.
3. Semantic tester (1 agent, `agents/05-semantic-verifier.md`, fill `{{OUT}} {{SRC}}
   {{REPO}} {{DIRECTIVES}}`): cross-document coherence of the MODERN target - stack
   consistency, decision fidelity, buildability, kept fidelity, ledger closure, directive
   sweep, alignment, citation hygiene. Returns advisory findings (JSON); append them to
   `$MOD/verification/verification-report.md` under `## Semantic Findings (advisory)`.
   Advisory findings never block delivery, but they must appear in the final report.

### Phase 5 - Deliver (you do this directly)

1. Write `$MOD/SUMMARY.md`:
   - Inputs (SRC, REPO_SHA, MODE, TPL, DIRECTIVES verbatim or "default policy"), dates
   - Orchestration log: every dispatch (role, phase, round, outcome, duration if known)
   - **Modernization scorecard**: decisions applied (count, M-ids), elements kept,
     assumptions resolved/accepted/deferred (counts + ids), issues resolved/accepted/
     deferred (counts + ids), directives coverage (each D-id → status)
   - Defect ledger per doc: found / fixed / refuted / unresolved (with ids)
   - Verification verdict per doc: PASS / PASS WITH ADVISORIES / FAILED (list)
   - docs-only mode note if `REPO` was unavailable; PARTIAL/deferred roll-up
2. Final message to the user: table of the six artifacts + verdicts, the scorecard, the
   path to `$MOD`, how to re-verify
   (`python3 <SKILL_DIR>/scripts/verify.py $MOD $SRC`), and any unresolved items. If any doc
   is FAILED or PARTIAL, say so plainly and what would be needed to close it.
   **Never present an unverified artifact as verified.**

## 4. Recovery Policies

- **R1 Intake failure:** missing source artifact or template → STOP with the exact list.
  Missing `.repo` → docs-only mode (not a failure): say so in SUMMARY and the final message.
- **R2 Agent failure/timeout:** one re-dispatch with a "previous attempt failed partway;
  resume" note; writers still failing → mark artifact `PARTIAL` and continue. Log in SUMMARY.
- **R3 Bad/failed plan:** build a fallback `modernization-plan.json` yourself: parse the
  directives into D-n items (kind by keyword: keep/retain→keep, change/replace/use/->
  →change, add/introduce→add, drop/skip/ignore→defer); stack from the source
  Specification §3 with source-artifact citations; one decision per change/add directive
  (concrete target, citations from the source artifact); ledger from `grep -n UNVERIFIED`
  over the six source artifacts - every marker becomes an A-n with `deferred` +
  "planner unavailable; needs manual review"; `artifact_scopes`: all docs get all
  decisions. Log that the planner failed and why.
- **R4 Loop exhaustion:** remaining majors → `## Unresolved Findings` in the verification
  report + doc verdict `FAILED` or `PARTIAL`. Deliver the rest. State exactly what remains.
- **R5 Context loss (long run):** re-read `$MOD/intake.json`, `modernization-plan.json`,
  `critique/`, `verification/report.json` to reconstruct state; the disk IS the memory.
- **R6 Plan conflict (fixer `plan_conflict`):** re-dispatch the Planner once with the
  conflict notes ("these fixes require plan changes: ...; preserve existing ids, add or
  amend entries"); on success, re-dispatch the affected writers/fixer for the changed
  scope. If the Planner cannot resolve it → the affected doc's verdict is `PARTIAL`, the
  conflict is logged in SUMMARY, and the rest delivers.
- **R7 plan_gaps from writers:** one Planner re-dispatch carrying all reported gaps (same
  contract as R6); then re-dispatch only the writers whose scope changed.

## 5. Output Contract

```
modernized/<REPO_NAME>/
├── intake.json
├── modernization-plan.json
├── DatabaseModel.md  ClassModel.md  DomainModel.md
├── UseCaseModel.md   ActivityDiagram.md  Specification.md
├── critique/<doc>-r<r>.json  <doc>-r<r>-fixer.json
├── verification/report.json  verification-report.md
└── SUMMARY.md
```

The six artifacts mirror their templates' section order/headings, carry the modernization
header block, a `Modernization` column in every table, Mermaid + node maps, and the two
honesty sections (`Modernization Decisions (this document)`, `Resolved Assumptions &
Issues`). They intentionally share filenames with the source artifacts - that is the point:
the same templates, modernized content.

## 6. Verification semantics (what verify.py enforces)

Per document: template sections present; modernization header; honesty sections present; no
`UNVERIFIED` outside the resolved section; every M/A/I/D/K reference resolves in the plan;
every citation resolves (legacy against REPO, source-artifact against SRC; when no REPO,
unresolvable legacy spans are SKIPPED warnings, never failures); Mermaid fences/types/
swimlanes; node maps; scope floors (a doc assigned decisions/ledger entries must reference
them). Plus the plan itself: decisions/directives/ledger/scopes structurally valid and the
ledger covering every source artifact with UNVERIFIED markers.

## 7. Host Mapping

| Host          | Dispatch primitive                          | Notes |
|---------------|---------------------------------------------|-------|
| Kimi Code     | `Agent` tool (`subagent_type`: explore/coder/plan) | Planner/Modernizers/Fixer → coder; Critics/Semantic → explore |
| Claude Code   | `Task` tool with a general-purpose subagent | The role template IS the task prompt; keep it self-contained |
| Hermes / other| Any sub-agent/Task primitive                 | If none exists: **degraded inline mode** - run each role in sequence in your own context, reading the role template before each phase. Same contracts, same files, slower. Say in the final message that inline mode was used. |

## 8. Supporting Files (SKILL_DIR)

- `agents/01-modernization-planner.md` ... `agents/05-semantic-verifier.md` - role prompts
  (read + fill + dispatch)
- `scripts/intake.py` - source-output validation + intake.json (Phase 0)
- `scripts/verify.py` - mechanical reference/citation/section/mermaid/plan verification
  (Phase 4)
- `references/modernization-plan-schema.md` - the modernization-plan.json schema
- `tests/` - fixture source output + fixture repo + hand-verified passing modernized
  outputs; `scripts/selftest.sh` runs the whole deterministic contract
- `README.md` - full usage guide

Note: role prompts in `agents/` are self-contained; they do not depend on any extra files.
This skill is the downstream companion of `codebase-modeler`: it consumes its output
directory and never re-clones or re-models the repo.
