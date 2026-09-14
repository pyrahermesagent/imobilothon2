#!/usr/bin/env bash
# Selftest for the codebase-modeler skill scripts.
#
# What it proves, end to end, without any LLM in the loop:
#   1. inventory.py runs cleanly on the bundled fixture repo and emits
#      inventory.json + inventory.md.
#   2. verify.py PASSes (exit 0) on the bundled hand-written fixture outputs.
#   3. verify.py FAILs (exit 1) when a citation is deliberately broken
#      (out-of-range line number) — i.e. the mechanical check actually
#      catches defects instead of rubber-stamping.
#   4. inventory.py rejects an empty repository (exit 3).
#
# Usage:  bash scripts/selftest.sh
# Exit:   0 if every check passes, 1 otherwise.

set -u
cd "$(dirname "$0")/.."

PASS=0
FAIL=0

check() {
  # check <name> <ok:0|1>
  if [ "$2" -eq 0 ]; then
    echo "PASS  $1"
    PASS=$((PASS + 1))
  else
    echo "FAIL  $1"
    FAIL=$((FAIL + 1))
  fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --- 1. inventory on the fixture repo -------------------------------------
INV_OUT="$TMP/inventory"
python3 scripts/inventory.py tests/fixture-repo "$INV_OUT" > "$TMP/inv.log" 2>&1
rc=$?
ok=1
[ $rc -eq 0 ] && \
  [ -f "$INV_OUT/inventory.json" ] && \
  [ -f "$INV_OUT/inventory.md" ] && \
  python3 -c "import json,sys; json.load(open('$INV_OUT/inventory.json'))" > /dev/null 2>&1 \
  && ok=0
check "inventory.py: fixture repo -> exit 0, valid inventory.json + inventory.md" "$ok"
[ $ok -ne 0 ] && { echo "  rc=$rc"; sed 's/^/  /' "$TMP/inv.log" | tail -5; }

# --- 2. verify on the real fixture outputs ---------------------------------
python3 scripts/verify.py tests/fixture-output tests/fixture-repo > "$TMP/v1.log" 2>&1
rc=$?
check "verify.py: fixture outputs -> OVERALL PASS (exit 0)" "$([ $rc -eq 0 ] && echo 0 || echo 1)"
[ $rc -ne 0 ] && { sed 's/^/  /' "$TMP/v1.log" | tail -5; }

# --- 3. verify catches a broken citation -----------------------------------
BROKEN="$TMP/broken-outputs"
cp -r tests/fixture-output "$BROKEN"
# models.py has 29 lines; :7-999 is out of range and must be flagged.
sed -i 's|models\.py:7-20|models.py:7-999|g' "$BROKEN/ClassModel.md"
grep -q 'models.py:7-999' "$BROKEN/ClassModel.md"
check "selftest setup: broken citation injected into ClassModel.md" "$?"
python3 scripts/verify.py "$BROKEN" tests/fixture-repo > "$TMP/v2.log" 2>&1
rc=$?
grep -q 'unresolvable citation' "$BROKEN/verification/report.json" 2>/dev/null
check "verify.py: broken citation -> OVERALL FAIL (exit 1) + defect recorded" \
  "$([ $rc -eq 1 ] && echo 0 || echo 1)"
[ $rc -ne 1 ] && { sed 's/^/  /' "$TMP/v2.log" | tail -5; }

# --- 4. inventory rejects an empty repo ------------------------------------
EMPTY="$TMP/empty-repo"
mkdir -p "$EMPTY"
python3 scripts/inventory.py "$EMPTY" "$TMP/empty-out" > "$TMP/e.log" 2>&1
rc=$?
check "inventory.py: empty repo -> exit 3" "$([ $rc -eq 3 ] && echo 0 || echo 1)"
[ $rc -ne 3 ] && { echo "  rc=$rc"; sed 's/^/  /' "$TMP/e.log" | tail -5; }

echo "----------------------------------------"
echo "selftest: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ]
