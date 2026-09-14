# plan.json — Schema (written by the Planner, consumed by all Analysts)

Single file: `<OUT>/plan.json`. Valid JSON only (no comments).

```json
{
  "repo_name": "example-app",
  "repo_sha": "9f86d08...",
  "mode": "full",
  "stack": {
    "frontend": {"tech": "React 18 + Vite", "citations": ["`package.json:12-40`"]},
    "backend":  {"tech": "Python 3.12 + FastAPI", "citations": ["`requirements.txt:3-9`"]},
    "database": {"tech": "PostgreSQL 15 + SQLAlchemy", "citations": ["`alembic.ini:5`"]},
    "external": [
      {"name": "Stripe", "citations": ["`app/payments.py:3`"]}
    ]
  },
  "layers": {
    "frontend": ["web/src/"],
    "backend": ["app/", "api/"],
    "data": ["migrations/", "app/models/"],
    "external": []
  },
  "scopes": {
    "db":       {"files": ["migrations/", "app/models/", "schema.prisma"], "notes": "Alembic migrations are the source of truth"},
    "classes":  {"files": ["app/", "web/src/"], "notes": ""},
    "flows":    {"files": ["app/api/", "app/services/", "web/src/api/"], "notes": ""},
    "usecases": {"files": ["app/api/", "app/core/security.py", "web/src/pages/"], "notes": ""},
    "domain":   {"files": ["app/models/", "app/schemas/", "app/services/"], "notes": ""}
  },
  "top_processes": [
    {"name": "User login", "entry_points": ["`app/api/auth.py:21`", "`web/src/pages/Login.tsx:14`"], "why": "core auth flow with client+server+db"},
    {"name": "Checkout", "entry_points": ["`app/api/orders.py:55`"], "why": "money-critical, external payment call"}
  ],
  "top_use_cases": [
    {"id": "UC-01", "name": "Authenticate a user", "hint": "`app/api/auth.py:21-60`"},
    {"id": "UC-02", "name": "Place an order", "hint": "`app/api/orders.py:55-120`"}
  ],
  "risks": [
    {"risk": "no test suite found", "citation": "UNVERIFIED: find 'test' matched nothing in inventory.json"}
  ]
}
```

## Rules the orchestrator validates before dispatching analysts
- `stack.*.citations` — every non-empty stack entry has ≥ 1 citation.
- `scopes.*.files` — non-empty for all five analysts; each scope ≤ 60 files AND ≤ 25,000 lines
  (checked against `inventory.json` line counts; a directory prefix counts by its aggregate).
- `top_processes` — 3 to 8 entries, each with ≥ 1 entry-point citation.
- `top_use_cases` — 3 to 8 entries, ids `UC-01`... in order.
- Any field the planner could not establish: keep the key, set value to
  `"UNVERIFIED: <rationale>"` (or `[]` for lists) — never delete the key.
