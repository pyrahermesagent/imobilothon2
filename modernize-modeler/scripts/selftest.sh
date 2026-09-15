#!/usr/bin/env bash
# selftest.sh — mechanical smoke test for modernize-modeler scripts + fixtures.
# No network, no LLM. Exercises intake.py and verify.py against the tests/ fixtures.
# Usage: bash scripts/selftest.sh
set -u
cd "$(dirname "$0")/.."

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0
ok()   { echo "ok   - $1"; PASS=$((PASS+1)); }
bad()  { echo "FAIL - $1"; FAIL=$((FAIL+1)); }

# jval <file.json> <dot.path>  — print a scalar from a JSON file
jval() {
  python3 -c 'import json, sys
d = json.load(open(sys.argv[1]))
cur = d
for p in sys.argv[2].split("."):
    cur = cur[int(p)] if isinstance(cur, list) else cur[p]
print(cur)' "$1" "$2" 2>/dev/null
}

# Shared: templates dir for intake (intake only needs the six .md names to exist)
mkdir -p "$TMP/templates"
cp tests/fixture-source/*.md "$TMP/templates/"

# (a) intake: happy path
python3 scripts/intake.py tests/fixture-source "$TMP/mod-a" "$TMP/templates" >"$TMP/a.out" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && [ "$(jval "$TMP/mod-a/intake.json" total_unverified)" = "6" ]; then
  ok "intake happy path (rc=0, total_unverified=6)"
else
  bad "intake happy path (rc=$rc, total_unverified=$(jval "$TMP/mod-a/intake.json" total_unverified 2>/dev/null))"
fi

# (b) intake: missing source doc is rejected
mkdir -p "$TMP/src-missing"
cp tests/fixture-source/*.md "$TMP/src-missing/"
rm "$TMP/src-missing/DomainModel.md"
err=$(python3 scripts/intake.py "$TMP/src-missing" "$TMP/mod-b" "$TMP/templates" 2>&1 >/dev/null)
rc=$?
if [ "$rc" -eq 2 ] && printf '%s' "$err" | grep -q 'DomainModel.md'; then
  ok "intake rejects missing DomainModel.md (rc=2, named on stderr)"
else
  bad "intake rejects missing DomainModel.md (rc=$rc, stderr=$err)"
fi

# (c) verify: happy path on a copy (verify.py writes into its first arg)
rm -rf "$TMP/mod-c" && cp -r tests/fixture-mod "$TMP/mod-c"
out=$(python3 scripts/verify.py "$TMP/mod-c" tests/fixture-source tests/fixture-repo 2>&1)
rc=$?
if [ "$rc" -eq 0 ] && [ "$(jval "$TMP/mod-c/verification/report.json" overall.pass)" = "True" ] && printf '%s' "$out" | grep -q 'OVERALL: PASS'; then
  ok "verify happy path (rc=0, overall.pass=true, OVERALL: PASS)"
else
  bad "verify happy path (rc=$rc, pass=$(jval "$TMP/mod-c/verification/report.json" overall.pass 2>/dev/null), out=$out)"
fi

# (d) verify: unknown plan id must fail and be reported
rm -rf "$TMP/mod-d" && cp -r tests/fixture-mod "$TMP/mod-d"
printf '\nSee M-99 for the dropped feature.\n' >> "$TMP/mod-d/DomainModel.md"
python3 scripts/verify.py "$TMP/mod-d" tests/fixture-source tests/fixture-repo >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 1 ] && grep -q 'M-99' "$TMP/mod-d/verification/report.json"; then
  ok "verify flags unknown id M-99 (rc=1, present in report.json)"
else
  bad "verify flags unknown id M-99 (rc=$rc)"
fi

# (e) verify: out-of-range citation span must fail (guard: span must exist first)
if ! grep -q 'models\.py:7-20' tests/fixture-mod/Specification.md; then
  bad "selftest guard: tests/fixture-mod/Specification.md no longer contains models.py:7-20 — case (e) premise stale"
else
  rm -rf "$TMP/mod-e" && cp -r tests/fixture-mod "$TMP/mod-e"
  sed -i 's/models\.py:7-20/models.py:7-999/g' "$TMP/mod-e/Specification.md"
  python3 scripts/verify.py "$TMP/mod-e" tests/fixture-source tests/fixture-repo >/dev/null 2>&1
  rc=$?
  if [ "$rc" -eq 1 ] && grep -q 'file not found (repo and source)' "$TMP/mod-e/verification/report.json"; then
    ok "verify flags out-of-range span models.py:7-999 (rc=1, reason in report.json)"
  else
    bad "verify flags out-of-range span (rc=$rc)"
  fi
fi

# (f) verify without a repo dir: repo citations skipped, still overall pass
rm -rf "$TMP/mod-f" && cp -r tests/fixture-mod "$TMP/mod-f"
python3 scripts/verify.py "$TMP/mod-f" tests/fixture-source >/dev/null 2>&1
rc=$?
allskipped=$(python3 -c 'import json
d = json.load(open("'"$TMP"'/mod-f/verification/report.json"))
print(all(c["citations"]["skipped"] > 0 for c in d["docs"].values()))')
if [ "$rc" -eq 0 ] && [ "$(jval "$TMP/mod-f/verification/report.json" overall.pass)" = "True" ] && [ "$allskipped" = "True" ]; then
  ok "verify no-repo mode (rc=0, pass=true, every doc skipped>0)"
else
  bad "verify no-repo mode (rc=$rc, pass=$(jval "$TMP/mod-f/verification/report.json" overall.pass 2>/dev/null), allskipped=$allskipped)"
fi

echo
echo "selftest: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
