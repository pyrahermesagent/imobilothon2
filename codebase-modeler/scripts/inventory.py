#!/usr/bin/env python3
"""Codebase Modeler - repo inventory (Phase 0).

Usage:  python3 inventory.py <repo_dir> <out_dir>
Writes: <out_dir>/inventory.json + <out_dir>/inventory.md
Exit:   0 ok | 2 repo dir missing | 3 no source files found
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "env", ".env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".idea",
    ".vscode", "dist", "build", "out", "target", "coverage", ".next", ".nuxt",
    ".turbo", ".cache", "vendor", ".terraform", "Pods", "DerivedData",
    "staticfiles", "media", ".eggs",
}
SKIP_FILE_PATTERNS = (".min.js", ".min.css", ".map", ".lock", ".min.")

EXT_LANG = {
    "py": "python", "pyi": "python", "ipynb": "jupyter",
    "js": "javascript", "mjs": "javascript", "cjs": "javascript", "jsx": "javascript",
    "ts": "typescript", "tsx": "typescript", "mts": "typescript",
    "java": "java", "kt": "kotlin", "kts": "kotlin", "scala": "scala",
    "cs": "csharp", "fs": "fsharp", "fsx": "fsharp",
    "go": "go", "rs": "rust", "rb": "ruby", "php": "php", "swift": "swift",
    "c": "c", "h": "c", "cpp": "cpp", "cc": "cpp", "hpp": "cpp", "cxx": "cpp",
    "hpp": "cpp", "m": "objc", "mm": "objc", "lua": "lua", "pl": "perl", "pm": "perl",
    "sh": "shell", "bash": "shell", "zsh": "shell", "ps1": "powershell",
    "html": "html", "htm": "html", "css": "css", "scss": "scss", "less": "less",
    "vue": "vue", "svelte": "svelte", "twig": "twig", "hbs": "handlebars",
    "ejs": "ejs", "jsp": "jsp", "asp": "asp", "aspx": "aspx", "cshtml": "razor",
    "sql": "sql", "graphql": "graphql", "gql": "graphql", "proto": "protobuf",
    "prisma": "prisma", "dbml": "dbml", "md": "markdown", "mdx": "markdown",
    "json": "json", "yaml": "yaml", "yml": "yaml", "toml": "toml", "ini": "ini",
    "cfg": "cfg", "conf": "conf", "properties": "properties", "gradle": "gradle",
    "xml": "xml", "csproj": "msbuild", "sln": "msbuild", "vb": "vb",
    "cob": "cobol", "cbl": "cobol", "cpy": "cobol", "ex": "elixir", "exs": "elixir",
    "dart": "dart", "ml": "ocaml", "erl": "erlang", "nim": "nim", "r": "r",
}
SOURCE_EXTS = set(EXT_LANG) - {"markdown", "json", "yaml", "toml", "ini", "cfg", "conf",
                               "properties", "xml", "msbuild", "html"}

# framework detection: manifest -> names that imply these frameworks
FRAMEWORK_HINTS = {
    "react": ["react", "react-dom"], "next": ["next"], "vue": ["vue", "nuxt", "nuxt3"],
    "nuxt": ["nuxt", "nuxt3"], "svelte": ["svelte", "@sveltejs/kit"],
    "angular": ["@angular/core"], "solid": ["solid-js"], "preact": ["preact"],
    "tailwind": ["tailwindcss"], "redux": ["@reduxjs/toolkit", "redux"],
    "zustand": ["zustand"], "pinia": ["pinia"], "vuex": ["vuex"],
    "express": ["express"], "fastify": ["fastify"], "koa": ["koa"],
    "nestjs": ["@nestjs/core"], "hapi": ["@hapi/hapi"], "sveltekit": ["@sveltejs/kit"],
    "vite": ["vite"], "webpack": ["webpack"], "react-router": ["react-router", "react-router-dom"],
    "flask": ["flask"], "django": ["django", "django.*"], "fastapi": ["fastapi"],
    "tornado": ["tornado"], "aiohttp": ["aiohttp"], "bottle": ["bottle"],
    "starlette": ["starlette"], "celery": ["celery"],
    "spring-boot": ["spring-boot", "spring-boot-starter"], "spring": ["spring-"],
    "hibernate": ["hibernate"], "jackson": ["jackson"],
    "rails": ["rails", "railties"], "sequel": ["sequel"], "activerecord": ["activerecord"],
    "laravel": ["laravel/framework"], "symfony": ["symfony/framework-bundle"],
    "gin": ["github.com/gin-gonic/gin"], "chi": ["github.com/go-chi/chi"],
    "echo": ["github.com/labstack/echo"], "fiber": ["github.com/gofiber/fiber"],
    "gorilla-mux": ["github.com/gorilla/mux"],
    "entity-framework-core": ["microsoft.entityframeworkcore"],
    "sqlalchemy": ["sqlalchemy"], "peewee": ["peewee"], "tortoise": ["tortoise-orm"],
    "prisma": ["prisma", "@prisma/client"], "typeorm": ["typeorm"],
    "drizzle": ["drizzle-orm"], "sequelize": ["sequelize"], "knex": ["knex"],
    "mongoose": ["mongoose"], "pymongo": ["pymongo"], "psycopg2": ["psycopg2", "psycopg2-binary"],
    "psycopg": ["psycopg"], "asyncpg": ["asyncpg"], "mysql-connector": ["mysql-connector-python"],
    "sqlite": ["aiosqlite", "sqlite3"], "redis": ["redis", "redis-py", "ioredis"],
    "kafka": ["kafka-python", "confluent-kafka", "kafka"], "stripe": ["stripe"],
    "sendgrid": ["sendgrid", "python-http-client"], "twilio": ["twilio"],
    "jwt": ["pyjwt", "jsonwebtoken", "python-jose"], "boto3": ["boto3"],
    "graphql": ["graphql", "graphql-core", "apollo-server"], "pytest": ["pytest"],
    "jest": ["jest"], "mocha": ["mocha"], "vitest": ["vitest"], "cypress": ["cypress"],
    "playwright": ["@playwright/test", "playwright"], "selenium": ["selenium"],
    "junit": ["junit", "junit-jupiter"], "xunit": ["xunit"], "mocha2": ["mocha"],
    "webpack-dev-server": ["webpack-dev-server"], "docker": ["docker"],
}
MANIFEST_NAMES = {"package.json", "requirements.txt", "pyproject.toml", "Pipfile",
                  "pom.xml", "build.gradle", "build.gradle.kts", "go.mod", "Gemfile",
                  "composer.json", "Cargo.toml", "mix.exs", "setup.py", "setup.cfg",
                  "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "alembic.ini",
                  "schema.prisma", "manage.py", "wsgi.py", "asgi.py"}


def looks_binary(path, sample=8192):
    try:
        with open(path, "rb") as f:
            return b"\x00" in f.read(sample)
    except OSError:
        return True


def count_lines(path):
    try:
        n = 0
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for _ in f:
                n += 1
        return n
    except OSError:
        return 0


def read_text_capped(path, cap=200_000):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(cap)
    except OSError:
        return ""


def detect_frameworks(repo):
    found = {}
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if fn in MANIFEST_NAMES and fn in ("package.json", "requirements.txt",
                                              "pyproject.toml", "Pipfile", "pom.xml",
                                              "build.gradle", "build.gradle.kts", "go.mod",
                                              "Gemfile", "composer.json", "Cargo.toml"):
                p = os.path.join(dirpath, fn)
                text = read_text_capped(p)
                for fw, names in FRAMEWORK_HINTS.items():
                    for nm in names:
                        if re.search(r"(?<![A-Za-z0-9_-])" + re.escape(nm) + r"(?![A-Za-z0-9_-])",
                                     text):
                            found.setdefault(fw, []).append(os.path.relpath(p, repo))
                break  # one manifest per dirname check is enough? no - keep scanning
    return found


def main():
    if len(sys.argv) != 3:
        print("usage: inventory.py <repo_dir> <out_dir>", file=sys.stderr)
        sys.exit(2)
    repo, out = sys.argv[1].rstrip("/"), sys.argv[2]
    if not os.path.isdir(repo):
        print(f"ERROR: repo dir not found: {repo}", file=sys.stderr)
        sys.exit(2)
    os.makedirs(out, exist_ok=True)

    files = []
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if any(fn.endswith(p) for p in SKIP_FILE_PATTERNS):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, repo)
            ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
            if looks_binary(p):
                continue
            files.append({"path": rel, "ext": ext, "lines": count_lines(p)})

    src = [f for f in files if f["ext"] in SOURCE_EXTS]
    total_lines = sum(f["lines"] for f in files)
    lang = {}
    for f in files:
        l = EXT_LANG.get(f["ext"], "other")
        lang[l] = lang.get(l, 0) + f["lines"]

    if not src:
        print("ERROR: no source files found - is this a source repository?", file=sys.stderr)
        print(f"   (found {len(files)} files total)", file=sys.stderr)
        sys.exit(3)

    # directory aggregation (top-level + one level down)
    dirs = {}
    for f in files:
        parts = f["path"].split(os.sep)
        for n in (1, 2):
            if len(parts) > n:
                key = os.sep.join(parts[:n]) + "/"
                dirs.setdefault(key, {"files": 0, "lines": 0})
                dirs[key]["files"] += 1
                dirs[key]["lines"] += f["lines"]
    top_dirs = sorted(
        ({"dir": k, **v} for k, v in dirs.items() if k.count(os.sep) == 1),
        key=lambda d: d["lines"], reverse=True)[:40]

    fw = detect_frameworks(repo)
    frameworks = sorted(fw)

    def bucket(pred):
        return [f["path"] for f in src if pred(f)]

    def pathin(*parts):
        return lambda f: any(p in f["path"] for p in parts)

    buckets = {
        "db": [f["path"] for f in files if f["path"].endswith((".sql", ".prisma", ".dbml"))
               or re.search(r"(^|/)(migrations?|alembic|db|database|prisma|schema)/", f["path"])],
        "frontend": [f["path"] for f in src
                     if f["ext"] in ("tsx", "jsx", "vue", "svelte", "twig", "hbs", "ejs",
                                     "jsp", "asp", "aspx", "cshtml", "html", "css", "scss", "less")
                     or re.search(r"(^|/)(components?|pages?|views?|templates?|static?|public?)/",
                                  f["path"])],
        "backend": [f["path"] for f in src
                    if re.search(r"(^|/)(routes?|controllers?|api|handlers?|services?|"
                                 r"endpoints?|middleware|graphql?|resolvers?|wsgi|asgi)/",
                                  f["path"])
                    or f["path"] in ("manage.py", "wsgi.py", "asgi.py", "app.py")],
        "tests": [f["path"] for f in src
                  if re.search(r"(^|/)(tests?|spec|__tests__|e2e|cypress|playwright)/", f["path"])
                  or re.search(r"(\.test\.|\.spec\.|_test\.|_spec\.|test_)", f["path"])],
        "entry": [f["path"] for f in src
                  if re.fullmatch(r"(main|app|index|server|cli|manage|wsgi|asgi|run|Program)\.[^.]+",
                                  f["path"].rsplit("/", 1)[-1])],
    }

    inventory = {
        "repo_name": os.path.basename(repo),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "totals": {"files": len(files), "source_files": len(src), "lines": total_lines,
                   "lines_by_language": dict(sorted(lang.items(), key=lambda x: -x[1]))},
        "top_dirs": top_dirs,
        "frameworks": frameworks,
        "framework_evidence": {k: sorted(set(v))[:5] for k, v in sorted(fw.items())},
        "manifests": [f["path"] for f in files if f["path"].rsplit("/", 1)[-1] in MANIFEST_NAMES],
        "buckets": {k: v[:200] for k, v in buckets.items()},
        "files": files[:5000],
        "files_truncated": len(files) > 5000,
    }

    with open(os.path.join(out, "inventory.json"), "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=1)

    md = [f"# Inventory - {inventory['repo_name']}", "",
          f"Generated {inventory['generated_at']}", "",
          f"- Files: {len(files)} (source: {len(src)}), total lines: {total_lines}",
          "- Languages: " + ", ".join(f"{k} ({v})" for k, v in
                                      inventory["totals"]["lines_by_language"].items()),
          f"- Frameworks detected: {', '.join(frameworks) or 'none detected'}",
          f"- Manifests: {', '.join(inventory['manifests']) or 'none'}", "",
          "## Top directories (by lines)", "",
          "| Dir | Files | Lines |", "| :-- | --: | --: |"]
    for d in top_dirs[:20]:
        md.append(f"| `{d['dir']}` | {d['files']} | {d['lines']} |")
    for name, key in (("DB / migrations / schema", "db"), ("Frontend", "frontend"),
                      ("Backend / API", "backend"), ("Tests", "tests"), ("Entry points", "entry")):
        md += ["", f"## {name} (`{len(buckets[key])}` files)", ""]
        for p in buckets[key][:40]:
            md.append(f"- `{p}`")
        if len(buckets[key]) > 40:
            md.append(f"- ... and {len(buckets[key]) - 40} more (see inventory.json)")
    md += ["", f"> Scope caps for the Planner: ≤ 60 files and ≤ 25,000 lines per analyst scope."]
    with open(os.path.join(out, "inventory.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"OK: {len(files)} files, {len(src)} source, {total_lines} lines, "
          f"{len(frameworks)} frameworks -> {out}/inventory.json")


if __name__ == "__main__":
    main()
