#!/usr/bin/env python3
"""Modernize Modeler - intake (Phase 0, deterministic).

Usage:  python3 intake.py <src_dir> <mod_dir> <templates_dir>

Validates that <src_dir> is a usable codebase-modeler output directory:
  - all six artifacts are present (Specification.md, ClassModel.md, DatabaseModel.md,
    DomainModel.md, UseCaseModel.md, ActivityDiagram.md);
  - all six templates are present in <templates_dir>.
Detects the optional inputs the codebase-modeler run left behind (the pinned .repo
clone, plan.json, inventory.json/md, evidence/*.json, SUMMARY.md, verification/*) and
the per-artifact UNVERIFIED marker counts (the assumption/issue workload the
modernization plan must close).
Writes: <mod_dir>/intake.json
Exit:   0 ready | 2 missing required inputs (the list is printed)
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

DOCS = ["Specification.md", "ClassModel.md", "DatabaseModel.md", "DomainModel.md",
        "UseCaseModel.md", "ActivityDiagram.md"]

EVIDENCE = ["db.json", "classes.json", "flows.json", "usecases.json", "domain.json"]


def unverified_count(path):
    """Number of lines containing an UNVERIFIED marker in a source artifact."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return sum(1 for line in f if "UNVERIFIED" in line)
    except OSError:
        return 0


def main():
    if len(sys.argv) != 4:
        print("usage: intake.py <src_dir> <mod_dir> <templates_dir>", file=sys.stderr)
        sys.exit(2)
    src, mod, tpls = [a.rstrip("/") for a in sys.argv[1:4]]

    if not os.path.isdir(src):
        print(f"ERROR: source output dir not found: {src}", file=sys.stderr)
        print("Expected the codebase-modeler output directory, e.g. output/<repo-name>/.",
              file=sys.stderr)
        sys.exit(2)

    missing = [d for d in DOCS if not os.path.isfile(os.path.join(src, d))]
    missing_tpl = [d for d in DOCS if not os.path.isfile(os.path.join(tpls, d))]
    if missing or missing_tpl:
        print("ERROR: required inputs missing:", file=sys.stderr)
        for d in missing:
            print(f"  - {src}/{d} (source artifact)", file=sys.stderr)
        for d in missing_tpl:
            print(f"  - {tpls}/{d} (template)", file=sys.stderr)
        sys.exit(2)

    # Pinned repo: the codebase-modeler clone under <src>/.repo, if it survived.
    repo = os.path.join(src, ".repo")
    repo_dir, repo_sha = None, None
    if os.path.isdir(repo):
        repo_dir = repo
        try:
            repo_sha = subprocess.run(
                ["git", "-C", repo, "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=15).stdout.strip() or None
        except (OSError, subprocess.SubprocessError):
            pass
        if not repo_sha:
            repo_sha = "n/a (no git metadata)"

    def have(rel):
        return os.path.isfile(os.path.join(src, rel))

    evidence_dir = os.path.join(src, "evidence")
    optional = {
        "repo": repo_dir is not None,
        "plan": have("plan.json"),
        "inventory_json": have("inventory.json"),
        "inventory_md": have("inventory.md"),
        "evidence": all(os.path.isfile(os.path.join(evidence_dir, e)) for e in EVIDENCE),
        "summary": have("SUMMARY.md"),
        "verification": have(os.path.join("verification", "report.json")),
    }

    out = {
        "src_dir": src,
        "mod_dir": mod,
        "templates_dir": tpls,
        "repo_dir": repo_dir,
        "repo_sha": repo_sha,
        "artifacts": DOCS,
        "optional_inputs": optional,
        "unverified_counts": {d: unverified_count(os.path.join(src, d)) for d in DOCS},
        "total_unverified": sum(unverified_count(os.path.join(src, d)) for d in DOCS),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    os.makedirs(mod, exist_ok=True)
    with open(os.path.join(mod, "intake.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    mode = "full inputs" if all(optional.values()) else \
        "docs-only" if not optional["repo"] else "partial inputs"
    print(f"INTAKE OK  src={src}  repo_sha={repo_sha or 'n/a'}  mode={mode}  "
          f"unverified_markers={out['total_unverified']}  -> {os.path.join(mod, 'intake.json')}")
    sys.exit(0)


if __name__ == "__main__":
    main()
