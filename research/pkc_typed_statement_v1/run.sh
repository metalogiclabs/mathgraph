#!/usr/bin/env bash
set -euo pipefail
WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PKC="$WORKSPACE/target"
V5="$WORKSPACE/frozen-v5"
OWN="$WORKSPACE/research/pkc_typed_statement_v1"
RESULTS="$OWN/results"
CASES="typed_match false_mismatch typed_mismatch wrong_citation unsupported true_unsupported no_statement"
PIN="e0deb453e05ffa63297d9704ceb47d0855193824"
test "$(git -C "$PKC" rev-parse HEAD)" = "$PIN"
test "$(cat "$PKC/lean-toolchain")" = "leanprover/lean4:v4.34.0"
test "$(git -C "$V5" rev-parse HEAD)" = "4691ae2de91958d5a366f636b4a329a938b76116"
: "${SYSML:?Missing pinned OpenSysML executable}"
mkdir -p "$RESULTS"
export PATH="$HOME/.elan/bin:$PATH"
cd "$PKC"
lake env lean "$V5/research/jpl_pkc_statement_v4/generate_api_inputs.lean" \
  2>&1 | tee "$RESULTS/generate-frozen-api.log"
lake env lean "$V5/research/jpl_pkc_statement_v5/emit_sysml_from_frozen_v4.lean" \
  2>&1 | tee "$RESULTS/emit-frozen-sysml.log"
MODEL_DIR="$PKC/.lake/build/sysml/typed-v1"
python3 "$OWN/make_cases.py" "$MODEL_DIR" "$PKC/.lake/build/sysml/claim-audit-v4" \
  2>&1 | tee "$RESULTS/freeze-inputs.log"
: > "$RESULTS/native-status.tsv"
for case in $CASES; do
  model="$MODEL_DIR/$case.sysml"
  cp "$model" "$RESULTS/$case.sysml"
  "$SYSML" -validate "$PKC/sysml/PKC.sysml" "$model" \
    > "$RESULTS/$case.validate.log" 2>&1
  "$SYSML" -convert api-json "$PKC/sysml/PKC.sysml" "$model" \
    > "$MODEL_DIR/$case.api.json" 2> "$RESULTS/$case.convert-stderr.log"
  cp "$MODEL_DIR/$case.api.json" "$RESULTS/$case.api.json"
  if SYSML="$SYSML" bash scripts/ingest-sysml.sh "$model" \
    > "$RESULTS/$case.ingest.log" 2>&1; then code=0; else code=$?; fi
  printf '%s\t%d\n' "$case" "$code" >> "$RESULTS/native-status.tsv"
  echo "PKC_V6_ORIGINAL_NATIVE case=$case exit=$code"
  test "$code" -eq 0 || { echo "PKC_V6_NATIVE_INGEST_FAILED case=$case"; exit 1; }
  grep -F '0 unverified citation(s)' "$RESULTS/$case.ingest.log" > /dev/null
  cp ".lake/build/sysml/Generated/M.lean" "$RESULTS/$case.Generated.lean"
  lake env lean "$RESULTS/$case.Generated.lean" > "$RESULTS/$case.kernel.log" 2>&1
  if test "$case" = no_statement; then
    grep -F -- '-- checked: PropertyKindCalculus.Iso80000.Part3.Edge.width_length' "$RESULTS/$case.Generated.lean" >/dev/null
  else
    case "$case" in
      typed_match) statement='PKC:Edge(width,length)'; decl='Edge.width_length';;
      false_mismatch) statement='False'; decl='Edge.width_length';;
      typed_mismatch) statement='PKC:Edge(width,height)'; decl='Edge.width_length';;
      wrong_citation) statement='PKC:Edge(width,length)'; decl='Edge.height_length';;
      unsupported) statement='The width is a length'; decl='Edge.width_length';;
      true_unsupported) statement='True'; decl='Edge.width_length';;
    esac
    grep -F -- "-- checked: PropertyKindCalculus.Iso80000.Part3.$decl — $statement" \
      "$RESULTS/$case.Generated.lean" > /dev/null
  fi
done
lake env lean "$OWN/Check.lean" > "$RESULTS/independent-typed.log" 2>&1 || {
  cat "$RESULTS/independent-typed.log"; exit 1;
}
cat "$RESULTS/independent-typed.log"
test -z "$(git diff --name-only)"
python3 "$OWN/verify.py" "$RESULTS"
python3 "$OWN/link_v1.py" "$RESULTS"
echo "PKC_V6_FULL_NATIVE_TYPED_CORRESPONDENCE_AUDIT_COMPLETE"
