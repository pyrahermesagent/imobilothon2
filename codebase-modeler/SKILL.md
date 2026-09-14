---
name: codebase-modeler
description: Multi-agent orchestration that turns a GitHub URL (or local path) into six line-traceable architecture artifacts - Activity Diagram, Class Model, Database Model, Domain Model, Use Case Model and a full Program Specification - written strictly to the project templates, with a critic-fixer verification loop and mechanical reference verification.
whenToUse: When the user provides a GitHub URL or local repository path and asks for architecture models, UML diagrams, class/domain/database/use-case models, activity diagrams, or a program specification generated from source code.
arguments:
  - repo
  - mode
  - templates_dir
  - out_dir
---

# Codebase Modeler - Multi-Agent Orchestration Network

You are the **Orchestrator**. Do NOT do the analysis, writing, or critique work yourself.
Your job is to run a network of specialized micro-agents (Planner, five Analysts, six Writers,
Critics, a Fixer, and a Tester), hand off their work through files on disk, and enforce a
verification loop until the artifacts pass - or to honestly report what is unresolved.

SKILL_DIR = the directory containing this SKILL.md (in Kimi Code, `${KIMI_SKILL_DIR}` expands to it;
in Claude Code, use the skill's base directory; in other hosts, the folder this file lives in).

## 0. Inputs

- `$repo` (or `$0` / `$ARGUMENTS` if named args were not supplied): a GitHub URL
  (`https://github.com/<owner>/<name>[.git]`) or a local path to a git repository.
- `$mode`: `full` (default) or `lite`. Lite = single writer batch, 1 critique round, for small repos (< ~15k LOC).
- `$templates_dir`: where the six templates live. Default: `templates/` in the project root.
  Required files: `ActivityDiagram.md`, `ClassModel.md`, `DatabaseModel.md`, `DomainModel.md`,
  `Specification.md`, `UseCaseModel.md`. **If any is missing, STOP and tell the user which file is missing.**
- `$out_dir`: output root. Default: `output/` in the project root.
- If no repo was given, ask the user for the GitHub URL before doing anything else.

Derived values (compute once, reuse everywhere):

```
REPO_NAME  = <name> from the URL (strip .git) or basename of the local path
OUT        = <out_dir>/<REPO_NAME>
REPO       = <OUT>/.repo          (the cloned working copy)
TPL        = <templates_dir>
MAX_ROUNDS = 3 (full) | 1 (lite)
```

## 1. Traceability Contract (applies to EVERY artifact)

This is the single most important rule of the skill. Every agent prompt you send restates it:

1. **Citation format:** `` `rel/path/to/file.ext:42` `` or `` `rel/path/to/file.ext:42-58` `` -
   path relative to the repo root, 1-based line numbers, backticks in prose and tables.
   Inside Mermaid node labels (no backticks allowed) the same form appears bare.
2. **Every modeled element carries at least one citation**: every class, attribute, method,
   interface, DTO, table, column, constraint, index, FK, entity, value object, aggregate,
   invariant, business rule, domain event, domain service, actor, use case (and every step of
   its main/alternative/exception flows), activity node, decision guard, swimlane assignment,
   tech-stack claim, and API endpoint.
3. **Citations point at the pinned commit.** Never cite memory, docs, or "typical practice".
   If something cannot be verified in the code, mark it `UNVERIFIED` with a one-line rationale
   and collect it in the document's `Assumptions & Unverified Items` section. Never invent.
4. **Mermaid diagrams are verified via node maps.** Every Mermaid block is followed by a
   `| Node | Element | Code Reference |` table mapping each node id to its code citation.
5. **Verification is mechanical:** `scripts/verify.py` (SKILL_DIR) re-checks every citation
   against the actual cloned files. A document with an unresolvable citation is FAILED.

## 2. Phase 0 - Intake (deterministic, you do this directly)

1. `mkdir -p $OUT`
2. Clone (error recovery R1):
   - `git clone --depth 1 --single-branch <repo> $REPO`
   - On failure retry with a plain `git clone <repo> $REPO`.
   - On failure for a GitHub URL try the tarball: `curl -sL <url-with-.git→.tar.gz> | tar xz -C $OUT && mv <name> $REPO` (create a pseudo-root; note in SUMMARY that no git metadata exists).
   - Still failing (404, private, network): STOP, show the raw error, ask the user (auth? correct URL?).
3. Pin the commit: `REPO_SHA = git -C $REPO rev-parse HEAD` (or `n/a (tarball)`). All citations are against this tree.
4. Run inventory: `python3 <SKILL_DIR>/scripts/inventory.py $REPO $OUT`
   - Exit 0 → continue. Exit 2 → bad path (R1). Exit 3 → no source files found: STOP and tell the user the repo looks empty/non-source.
   - Produces `$OUT/inventory.json` + `$OUT/inventory.md`.
5. Confirm `git -C $REPO` working tree is clean enough to cite from; record total LOC from `inventory.md`.

## 3. The Orchestration Network

```
  Phase 0        Phase 1          Phase 2 (parallel x5)         Phase 3 (parallel x6)
+----------+     +---------+      +---+ +---+ +----+ +----+ +---+   +---+ +---+ +---+ +---+ +---+ +---+
| INTAKE   | --> | PLANNER | --> |DBA| |CA | |FA  | |UCA | |DA | --> |W | |W | |W | |W | |W | |W |
| (script) |     | (plan)  |     |   | |   | |    | |    | |   |     |DB| |CL| |DO| |UC| |AC| |SP |
+----------+     +---------+      +---+ +---+ +----+ +----+ +---+   +---+ +---+ +---+ +---+ +---+ +---+
                                                                                          |
                    +-----------------------------------------------+                    v
                    |                                                 |            +-----------------+
                    v                                                 |            | PHASE 4 (xN    |
              +------------+     +---------+     +---------+         +----------> | CRITIC <-> FIXER|
              | PHASE 5    | <--- | PHASE 6 |     |  CRITICS|   (hand:              | debate loop,   |
              | TESTER     |     | DELIVER |     | (x6 par)|   defect               | up to 3 rounds)|
              | (script +  |     | (you)   |     +---------+   files)               +-----------------+
              | semantic)  |     +---------+
              +------------+
                    |
                 pass -> Phase 6
                    fail -> Fixer (targeted) -> back to Phase 5 (max 2 loops)
```

**Dispatch rules (all hosts):**
- YOU are the only dispatcher. Sub-agents cannot spawn sub-agents (Kimi Code: built-ins never
  dispatch further; Claude Code: Tasks don't nest). The network is **flat and staged**;
  "communication" between agents is strictly through the hand-off files in `$OUT`.
- Dispatch = one `Agent`/`Task` call per agent, with a **fully self-contained prompt**:
  read the role template from `<SKILL_DIR>/agents/<file>.md`, fill its `{{placeholders}}`,
  and send the whole thing as the sub-agent's task. Sub-agents start with ZERO context -
  the template is their entire brief.
- Where a phase says "parallel", issue all dispatches in a single turn (multiple Agent calls
  in one response). Do not poll; you are notified on completion.
- Sub-agent type mapping (see §6 Host mapping for other hosts):
  Planner → `plan`-style (read-only); Analysts/Writers/Fixer → `coder`-style (must write files);
  Critics/semantic Tester → `explore`-style (must NOT modify artifacts; they return findings as text).

### Phase 1 - Planner (1 agent, role template `agents/01-planner.md`)

Placeholder fill: `{{REPO}} {{OUT}} {{REPO_SHA}} {{TPL}} {{MODE}}`.
Output: `$OUT/plan.json` (schema in `references/plan-schema.md`). You MUST validate it:
parse it, confirm every analyst `scope` is non-empty, ≤ 60 files and ≤ 25k lines (sum of cited
file sizes from `inventory.json`), and `top_processes`/`top_use_cases` each list 3-8 candidates.
If invalid → recovery R3 (fallback plan from inventory buckets).

### Phase 2 - Analyst swarm (5 agents in parallel, role templates `agents/02-*`)

One per model: `02-db-analyst`, `02-class-analyst`, `02-flow-analyst`, `02-usecase-analyst`,
`02-domain-analyst`. Fill: `{{REPO}} {{OUT}} {{SCOPE}}` (from plan.json) `{{REPO_SHA}}`.
Each writes exactly one evidence file `$OUT/evidence/<model>.json`
(schema in `references/evidence-schema.md`) and returns a ≤15-line summary.
Constraints restated in every analyst prompt: read-only on the repo; write only under `$OUT/evidence/`;
every element ≥1 citation; `UNVERIFIED` where the code doesn't answer.
Failure/timeout of one analyst → R2 (re-dispatch once with the same prompt + "a previous attempt
failed partway; resume from the evidence file if it exists"). If it fails again, split its scope in
half and dispatch two analysts; if still failing, mark that model `PARTIAL` and continue - never
silently drop a model.

### Phase 3 - Writers (6 agents in parallel, role template `agents/03-writer.md`)

One writer per artifact: `DB → DatabaseModel.md`, `CL → ClassModel.md`, `DO → DomainModel.md`,
`UC → UseCaseModel.md`, `AC → ActivityDiagram.md`, `SP → Specification.md`.
Fill: `{{DOC}} {{TEMPLATE}}` (path in TPL) `{{EVIDENCE}}` (all evidence files; the Specification
writer gets all six + `plan.json` + `inventory.md`) `{{REPO}} {{OUT}} {{REPO_SHA}}`.
Each writer reads its template and produces `$OUT/<DOC>` structurally mirroring it (same section
order and headings, adapted to this codebase), every value cited per the Traceability Contract.
The Specification writer additionally cross-links the other five documents.

### Phase 4 - Critic-Fixer debate loop (rounds r = 1..MAX_ROUNDS)

For each artifact with open defects (initially: all six), in parallel:
1. Dispatch a Critic (`agents/04-critic.md`, fill `{{DOC}} {{TEMPLATE}} {{ROUND}} {{REPO}} {{OUT}}`).
   The critic VERIFIES by reading the actual cited lines: for a sample of ≥30% of citations (all if
   fewer) it opens the file at the line and checks the claim matches; checks template completeness;
   checks node maps; checks semantics (no orphan elements, layers consistent).
   It returns a defect list (JSON, ≤25 items, each with `severity: major|minor`, `location`,
   `claim`, `problem`, `evidence` (quoted file lines), `fix_instruction`). You write it to
   `$OUT/critique/<doc>-r<r>.json`.
2. Defects with `severity: major` → dispatch a Fixer (`agents/05-fixer.md`, fill `{{DOC}}`
   `{{DEFECTS}}` `{{ROUND}}`). The fixer edits ONLY `$OUT/<DOC>`, and for every defect returns a
   verdict: `fixed` (with what changed) or `refuted` (with counter-evidence quoting code lines).
   You append the verdicts to `$OUT/critique/<doc>-r<r>-fixer.json`.
3. `refuted` majors go back to the same doc's Critic for one adjudication (round r+1 critic prompt
   includes "these defects were refuted by the fixer with this evidence: ... - confirm or stand down").
   A critic may not keep a defect alive past adjudication; survivors move to Unresolved.
4. `minor` defects: fixed in the final round only (no re-critique), verdicts logged.
Loop exits when a doc has zero open majors, or after MAX_ROUNDS.

### Phase 5 - Tester (deterministic + semantic)

1. Mechanical tester: `python3 <SKILL_DIR>/scripts/verify.py $OUT $REPO`
   → `$OUT/verification/report.json` + `$OUT/verification/verification-report.md`.
   Exit 0 = all citations resolve, all required template sections present, Mermaid blocks well-formed.
   Exit 1 = hard failures (unresolved citations, missing sections, broken Mermaid).
2. On exit 1 → dispatch a targeted Fixer with the exact failure list from `report.json`
   (`agents/05-fixer.md`, `{{DEFECTS}}` = the failing citation/section list). Re-run verify.
   Max 2 such loops. Never end Phase 5 while verify exits 1 without reporting the failures.
3. Semantic tester (1 agent, `agents/06-verifier.md`): cross-document consistency - entity sets
   consistent across DB/Domain/Spec, actors consistent across UC/Activity/Spec, use cases ↔ activity
   processes ↔ spec features aligned, naming consistent. Returns advisory findings (JSON); you append
   them to `$OUT/verification/verification-report.md` under `## Semantic Findings (advisory)`.
   Advisory findings never block delivery, but they must appear in the final report.

### Phase 6 - Deliver (you do this directly)

1. Write `$OUT/SUMMARY.md`:
   - Inputs (URL, MODE, TPL, REPO_SHA), dates
   - Orchestration log: every dispatch (role, phase, round, outcome, duration if known)
   - Defect ledger per doc: found / fixed / refuted / unresolved (with ids)
   - Verification verdict per doc: PASS / PASS WITH ADVISORIES / FAILED (list)
   - PARTIAL/UNVERIFIED roll-up
2. Final message to the user: table of the six artifacts + their verdicts, the path to
   `$OUT`, how to re-verify (`python3 <SKILL_DIR>/scripts/verify.py $OUT $REPO`), and any
   unresolved items. If any doc is FAILED or PARTIAL, say so plainly and what would be needed
   to close it. **Never present an unverified artifact as verified.**

## 4. Recovery Policies

- **R1 Clone failure:** retry ladder in Phase 0; if auth/404, stop and ask.
- **R2 Agent failure/timeout:** one re-dispatch with resume note; then scope split (analysts) or
  mark artifact `PARTIAL` (writers). Log in SUMMARY.
- **R3 Bad plan:** build a fallback plan.json yourself from `inventory.json` buckets
  (db → db-analyst scope, etc.), log that the planner failed and why.
- **R4 Loop exhaustion:** remaining majors → `## Unresolved Findings` in the verification report
  + doc verdict `FAILED` or `PARTIAL`. Deliver the rest. State exactly what remains and why.
- **R5 Context loss (long run):** re-read `$OUT/plan.json`, `evidence/`, `critique/`,
  `verification/report.json` to reconstruct state; the disk IS the memory of the network.

## 5. Output Contract

```
$OUT/
├── .repo/                      # pinned clone (citations resolve against this tree)
├── inventory.md  inventory.json
├── plan.json
├── evidence/{db,classes,flows,usecases,domain}.json
├── DatabaseModel.md  ClassModel.md  DomainModel.md
├── UseCaseModel.md   ActivityDiagram.md  Specification.md
├── critique/<doc>-r<r>.json  <doc>-r<r>-fixer.json
├── verification/report.json  verification-report.md
└── SUMMARY.md
```

## 6. Host Mapping

| Host          | Dispatch primitive                          | Notes |
|---------------|---------------------------------------------|-------|
| Kimi Code     | `Agent` tool (`subagent_type`: explore/coder/plan) | Optional host-native custom agent files can harden the critic to read-only (not bundled; see README) |
| Claude Code   | `Task` tool with a general-purpose subagent | The role template IS the task prompt; keep it self-contained |
| Hermes / other| Any sub-agent/Task primitive                 | If none exists: **degraded inline mode** - run each role in sequence in your own context, reading the role template before each phase. Same contracts, same files, slower. Say in the final message that inline mode was used. |

## 7. Supporting Files (SKILL_DIR)

- `agents/01-planner.md` ... `agents/06-verifier.md` - role prompts (read + fill + dispatch)
- `scripts/inventory.py` - repo inventory (Phase 0)
- `scripts/verify.py` - mechanical citation/section/mermaid verification (Phase 5)
- `references/plan-schema.md`, `references/evidence-schema.md` - hand-off file schemas
- `tests/` - fixture repo + hand-verified passing outputs; `scripts/selftest.sh` runs the whole contract
- `README.md` - full usage guide

Note: role prompts in `agents/` are self-contained; they do not depend on any
extra files. Hosts that support custom agent definitions (e.g. Kimi Code
`custom-agents/`) can optionally add thin role files there for hard tool
boundaries (read-only critic), but nothing in this skill requires them.
