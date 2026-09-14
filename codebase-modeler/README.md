# Codebase Modeler — Multi-Agent Orchestration Skill

A skill for **Kimi Code**, **Claude Code**, and **Hermes** (or any agent host with
sub-agent dispatch) that takes a GitHub URL and produces six **line-traceable**
modeling artifacts:

| Artifact | Template | Diagram engine |
|---|---|---|
| `ActivityDiagram.md` | `templates/ActivityDiagram.md` | Mermaid `flowchart` with swimlanes |
| `ClassModel.md` | `templates/ClassModel.md` | Mermaid `classDiagram` |
| `DatabaseModel.md` | `templates/DatabaseModel.md` | Mermaid `erDiagram` |
| `DomainModel.md` | `templates/DomainModel.md` | Mermaid UML |
| `UseCaseModel.md` | `templates/UseCaseModel.md` | Mermaid `flowchart`/`graph` |
| `Specification.md` | `templates/Specification.md` | (structured text) |

Every node, edge, attribute, relationship and specification entry carries a
**code citation** like `routes/notes.py:9-15` — file path + line range inside the
cloned repo — so a human or machine can jump straight to the source and check
whether the model is correct. A deterministic verifier
(`scripts/verify.py`) re-checks every citation, section, and diagram type and
fails the artifact if anything cannot be resolved.

## How it works: the agent network

One model with one big prompt is fragile; this skill instead runs a
**specialized collective** of micro-agents (Planner / Analysts / Writers /
Critic / Fixer / Tester) that hand work off to each other through files on disk.

```
                +----------------+
   Phase 0      |   intake       |  (host, deterministic)
                | clone+inventory|
                +-------+--------+
                        |
                +-------v--------+
   Phase 1      |    planner     |  1 agent -> plan.json
                +-------+--------+
                        |
   Phase 2      +-------+--------+
                | analyst swarm  |  5 agents in parallel
                | classes, db,   |  -> evidence/{classes,db,flows,
                | flows, usecase,|     usecases,domain}.json
                | domain         |
                +-------+--------+
                        |
   Phase 3      +-------+--------+
                |    writers     |  6 agents in parallel
                | (one per doc)  |  -> the six .md artifacts
                +-------+--------+
                        |
   Phase 4      +-------+--------+     +---------------+
                | critic <-> fixer | <->|  up to 3 rounds |
                | debate loop     |     | (1 in lite)     |
                +-------+--------+     +---------------+
                        |
   Phase 5      +-------+--------+
                |  verifier       |  verify.py, mechanical
                +-------+--------+
                        |
   Phase 6      +-------+--------+
                |  deliver        |  SUMMARY.md + final report
                +-----------------+
```

**Why flat, not nested.** Sub-agents on all supported hosts cannot spawn their
own sub-agents, so the "network" is a *staged* flat dispatch: the orchestrating
model (you, the skill's reader) dispatches one batch of agents per phase, reads
the hand-off files they wrote, then dispatches the next batch. Each role prompt
in `agents/` is self-contained — an agent never needs to have seen the
conversation.

**Hand-offs are files, not chat.** The network's memory lives on disk:

- `plan.json` — planner's scoping (who analyzes what)
- `evidence/{classes,db,flows,usecases,domain}.json` — analysts' findings,
  each item already carrying its code citations
- `critique/<doc>-r<n>.json` / `<doc>-r<n>-fixer.json` — critic verdicts and
  fixer responses, per document, per round
- `verification/report.json` — mechanical verdict per document

Because state is in files, the run survives context loss: the orchestrator can
re-read the artifacts and continue (recovery policy R5).

### The Critic-Fixer debate (and why it matters)

This is the "write → run → read the error log → fix autonomously" loop, applied
to *documentation* instead of code. Each round:

1. **Critic** (one agent per document, prompted by `agents/04-critic.md`)
   re-reads the artifact *and* the cited source lines, and files a machine-
   readable critique: wrong line numbers, invented members, missing edges,
   section gaps, citation typos. The critic is read-only — it may only write
   `critique/*.json`.
2. **Fixer** (one agent per document with majors, `agents/05-fixer.md`)
   reads the critique, re-inspects the source, and rewrites the document.
3. The loop repeats for up to **3 rounds** (`full` mode) or **1 round**
   (`lite` mode). What the critic cannot argue the fixer to accept is decided
   by the deterministic verifier, so taste-based nitpicks cannot loop forever.

### Robust error recovery

The "wow" of a multi-agent system is not the dispatch; it is what happens when
things fail. Every failure mode has a named policy (SKILL.md §4):

| Policy | Failure | Recovery |
|---|---|---|
| **R1** | clone fails (auth / 404 / network) | retry ladder (shallow clone, `--depth 1`); on auth/404 stop and ask the user |
| **R2** | an agent fails or times out | re-dispatch once with a "previous attempt" resume note; then split the scope (analysts) or mark the artifact `PARTIAL` (writers) and log it |
| **R3** | planner emits an invalid plan | orchestrator builds a fallback `plan.json` straight from `inventory.json` buckets; the planner's failure is logged |
| **R4** | critic-fixer loop exhausts rounds with majors left | remaining majors go into `## Unresolved Findings`; the document is delivered as `FAILED`/`PARTIAL`, the rest ships, and the final message states exactly what is open |
| **R5** | the run outlives its context window | re-read `plan.json`, `evidence/`, `critique/`, `verification/report.json` — disk is the network's memory — and resume |

Nothing is silently dropped: every recovery is recorded in `SUMMARY.md`.

## Installation

Copy (or symlink) this `codebase-modeler/` folder into your skills directory:

```sh
# Kimi Code (user scope)
cp -r codebase-modeler ~/.agents/skills/        # or ln -s

# Claude Code (project scope)
cp -r codebase-modeler .claude/skills/

# any other host: put it wherever that host loads skills from
```

The skill is **self-contained** — no `custom-agents/`, no extra persona files.
Role prompts in `agents/` are complete. Hosts that support custom agent
definitions (e.g. Kimi Code's `custom-agents/`) *may* add thin role files to
harden the critic to a strict read-only tool set, but the skill works without
them.

Python 3 is required for the two deterministic scripts (no third-party
packages).

## Usage

With the skill installed, invoke it from the project that contains your
`templates/` folder:

```
/codebase-modeler https://github.com/owner/repo
```

Full form:

```
/codebase-modeler <github-url> [full|lite] [templates_dir] [out_dir]
```

- **`<github-url>`** — `https://github.com/<owner>/<name>` (a `.git` suffix is
  fine). A local git-repo path also works.
- **`[full|lite]`** — `full` (default): parallel analysts, per-document
  writers, 3 critic-fixer rounds. `lite`: single writer batch, 1 round — use
  for small repos (< ~15k LOC).
- **`[templates_dir]`** — where the six `*.md` templates live
  (default `templates/` in the project root). If a template is missing the
  skill stops and tells you which one.
- **`[out_dir]`** — output root (default `output/`); artifacts land in
  `output/<REPO_NAME>/`.

### Output layout

```
output/<REPO_NAME>/
├── .repo/                     # the cloned working copy (citations point here)
├── inventory.md  inventory.json
├── plan.json
├── evidence/{db,classes,flows,usecases,domain}.json
├── DatabaseModel.md  ClassModel.md  DomainModel.md
├── UseCaseModel.md   ActivityDiagram.md  Specification.md
├── critique/<doc>-r<r>.json  <doc>-r<r>-fixer.json
├── verification/report.json  verification-report.md
└── SUMMARY.md
```

## Verifying the results yourself

The same mechanical check the skill runs at the end can be re-run any time:

```sh
python3 scripts/verify.py <out_dir>/<REPO_NAME> <out_dir>/<REPO_NAME>/.repo
```

Exit `0` = every document PASS; exit `1` = at least one FAIL, with the defect
list in `verification/report.json` / `verification-report.md`. The verifier
checks, per document: required template sections, balanced code fences, the
required Mermaid diagram type (activity diagrams must contain swimlanes),
per-node traceability maps, and that **every citation resolves to a real file
and a line range that exists**.

### Self-test

The skill ships with a fixture repo and hand-written passing outputs, plus a
self-test that exercises the deterministic parts end to end:

```sh
bash scripts/selftest.sh
```

It proves: `inventory.py` runs cleanly and emits `inventory.json`/`inventory.md`,
`verify.py` PASSes on the good fixture outputs, `verify.py` **FAILs** (exit 1)
when a citation is deliberately broken (out-of-range line number), and
`inventory.py` rejects an empty repo (exit 3). Five checks, all must pass.

## What is and is not automated

- **Automated and self-tested:** repo inventory, citation resolution,
  section/diagram/traceability-map checks, self-test suite.
- **Not covered by the self-test:** the LLM phases (planner, analysts,
  writers, critic, fixer) — running them needs a real clone of a target repo
  and real sub-agent dispatches by the host. The self-test exists so the
  deterministic contracts those agents are held to are known-good.
