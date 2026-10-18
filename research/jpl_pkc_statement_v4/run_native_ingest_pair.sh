#!/usr/bin/env bash
# Replay the exact frozen six API-JSON cases through JPL's actual ingest entrypoint.
# Side effects are restricted to an ephemeral checkout and CI evidence artifacts.
set -euo pipefail

RESEARCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$RESEARCH_DIR/../.." && pwd)"
TARGET="$WORKSPACE/target"
EVIDENCE="$WORKSPACE/research/jpl_pkc_statement_v4/results"
mkdir -p "$EVIDENCE"
PIN="e0deb453e05ffa63297d9704ceb47d0855193824"
test "$(git -C "$TARGET" rev-parse HEAD)" = "$PIN"
test "$(cat "$TARGET/lean-toolchain")" = "leanprover/lean4:v4.34.0"

cd "$TARGET"
LAKE="$HOME/.elan/bin/lake"
CASES="no_statement false_statement true_statement missing_declaration data_citation axiom_citation"

"$LAKE" env lean "$RESEARCH_DIR/generate_api_inputs.lean" \
  2>&1 | tee "$EVIDENCE/api-fixture-generation.log"
for test in $CASES; do
  test -s ".lake/build/sysml/claim-audit-v4/$test.api.json"
done
sha256sum .lake/build/sysml/claim-audit-v4/*.api.json \
  > "$EVIDENCE/fixtures.sha256"
cp -a .lake/build/sysml/claim-audit-v4 "$EVIDENCE/frozen-api-inputs"

run_lane() {
  local lane="$1" case="$2"
  local input="$TARGET/.lake/build/sysml/claim-audit-v4/$case.api.json"
  local out="$EVIDENCE/${lane}-${case}.log"
  local gen="$TARGET/.lake/build/sysml/claim-audit-v4/${lane}-${case}.generated.txt"
  local ret
  if PKC_INGEST="$input" PKC_INGEST_OUT="$gen" \
    "$LAKE" env lean scripts/ingest-sysml.lean > "$out" 2>&1; then
    ret=0
  else
    ret=$?
  fi
  printf '%s\t%s\t%d\n' "$lane" "$case" "$ret" >> "$EVIDENCE/native-results.tsv"
  printf 'RESULT lane=%s case=%s exit=%d\n' "$lane" "$case" "$ret"
}

: > "$EVIDENCE/native-results.tsv"
echo "BASELINE_INTAKE_START pinned=$PIN"
for testcase in $CASES; do
  run_lane original "$testcase"
  if [ "$testcase" = "false_statement" ]; then
    test -f .lake/build/sysml/Generated/M.lean
    grep -F -- '-- checked: PropertyKindCalculus.Iso80000.Part3.Edge.width_length — False' \
      .lake/build/sysml/Generated/M.lean
    cp .lake/build/sysml/Generated/M.lean "$EVIDENCE/OriginalFalseComment.lean"
    "$LAKE" env lean "$EVIDENCE/OriginalFalseComment.lean" \
      2>&1 | tee "$EVIDENCE/original-generated-lean.log"
  fi
done

python3 "$RESEARCH_DIR/strict_patch.py" "$TARGET" \
  --receipt "$EVIDENCE/strict-patch-receipt.json"
"$LAKE" build Interchange 2>&1 | tee "$EVIDENCE/strict-rebuild.log"
echo "STRICT_INTAKE_START"
for testcase in $CASES; do
  run_lane strict "$testcase"
done

# Causal ablation: physically withdraw ONLY the new policy, then ensure the
# original false-statement acceptance returns, with the source checkout clean.
git checkout -- interchange/PropertyKindCalculus/Interchange/Harvest.lean
test -z "$(git diff --name-only)"
"$LAKE" build Interchange 2>&1 | tee "$EVIDENCE/withdraw-rebuild.log"
run_lane withdrawn false_statement

python3 "$RESEARCH_DIR/verify_results.py" \
  --tsv "$EVIDENCE/native-results.tsv" \
  --result "$EVIDENCE/PINNED_RESULT.json" \
  --pin "$PIN"

echo "V4_COMPLETE: source-exact paired native API ingestion and withdrawal PASS"
