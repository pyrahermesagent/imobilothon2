#!/usr/bin/env python3
"""Codebase Modeler - mechanical verifier (Phase 5).

Usage:  python3 verify.py <out_dir> <repo_dir>
Checks, for each of the six artifacts in <out_dir>:
  1. every code citation (backticked `path:line[-end]` in text/tables; bare path:line inside
     Mermaid blocks) resolves against <repo_dir>: file exists, line range in bounds;
  2. all required template sections are present (fuzzy, case-insensitive);
  3. Mermaid fences balanced, required diagram types present, activity diagrams use swimlanes;
  4. every Mermaid block (except erDiagram) is followed by a node-map table covering its node ids;
  5. per-section citation density (warning only).
Writes: <out_dir>/verification/report.json + <out_dir>/verification/verification-report.md
Exit:   0 all artifacts PASS | 1 at least one artifact FAIL
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
    "DomainModel.md": [],  # advisory only
    "Specification.md": [],
}

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

MERMAID_KEYWORDS = {
    "subgraph", "end", "direction", "classDiagram", "erDiagram", "flowchart", "graph",
    "sequenceDiagram", "stateDiagram", "class", "classDef", "style", "click", "linkStyle",
    "TB", "TD", "LR", "RL", "BT", "participant", "as", "activate", "deactivate", "note",
    "left", "right", "center", "over", "rect", "alt", "loop", "opt", "par", "critical",
    "break", "else", "of", "in", "out", "and", "the", "a", "an", "this", "is", "are",
}


def parse_citation(span):
    """Return (path, start, end) or None. span like 'rel/path.py:10-24'."""
    m = CITE_RE.match(span)
    if not m:
        return None
    path = span[:span.rfind(":")]
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else start
    return path, start, end


def strip_mermaid_labels(text):
    """Remove node/edge label contents so only identifiers + arrows remain."""
    for _ in range(3):
        text = re.sub(r"\[[^\[\]]*\]", "[]", text)
        text = re.sub(r"\{[^{}]*\}", "{}", text)
        text = re.sub(r"\([^()]*\)", "()", text)
        text = re.sub(r"\|[^|]*\|", "|", text)   # edge labels  -->|yes|
    text = re.sub(r'"[^"]*"', '""', text)
    return text


ARROW_RE = re.compile(r"(-->|<--|--|\.\.>|==>|~>|--o|o--|\[o|o\]|o\||\|o|<\|o|o\|>|-o|o-|<\|--|--\|>)")


def extract_node_ids(block, dtype):
    """Return the set of node identifiers for a diagram body of the given type.

    - classDiagram : class names only (members like `+int id` are NOT nodes).
    - erDiagram    : skipped by caller (returns empty set).
    - flowchart/graph/sequence/state : line-token approach (labels are stripped).
    """
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
                head = strip_mermaid_labels(s.split(":")[0])  # drop rel label
                for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", head):
                    if tok not in MERMAID_KEYWORDS:
                        ids.add(tok)
        return ids
    ids = set()
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("%%"):
            continue
        if line.startswith("subgraph"):
            continue  # subgraph names are lanes, not nodes
        line = strip_mermaid_labels(line)
        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", line):
            if tok not in MERMAID_KEYWORDS:
                ids.add(tok)
    return ids


def mermaid_blocks(text):
    """Yield (start_line, end_line, first_line_of_body, body)."""
    out = []
    for m in MERMAID_BLOCK_RE.finditer(text):
        lines_before = text.count("\n", 0, m.start()) + 1
        lines_after = text.count("\n", 0, m.end()) + 1
        body = m.group(1)
        first = next((l.strip() for l in body.splitlines() if l.strip()), "")
        out.append((lines_before, lines_after, first, body))
    return out


class CiteChecker:
    def __init__(self, repo):
        self.repo = repo.rstrip("/")
        self._linecache = {}

    def _lines(self, path):
        if path not in self._linecache:
            full = os.path.join(self.repo, path)
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as f:
                    n = sum(1 for _ in f)
                self._linecache[path] = n
            except OSError:
                self._linecache[path] = None
        return self._linecache[path]

    def check(self, span, line_in_doc):
        """Return dict record for one citation span."""
        rec = {"citation": span, "doc_line": line_in_doc, "ok": False, "reason": "", "context": ""}
        parsed = parse_citation(span)
        if not parsed:
            rec["reason"] = "malformed"
            return rec
        path, start, end = parsed
        path = path[2:] if path.startswith("./") else path
        if not (1 <= start <= end):
            rec["reason"] = "bad range"
            return rec
        total = self._lines(path)
        if total is None:
            rec["reason"] = "file not found"
            return rec
        if end > total:
            rec["reason"] = f"line {end} beyond EOF ({total} lines)"
            return rec
        full = os.path.join(self.repo, path)
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                ctx = f.readline().strip() if start == 1 else ""
                if start > 1:
                    for _ in range(start - 1):
                        ctx = f.readline().strip()
            rec["context"] = ctx[:100]
        except OSError:
            pass
        rec["ok"] = True
        return rec


def extract_citations(doc_text):
    """Return (records_input_spans, mermaid_blocks_list).
    Spans: list of (citation_string, line_number)."""
    spans = []
    mermaid_line_ranges = []
    for m in MERMAID_BLOCK_RE.finditer(doc_text):
        mermaid_line_ranges.append(
            (doc_text.count("\n", 0, m.start()) + 1, doc_text.count("\n", 0, m.end()) + 1))
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
    # de-dup identical (span, line)
    seen, out = set(), []
    for s, l in spans:
        k = (s, l)
        if k not in seen:
            seen.add(k)
            out.append((s, l))
    return out


def main():
    if len(sys.argv) != 3:
        print("usage: verify.py <out_dir> <repo_dir>", file=sys.stderr)
        sys.exit(2)
    out_dir, repo = sys.argv[1].rstrip("/"), sys.argv[2]
    if not os.path.isdir(out_dir):
        print(f"ERROR: out dir not found: {out_dir}", file=sys.stderr)
        sys.exit(2)
    vdir = os.path.join(out_dir, "verification")
    os.makedirs(vdir, exist_ok=True)
    checker = CiteChecker(repo)
    report = {"out_dir": out_dir, "repo": repo,
              "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "docs": {}}
    md = ["# Verification Report", "",
          f"- Repo: `{repo}` (pinned tree for citations)",
          f"- Generated: {report['generated_at']}", ""]

    overall_ok = True
    for doc in DOCS:
        path = os.path.join(out_dir, doc)
        d = {"exists": os.path.isfile(path), "citations_total": 0, "citations_ok": 0,
             "citations_failed": [], "sections_missing": [],
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

        # 1. citations
        spans = extract_citations(text)
        d["citations_total"] = len(spans)
        ok_count = 0
        for span, line_no in spans:
            rec = checker.check(span, line_no)
            if rec["ok"]:
                ok_count += 1
            else:
                d["citations_failed"].append(rec)
        d["citations_ok"] = ok_count
        if d["citations_failed"]:
            d["major_defects"].append(
                f"{len(d['citations_failed'])} unresolvable citation(s)")
        if d["citations_total"] == 0:
            d["major_defects"].append("zero citations in artifact")

        # 2. sections
        low = text.lower()
        for sec in REQUIRED_SECTIONS[doc]:
            if sec.lower() not in low:
                d["sections_missing"].append(sec)
        if d["sections_missing"]:
            d["major_defects"].append(
                "missing sections: " + ", ".join(d["sections_missing"]))

        # 3. mermaid
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
                d["major_defects"].append(f"activity diagram (line {s}) has no swimlanes (subgraph)")
        d["mermaid"]["types"] = types_found
        for alts in REQUIRED_MERMAID[doc]:
            if not any(a in types_found for a in alts):
                d["mermaid"]["required_present"] = False
                d["major_defects"].append("required diagram type not found: "
                                          + "/".join(alts))
        if doc == "DomainModel.md" and not types_found:
            d["minor_warnings"].append("no UML diagram in DomainModel (template recommends one)")

        # 4. node maps
        for (s, e, first, body) in blocks:
            t = (first.split("(")[0].strip().split() or [""])[0]
            if t == "erDiagram":
                continue
            # region: after the closing fence up to next '## ' or next fence
            rest = lines[e:]
            region, stopped = [], False
            for l in rest:
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
                    d["major_defects"].append(
                        f"node map at line {s} missing {len(missing)} node ids")
                else:
                    d["minor_warnings"].append(
                        f"node map at line {s} missing ids: {', '.join(missing)}")

        # 5. density
        cur, cur_start = None, None
        for i, l in enumerate(lines, 1):
            if re.match(r"^## ", l):
                if cur is not None and i - cur_start > 1:
                    sect_text = "\n".join(lines[cur_start - 1:i - 1])
                    n_cites = sum(1 for sp, ln in spans if cur_start <= ln < i)
                    if len(sect_text) > 400 and n_cites == 0:
                        d["density_warnings"].append(f"§ {cur} (no citations)")
                cur, cur_start = l[3:].strip(), i
        if cur is not None:
            sect_text = "\n".join(lines[cur_start - 1:])
            n_cites = sum(1 for sp, ln in spans if ln >= cur_start)
            if len(sect_text) > 400 and n_cites == 0:
                d["density_warnings"].append(f"§ {cur} (no citations)")

        d["status"] = "PASS" if not d["major_defects"] else "FAIL"
        if d["status"] == "FAIL":
            overall_ok = False
        report["docs"][doc] = d

        md += [f"## {doc}", "",
               f"**Status: {d['status']}** - citations {d['citations_ok']}/"
               f"{d['citations_total']} ok; mermaid blocks: {d['mermaid']['blocks']} "
               f"({', '.join(d['mermaid']['types']) or 'none'})", ""]
        if d["major_defects"]:
            md.append("### Major defects")
            for x in d["major_defects"]:
                md.append(f"- {x}")
            md.append("")
        if d["sections_missing"]:
            md.append("Missing template sections: " + ", ".join(d["sections_missing"]))
            md.append("")
        if d["citations_failed"]:
            md.append("### Unresolvable citations")
            md.append("| Doc line | Citation | Reason |")
            md.append("| --: | :-- | :-- |")
            for rec in d["citations_failed"][:100]:
                md.append(f"| {rec['doc_line']} | `{rec['citation']}` | {rec['reason']} |")
            md.append("")
        if d["citations_ok"]:
            md.append("### Resolved citations (verify by eye against the code)")
            md.append("| Doc line | Citation | Context at cited line |")
            md.append("| --: | :-- | :-- |")
            shown = 0
            seen_ctx = set()
            for span, line_no in spans:
                if shown >= 150:
                    md.append(f"| ... | {len(spans) - shown} more | |")
                    break
                rec = checker.check(span, line_no)
                if rec["ok"] and rec["citation"] not in seen_ctx:
                    seen_ctx.add(rec["citation"])
                    shown += 1
                    md.append(f"| {line_no} | `{span}` | {rec['context'] or '-'} |")
            md.append("")
        if d["node_maps"]["missing_maps"]:
            md.append("Node maps missing for blocks at lines: "
                      + ", ".join(d["node_maps"]["missing_maps"]))
            md.append("")
        if d["density_warnings"]:
            md.append("Density warnings: " + "; ".join(d["density_warnings"]))
            md.append("")

    report["overall"] = {"pass": overall_ok,
                         "status": "PASS" if overall_ok else "FAIL"}
    with open(os.path.join(vdir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    with open(os.path.join(vdir, "verification-report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    verdicts = ", ".join(f"{k}: {v['status']}" for k, v in report["docs"].items())
    print(f"OVERALL: {report['overall']['status']}  ({verdicts})")
    sys.exit(0 if overall_ok else 1)


if __name__ == "__main__":
    main()
