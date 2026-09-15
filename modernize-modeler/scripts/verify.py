#!/usr/bin/env python3
"""Modernize Modeler - mechanical verifier (Phase 4).

Usage:  python3 verify.py <mod_dir> <src_dir> [repo_dir]
        (repo_dir defaults to <src_dir>/.repo when present)

Checks, for each of the six MODERNIZED artifacts in <mod_dir>:
  1. modernization header present (references the source output dir and
     modernization-plan.json);
  2. all required template sections present (fuzzy, case-insensitive) - the
     modernized document must mirror its template exactly;
  3. honesty sections present: "Modernization Decisions (this document)" and
     "Resolved Assumptions & Issues";
  4. no open UNVERIFIED markers outside the Resolved Assumptions & Issues
     section (modernized docs close every assumption: resolved/accepted/deferred);
  5. every decision/ledger reference (M-n, A-n, I-n, D-n, K-n) resolves in
     <mod_dir>/modernization-plan.json;
  6. every code citation `path:line[-end]` resolves - legacy repo citations
     against <repo_dir>, source-artifact citations (e.g. `Specification.md:33`)
     against <src_dir>; when no repo is available, unresolved non-source spans
     are SKIPPED (warning), never failed;
  7. Mermaid fences balanced, required diagram types present, activity diagrams
     use swimlanes, node-map tables cover diagram node ids.
Plus a global check of modernization-plan.json itself:
  8. decisions carry id/from_citations/why/artifacts; every directive item is
     dispositioned (decision refs, or deferred/kept_unchanged with a reason);
     every assumption/issue has a terminal status; the assumption/issue ledger
     covers every source artifact that contains UNVERIFIED markers.
Writes: <mod_dir>/verification/report.json + <mod_dir>/verification/verification-report.md
Exit:   0 all artifacts PASS | 1 at least one FAIL | 2 usage error
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

DOCS = ["Specification.md", "ClassModel.md", "DatabaseModel.md", "DomainModel.md",
        "UseCaseModel.md", "ActivityDiagram.md"]

REQUIRED_SECTIONS = {
    "Specification.md": ["Executive Summary", "Project Scope", "Technology Stack",
                         "Functional Requirements", "Non-Functional Requirements",
                         "Data Model", "API Specification", "UI/UX", "Testing Strategy",
                         "Deployment"],
    "ClassModel.md": ["Core Elements", "Backend", "DTO", "Frontend", "Relationships"],
    "DatabaseModel.md": ["System Overview", "Architecture", "Naming Conventions",
                         "Entity-Relationship", "Core Entities", "Relationships", "Index",
                         "Security", "Seed", "Scalab"],
    "DomainModel.md": ["Scope", "Ubiquitous Language", "Bounded Context", "Entity",
                       "Value Object", "Aggregate", "Relationship", "Invariant",
                       "Domain Event", "Domain Service"],
    "UseCaseModel.md": ["Introduction", "Actors", "Use-Case Diagram",
                        "Use-Case Specification", "Pre-condition", "Post-condition",
                        "Main Success", "Alternative Flow", "Exception", "Traceability"],
    "ActivityDiagram.md": ["Decision", "Swimlane", "Error"],
}

REQUIRED_MERMAID = {  # doc -> list of acceptable type keywords (any one suffices)
    "ClassModel.md": [["classDiagram"]],
    "DatabaseModel.md": [["erDiagram"]],
    "UseCaseModel.md": [["flowchart", "graph"]],
    "ActivityDiagram.md": [["flowchart", "graph"]],
    "DomainModel.md": [],
    "Specification.md": [],
}

HONESTY_SECTIONS = ["Modernization Decisions", "Resolved Assumptions"]

ALLOWED_EXTS = {
    "py", "js", "jsx", "ts", "tsx", "mjs", "cjs", "java", "cs", "go", "rb", "php", "sql",
    "md", "json", "yaml", "yml", "xml", "toml", "ini", "cfg", "conf", "properties",
    "csproj", "sln", "gradle", "kts", "pom", "kt", "scala", "swift", "vue", "svelte",
    "html", "htm", "css", "scss", "less", "sh", "bash", "zsh", "pl", "pm", "cob", "cbl",
    "vb", "jsp", "asp", "aspx", "cshtml", "graphql", "gql", "proto", "prisma", "dbml",
    "hbs", "ejs", "twig", "rs", "c", "h", "cpp", "hpp", "cc", "lua", "ex", "exs", "dart",
    "ml", "erl", "nim", "r", "m", "mm", "bat", "ps1", "ipynb", "txt", "env",
}

CITE_RE = re.compile(r"^[A-Za-z0-9_\-./]+\.[A-Za-z0-9]{1,10}:(\d+)(?:-(\d+))?$")
BARE_CITE_RE = re.compile(r"\b([A-Za-z0-9_\-./]+\.[A-Za-z0-9]{1,10}:(\d+)(?:-(\d+))?)")
MERMAID_BLOCK_RE = re.compile(r"^```mermaid\s*\n(.*?)^```", re.M | re.S)
REF_RE = re.compile(r"\b([MAIKD])-(\d+)\b")
UNRESOLVED_SEC_RE = re.compile(r"^## .*Resolved Assumptions", re.M)

MERMAID_KEYWORDS = {
    "subgraph", "end", "direction", "classDiagram", "erDiagram", "flowchart", "graph",
    "sequenceDiagram", "stateDiagram", "class", "classDef", "style", "click", "linkStyle",
    "TB", "TD", "LR", "RL", "BT", "participant", "as", "activate", "deactivate", "note",
    "left", "right", "center", "over", "rect", "alt", "loop", "opt", "par", "critical",
    "break", "else", "of", "in", "out", "and", "the", "a", "an", "this", "is", "are",
}


def parse_citation(span):
    m = CITE_RE.match(span)
    if not m:
        return None
    path = span[:span.rfind(":")]
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else start
    return path, start, end


def strip_mermaid_labels(text):
    for _ in range(3):
        text = re.sub(r"\[[^\[\]]*\]", "[]", text)
        text = re.sub(r"\{[^{}]*\}", "{}", text)
        text = re.sub(r"\([^()]*\)", "()", text)
        text = re.sub(r"\|[^|]*\|", "|", text)
    text = re.sub(r'"[^"]*"', '""', text)
    return text


ARROW_RE = re.compile(r"(-->|<--|--|\.\.>|==>|~>|--o|o--|\[o|o\]|o\||\|o|<\|o|o\|>|-o|o-|<\|--|--\|>)")


def extract_node_ids(block, dtype):
    if dtype == "erDiagram":
        return set()
    if dtype == "classDiagram":
        ids = set()
        for m in re.finditer(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)", block):
            ids.add(m.group(1))
        for line in block.splitlines():
            s = line.strip()
            if not s or s.startswith("%%") or s.startswith("class "):
                continue
            if ARROW_RE.search(s):
                head = strip_mermaid_labels(s.split(":")[0])
                for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", head):
                    if tok not in MERMAID_KEYWORDS:
                        ids.add(tok)
        return ids
    ids = set()
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("%%") or line.startswith("subgraph"):
            continue
        line = strip_mermaid_labels(line)
        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", line):
            if tok not in MERMAID_KEYWORDS:
                ids.add(tok)
    return ids


def mermaid_blocks(text):
    out = []
    for m in MERMAID_BLOCK_RE.finditer(text):
        before = text.count("\n", 0, m.start()) + 1
        after = text.count("\n", 0, m.end()) + 1
        body = m.group(1)
        first = next((l.strip() for l in body.splitlines() if l.strip()), "")
        out.append((before, after, first, body))
    return out


class FileLines:
    """Cached line counts + first-line context for a root directory."""

    def __init__(self, root):
        self.root = (root or "").rstrip("/")
        self._cache = {}

    def _count(self, rel):
        if rel not in self._cache:
            rel2 = rel[2:] if rel.startswith("./") else rel
            full = os.path.join(self.root, rel2) if self.root else None
            n = None
            if full:
                try:
                    with open(full, "r", encoding="utf-8", errors="replace") as f:
                        n = sum(1 for _ in f)
                except OSError:
                    n = None
            self._cache[rel] = n
        return self._cache[rel]

    def context(self, rel, line):
        rel = rel[2:] if rel.startswith("./") else rel
        full = os.path.join(self.root, rel)
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                ctx = f.readline().strip() if line == 1 else ""
                for _ in range(line - 1):
                    ctx = f.readline().strip()
            return ctx[:100]
        except OSError:
            return ""


def extract_citations(doc_text):
    """Backticked citations in prose/tables; bare path:line inside mermaid blocks."""
    spans = []
    mermaid_line_ranges = []
    for m in MERMAID_BLOCK_RE.finditer(doc_text):
        mermaid_line_ranges.append(
            (doc_text.count("\n", 0, m.start()) + 1,
             doc_text.count("\n", 0, m.end()) + 1))
    for i, line in enumerate(doc_text.splitlines(), 1):
        in_mermaid = any(a <= i <= b for a, b in mermaid_line_ranges)
        if in_mermaid:
            for cand in BARE_CITE_RE.findall(line):
                full = cand[0]
                ext = full.rsplit(".", 1)[-1].split(":")[0].lower()
                if "/" in full or ext in ALLOWED_EXTS:
                    spans.append((full, i))
        else:
            for span in line.split("`"):
                if span.startswith(" ") or span.endswith(" "):
                    continue
                if CITE_RE.match(span.strip()):
                    spans.append((span.strip(), i))
    seen, out = set(), []
    for s, l in spans:
        if (s, l) not in seen:
            seen.add((s, l))
            out.append((s, l))
    return out


def extract_refs(doc_text):
    """All M-/A-/I-/D-/K- reference ids, as (ref, line)."""
    out = []
    for i, line in enumerate(doc_text.splitlines(), 1):
        for m in REF_RE.finditer(line):
            out.append((m.group(0), i))
    return out


def unresolved_section_range(text):
    """Line range (1-based, inclusive) of the 'Resolved Assumptions & Issues' section."""
    m = UNRESOLVED_SEC_RE.search(text)
    if not m:
        return None
    start = text.count("\n", 0, m.start()) + 1
    rest = text[m.end():]
    nxt = re.search(r"^## ", rest, re.M)
    if nxt:
        # body lines between this heading and the next '## ' heading
        end = start + rest[:nxt.start()].count("\n") - 1
    else:
        end = len(text.splitlines())
    return start, end


def load_plan(mod_dir):
    path = os.path.join(mod_dir, "modernization-plan.json")
    if not os.path.isfile(path):
        return None, "modernization-plan.json missing"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), None
    except (json.JSONDecodeError, OSError) as e:
        return None, f"modernization-plan.json unreadable: {e}"


def check_plan(plan, src_unverified):
    """Global plan-level checks. Returns (defects, warnings, id_sets)."""
    defects, warnings = [], []
    ids = {"M": set(), "A": set(), "I": set(), "D": set(), "K": set()}
    if plan is None:
        return ["plan missing/unreadable - no reference can resolve"], warnings, ids

    for key in ("directives", "stack", "decisions", "kept", "assumptions", "issues",
                "artifact_scopes"):
        if key not in plan:
            defects.append(f"plan missing key: {key}")

    decisions = plan.get("decisions", []) or []
    for d in decisions:
        did = d.get("id")
        if not did or not did.startswith("M-"):
            defects.append(f"decision with bad id: {did!r}")
            continue
        ids["M"].add(did)
        if not d.get("summary"):
            defects.append(f"{did}: missing summary")
        if not (d.get("from_citations") or d.get("to_citations")):
            defects.append(f"{did}: no citations (from or to)")
        if not d.get("why"):
            defects.append(f"{did}: missing rationale")
        if not d.get("artifacts"):
            defects.append(f"{did}: missing artifacts list")
        else:
            bad = [a for a in d["artifacts"] if a not in DOCS]
            if bad:
                defects.append(f"{did}: unknown artifacts {bad}")

    items = (plan.get("directives", {}) or {}).get("items", []) or []
    for it in items:
        did = it.get("id")
        if not did or not did.startswith("D-"):
            defects.append(f"directive with bad id: {did!r}")
            continue
        ids["D"].add(did)
        refs = it.get("refs") or []
        disp = it.get("disposition", "")
        if not refs and disp not in ("deferred", "kept_unchanged"):
            defects.append(f"{did}: no decision refs and not deferred/kept_unchanged")
        elif disp in ("deferred", "kept_unchanged") and not it.get("reason"):
            defects.append(f"{did}: disposition {disp} without a reason")

    for coll, prefix in (("assumptions", "A"), ("issues", "I")):
        for e in plan.get(coll, []) or []:
            eid = e.get("id")
            if not eid or not eid.startswith(prefix + "-"):
                defects.append(f"{coll} entry with bad id: {eid!r}")
                continue
            ids[prefix].add(eid)
            if e.get("status") not in ("resolved", "accepted", "deferred"):
                defects.append(f"{eid}: status {e.get('status')!r} not terminal")
            if e.get("status") == "resolved" and not (e.get("decision_refs") or e.get("refs")):
                defects.append(f"{eid}: resolved without decision refs")
            if e.get("status") in ("accepted", "deferred") and not e.get("reason"):
                defects.append(f"{eid}: {e.get('status')} without a reason")
            if e.get("source_doc") and e["source_doc"] not in DOCS:
                defects.append(f"{eid}: source_doc {e['source_doc']!r} not an artifact")

    ids["K"].update(k.get("id", "") for k in plan.get("kept", []) or [])
    ids["K"].discard("")

    # Ledger coverage: every source artifact with UNVERIFIED markers must be covered.
    covered = {}
    for coll in ("assumptions", "issues"):
        for e in plan.get(coll, []) or []:
            sd = e.get("source_doc")
            if sd:
                covered[sd] = covered.get(sd, 0) + 1
    total_entries = sum(covered.values())
    total_markers = sum(src_unverified.values())
    for doc in DOCS:
        if src_unverified.get(doc, 0) > 0 and covered.get(doc, 0) < 1:
            defects.append(f"ledger does not cover {doc} "
                            f"({src_unverified[doc]} UNVERIFIED marker(s) in source, "
                            f"0 ledger entries)")
    if total_markers > 0 and total_entries < total_markers:
        warnings.append(f"ledger entries ({total_entries}) < UNVERIFIED markers "
                        f"in source ({total_markers}) - confirm each marker is closed")

    scopes = plan.get("artifact_scopes", {}) or {}
    for doc in DOCS:
        if doc not in scopes:
            defects.append(f"artifact_scopes missing {doc}")
    return defects, warnings, ids


def main():
    if len(sys.argv) not in (3, 4):
        print("usage: verify.py <mod_dir> <src_dir> [repo_dir]", file=sys.stderr)
        sys.exit(2)
    mod, src = sys.argv[1].rstrip("/"), sys.argv[2].rstrip("/")
    repo = sys.argv[3] if len(sys.argv) == 4 else None
    if repo is None and os.path.isdir(os.path.join(src, ".repo")):
        repo = os.path.join(src, ".repo")
    if not os.path.isdir(mod):
        print(f"ERROR: modernized dir not found: {mod}", file=sys.stderr)
        sys.exit(2)
    if not os.path.isdir(src):
        print(f"ERROR: source dir not found: {src}", file=sys.stderr)
        sys.exit(2)

    repo_lines = FileLines(repo) if repo else None
    src_lines = FileLines(src)
    plan, plan_err = load_plan(mod)
    src_unverified = {d: unverified_count(os.path.join(src, d)) for d in DOCS}
    plan_defects, plan_warnings, ref_ids = check_plan(plan, src_unverified)

    vdir = os.path.join(mod, "verification")
    os.makedirs(vdir, exist_ok=True)
    report = {"mod_dir": mod, "src_dir": src, "repo_dir": repo,
              "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "plan": {"ok": plan is not None and not plan_err, "defects": plan_defects,
                       "warnings": plan_warnings},
              "docs": {}}
    md = ["# Modernization Verification Report", "",
          f"- Source: `{src}`",
          f"- Repo: `{repo}` ({'citations verifiable' if repo else 'NOT available - legacy citations skipped'})",
          f"- Generated: {report['generated_at']}", ""]
    if plan_err:
        md.append(f"**PLAN FAIL: {plan_err}**", "")

    overall_ok = not (plan_err or plan_defects)
    for doc in DOCS:
        path = os.path.join(mod, doc)
        d = {"exists": os.path.isfile(path), "header": False, "honesty_sections": True,
             "citations": {"total": 0, "resolved_repo": 0, "resolved_src": 0,
                           "skipped": 0, "failed": []},
             "references": {"total": 0, "failed": []},
             "unverified_leftovers": [], "sections_missing": [],
             "mermaid": {"blocks": 0, "types": [], "required_present": True,
                          "fences_balanced": True},
             "node_maps": {"missing_maps": [], "missing_ids": {}},
             "density_warnings": [], "major_defects": [], "minor_warnings": [],
             "status": "PASS"}
        if not d["exists"]:
            d["major_defects"].append("artifact missing")
            d["status"] = "FAIL"
            report["docs"][doc] = d
            overall_ok = False
            md += [f"## {doc}", "", "**FAIL** - artifact missing.", ""]
            continue

        text = open(path, encoding="utf-8", errors="replace").read()
        lines = text.splitlines()
        low = text.lower()

        # 1. header
        if not re.search(r"^.*Source:.*$", text, re.M | re.I) or \
                "modernization-plan.json" not in text:
            d["header"] = False
            d["major_defects"].append("modernization header missing "
                                      "(Source: line + modernization-plan.json reference)")

        # 2. template sections
        for sec in REQUIRED_SECTIONS[doc]:
            if sec.lower() not in low:
                d["sections_missing"].append(sec)
        if d["sections_missing"]:
            d["major_defects"].append("missing sections: " + ", ".join(d["sections_missing"]))

        # 3. honesty sections
        for sec in HONESTY_SECTIONS:
            if sec.lower() not in low:
                d["honesty_sections"] = False
                d["major_defects"].append(f"missing honesty section: {sec}")

        # 4. UNVERIFIED leftovers outside the resolved section
        rng = unresolved_section_range(text)
        for i, l in enumerate(lines, 1):
            if "UNVERIFIED" in l and (rng is None or not (rng[0] <= i <= rng[1])):
                d["unverified_leftovers"].append(i)
        if d["unverified_leftovers"]:
            d["major_defects"].append(
                f"open UNVERIFIED marker(s) outside Resolved Assumptions section "
                f"(lines {d['unverified_leftovers'][:10]})")

        # 5. references
        refs = extract_refs(text)
        d["references"]["total"] = len(refs)
        for ref, line_no in refs:
            prefix = ref[0]
            if ref not in ref_ids.get(prefix, set()):
                rec = {"ref": ref, "line": line_no,
                       "reason": "not in modernization-plan.json"
                       if plan is not None else "plan missing"}
                if not any(x["ref"] == ref and x["line"] == line_no
                           for x in d["references"]["failed"]):
                    d["references"]["failed"].append(rec)
        if d["references"]["failed"]:
            uniq = sorted({x['ref'] for x in d["references"]["failed"]})
            d["major_defects"].append(f"unresolved reference(s): {', '.join(uniq)}")

        # 6. citations
        spans = extract_citations(text)
        d["citations"]["total"] = len(spans)
        for span, line_no in spans:
            parsed = parse_citation(span)
            if not parsed:
                d["citations"]["failed"].append({"citation": span, "line": line_no,
                                                 "reason": "malformed"})
                continue
            path_, start, end = parsed
            rel = path_[2:] if path_.startswith("./") else path_
            bad_range = not (1 <= start <= end)
            repo_ok = (repo_lines is not None and not bad_range and
                       (repo_lines._count(rel) or 0) >= end)
            src_ok = (not bad_range and (src_lines._count(rel) or 0) >= end)
            if repo_ok:
                d["citations"]["resolved_repo"] += 1
            elif src_ok:
                d["citations"]["resolved_src"] += 1
            elif repo_lines is None:
                d["citations"]["skipped"] += 1
            else:
                reason = "bad range" if bad_range else "file not found (repo and source)"
                d["citations"]["failed"].append({"citation": span, "line": line_no,
                                                 "reason": reason})
        if d["citations"]["failed"]:
            d["major_defects"].append(
                f"{len(d['citations']['failed'])} unresolvable citation(s)")
        if d["citations"]["total"] == 0:
            d["major_defects"].append("zero citations in artifact")
        if d["citations"]["skipped"] and d["citations"]["resolved_repo"] == 0 and \
                d["citations"]["resolved_src"] == 0:
            d["minor_warnings"].append(
                f"all {d['citations']['skipped']} citation(s) skipped - no repo available")

        # scope-driven reference floors: plan says this doc applies decisions /
        # closes assumptions -> the doc must reference at least one of them.
        scope = (plan or {}).get("artifact_scopes", {}).get(doc, {}) if plan else {}
        if scope.get("decisions") and "M-" not in text:
            d["major_defects"].append("scope assigns decisions to this document "
                                      "but it references no M- decision")
        if (scope.get("assumptions") or scope.get("issues")) and \
                not re.search(r"\b[AI]-\d+", text):
            d["major_defects"].append("scope assigns assumptions/issues to this document "
                                      "but it references no A-/I- entry")

        # 7. mermaid
        blocks = mermaid_blocks(text)
        d["mermaid"]["blocks"] = len(blocks)
        types_found = []
        if text.count("```") % 2 != 0:
            d["mermaid"]["fences_balanced"] = False
            d["major_defects"].append("unbalanced code fences")
        for (s, e, first, body) in blocks:
            t = (first.split("(")[0].split("|")[0].strip().split() or [""])[0]
            types_found.append(t)
            if doc == "ActivityDiagram.md" and t in ("flowchart", "graph") \
                    and "subgraph" not in body.lower():
                d["major_defects"].append(
                    f"activity diagram (line {s}) has no swimlanes (subgraph)")
        d["mermaid"]["types"] = types_found
        for alts in REQUIRED_MERMAID[doc]:
            if not any(a in types_found for a in alts):
                d["mermaid"]["required_present"] = False
                d["major_defects"].append("required diagram type not found: "
                                          + "/".join(alts))

        # 8. node maps
        for (s, e, first, body) in blocks:
            t = (first.split("(")[0].strip().split() or [""])[0]
            if t == "erDiagram":
                continue
            region, stopped = [], False
            for l in lines[e:]:
                if l.startswith("## ") or l.startswith("```"):
                    stopped = True
                    break
                region.append(l)
            region_text = "\n".join(region)
            if not re.search(r"^\s*\|.*\bnode\b.*\|", region_text, re.I | re.M):
                d["node_maps"]["missing_maps"].append(f"block at line {s}")
                d["major_defects"].append(f"mermaid block at line {s} has no node map table")
                continue
            ids = extract_node_ids(body, t)
            missing = [i for i in sorted(ids)
                       if not re.search(r"\b" + re.escape(i) + r"\b", region_text)]
            if missing:
                d["node_maps"]["missing_ids"][f"line {s}"] = missing[:30]
                if len(missing) >= 3:
                    d["major_defects"].append(f"node map at line {s} missing "
                                              f"{len(missing)} node ids")
                else:
                    d["minor_warnings"].append(f"node map at line {s} missing ids: "
                                               + ", ".join(missing))

        # 9. density (citations + references)
        all_marked = set(spans)
        all_marked.update((r, l) for r, l in refs)
        cur, cur_start = None, None
        for i, l in enumerate(lines, 1):
            if re.match(r"^## ", l):
                if cur is not None and i - cur_start > 1:
                    sect_text = "\n".join(lines[cur_start - 1:i - 1])
                    n = sum(1 for sp, ln in all_marked if cur_start <= ln < i)
                    if len(sect_text) > 400 and n == 0:
                        d["density_warnings"].append(f"§ {cur} (no citations/references)")
                cur, cur_start = l[3:].strip(), i
        if cur is not None:
            sect_text = "\n".join(lines[cur_start - 1:])
            n = sum(1 for sp, ln in all_marked if ln >= cur_start)
            if len(sect_text) > 400 and n == 0:
                d["density_warnings"].append(f"§ {cur} (no citations/references)")

        d["status"] = "PASS" if not d["major_defects"] else "FAIL"
        if d["status"] == "FAIL":
            overall_ok = False
        report["docs"][doc] = d

        c = d["citations"]
        md += [f"## {doc}", "",
               f"**Status: {d['status']}** - citations {c['resolved_repo'] + c['resolved_src']}"
               f"/{c['total']} resolved ({c['skipped']} skipped); "
               f"references {d['references']['total'] - len(d['references']['failed'])}/"
               f"{d['references']['total']}; mermaid: {d['mermaid']['blocks']} block(s)", ""]
        if d["major_defects"]:
            md.append("### Major defects")
            for x in d["major_defects"]:
                md.append(f"- {x}")
            md.append("")
        if d["sections_missing"]:
            md.append("Missing template sections: " + ", ".join(d["sections_missing"]))
            md.append("")
        if c["failed"]:
            md.append("### Unresolvable citations")
            md.append("| Doc line | Citation | Reason |")
            md.append("| --: | :-- | :-- |")
            for rec in c["failed"][:100]:
                md.append(f"| {rec['line']} | `{rec['citation']}` | {rec['reason']} |")
            md.append("")
        if d["references"]["failed"]:
            md.append("### Unresolved plan references")
            md.append("| Doc line | Reference | Reason |")
            md.append("| --: | :-- | :-- |")
            for rec in d["references"]["failed"][:100]:
                md.append(f"| {rec['line']} | `{rec['ref']}` | {rec['reason']} |")
            md.append("")
        if d["minor_warnings"]:
            md.append("Warnings: " + "; ".join(d["minor_warnings"]))
            md.append("")
        if d["density_warnings"]:
            md.append("Density warnings: " + "; ".join(d["density_warnings"]))
            md.append("")

    report["overall"] = {"pass": overall_ok, "status": "PASS" if overall_ok else "FAIL"}
    with open(os.path.join(vdir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    with open(os.path.join(vdir, "verification-report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    verdicts = ", ".join(f"{k}: {v['status']}" for k, v in report["docs"].items())
    print(f"OVERALL: {report['overall']['status']}  ({verdicts}; plan: "
          f"{'ok' if report['plan']['ok'] else 'FAIL'})")
    sys.exit(0 if overall_ok else 1)


def unverified_count(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return sum(1 for line in f if "UNVERIFIED" in line)
    except OSError:
        return 0


if __name__ == "__main__":
    main()
