# Evidence files — Schema (written by Analysts, consumed by Writers / Critics / Verifier)

Five files under `<OUT>/evidence/`: `db.json`, `classes.json`, `flows.json`, `usecases.json`,
`domain.json`. All share the common envelope; all are valid JSON (no comments).

## Common envelope (every file)

```json
{
  "model": "db | classes | flows | usecases | domain",
  "repo_name": "example-app",
  "repo_sha": "9f86d08...",
  "analyst_status": "ok | partial | failed",
  "generated_by": "02-db-analyst",
  "scope_note": "what was in/out of scope, one line",
  "elements": [ ... ],
  "gaps": ["items that could not be established, with reason"]
}
```

## Element (every element in every file)

```json
{
  "id": "DB-T1",                    // stable id, prefixed per model: DB-, CL-, PR-/N-/E-, UC-, DM-
  "kind": "table",                  // element kind (model-specific, see below)
  "name": "users",
  "description": "Stores authentication + profile data",
  "code_ref": ["migrations/0001_init.sql:10-24", "app/models/user.py:8"],
  "unverified": null,               // or a rationale string when the value is an inference
  "detail": { ... }                 // kind-specific payload (below)
}
```

Rules:
- `code_ref` is REQUIRED and must have ≥ 1 entry unless `unverified` explains why.
- Citation strings are PLAIN in JSON: `rel/path.sql:10-24` (repo-root-relative; no backticks;
  1-based lines; `start-end` ranges allowed).
- A Writer may only model elements that exist here. A Critic may only flag an element that is
  here or directly implied by the artifact.

## Kind-specific `detail` payloads (minimums; agents may add fields)

### db.json
- `storage_tech`: `{ "dbms": "...", "orm": "...", "migration_tool": "...", "connection_citation": "..." }`
- `table`: `{ "columns": ["DB-C1-1"...], "source_of_truth": "migration | orm | schema_file" }`
- `column`: `{ "type": "VARCHAR(255)", "nullable": false, "default": "null | ...", "unique": true, "enum_values": ["A","B"] }`
- `key` / `index`: `{ "columns": ["user_id"], "unique": true, "composite": true, "fts": false }`
- `relationship`: `{ "from": "DB-T2", "to": "DB-T1", "cardinality": "1:N", "fk_column": "orders.user_id", "on_delete": "RESTRICT", "junction": null }`
- `seed`: `{ "purpose": "...", "counts": "..." }`

### classes.json
- `class`: `{ "layer": "domain|data-access|service|controller|dto|component|api-client|store|model",
  "fully_detailed": true,
  "attributes": [{ "name": "email", "type": "string", "visibility": "+", "code_ref": "app/models/user.py:12" }],
  "methods":    [{ "name": "save", "params": "session", "returns": "User", "visibility": "+", "code_ref": "app/models/user.py:30-41" }],
  "annotations": ["@Entity", "route: POST /auth/login"] }`
- `class_group`: `{ "description": "23 small form-field components", "paths": ["web/src/components/"] }`
- `relationship`: `{ "from": "CL-3", "to": "CL-7", "type": "association|directed|aggregation|composition|inheritance|dependency",
  "multiplicity": "1..*", "code_ref": "app/services/order_service.py:5" }`

### flows.json
- `process`: `{ "lanes": ["client","server","database","external"], "start": "PR-1-N1", "ends": ["PR-1-N14","PR-1-N15"] }`
- `node`: `{ "process_id": "PR-1", "label": "Validate credentials", "lane": "server", "kind": "action|decision|fork|join|start|end" }`
- `edge`: `{ "process_id": "PR-1", "from": "PR-1-N4", "to": "PR-1-N5", "guard": "valid" }`
  (guards on both decision exits; `code_ref` on the edge cites the branch condition)

### usecases.json
- `actor`: `{ "primary": true, "kind": "human|external_system|scheduler", "roles": ["USER","ADMIN"] }`
- `use_case`: `{ "brief": "...", "primary_actor": "UC-A1", "secondary_actors": ["UC-A5"],
  "preconditions":  [ { "text": "...", "code_ref": [...] } ],
  "postconditions": [ { "text": "...", "code_ref": [...] } ],
  "main_flow":  [ { "id": "UC-01-S1", "lane": "actor|frontend|backend|external", "text": "...", "code_ref": [...] } ],
  "alternatives": [ { "id": "UC-01-A1", "at_step": "3", "text": "...", "code_ref": [...] } ],
  "exceptions": [ { "id": "UC-01-E1", "at_step": "4", "text": "...", "code_ref": [...] } ],
  "special_requirements": [ { "text": "payment timeout 10s", "code_ref": [...] } ] }`

### domain.json
- `term`: `{ "definition": "..." }`
- `context`: `{ "handles": "...", "boundaries": ["app/identity/"] }`
- `entity`: `{ "identity": "UUID", "attributes": [...], "behaviors": [ { "name": "mark_as_shipped", "code_ref": [...] } ] }`
- `value_object`: `{ "attributes": [...], "immutability_evidence": "frozen dataclass" }`
- `aggregate`: `{ "root": "DM-E2", "children": ["DM-E3", "DM-V1"] }`
- `relationship`: `{ "from": "DM-E1", "to": "DM-E2", "cardinality": "1:N" }`
- `rule`: `{ "business_statement": "An order cannot ship before payment is verified",
  "enforced_by": "app/services/orders.py:88-96" }`
- `event`: `{ "trigger": "...", "subscribers": [ { "name": "...", "code_ref": [...] } ] }`
- `service`: `{ "responsibilities": "..." }`
