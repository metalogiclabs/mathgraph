#!/usr/bin/env bash
set -euo pipefail
RESEARCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$RESEARCH_DIR/../.." && pwd)"
JPL="$WORKSPACE/target"
RUN="$WORKSPACE/research/jpl_pkc_statement_v5/results"
mkdir -p "$RUN"
PIN="e0deb453e05ffa63297d9704ceb47d0855193824"
test "$(git -C "$JPL" rev-parse HEAD)" = "$PIN"
test "$(cat "$JPL/lean-toolchain")" = "leanprover/lean4:v4.34.0"
: "${SYSML:?SYSML must identify verified pinned OpenSysML executable}"
test -x "$SYSML"
"$SYSML" --version 2>&1 | tee "$RUN/opensysml-version.txt"

cd "$JPL"
LAKE="$HOME/.elan/bin/lake"
# JPL's own ingest-sysml.sh invokes plain 'lake'. Keep the source unchanged;
# make the pinned toolchain available via the runner environment instead.
export PATH="$HOME/.elan/bin:$PATH"
command -v lake >/dev/null
"$LAKE" env lean "$WORKSPACE/research/jpl_pkc_statement_v4/generate_api_inputs.lean" \
  2>&1 | tee "$RUN/frozen-fixtures.log"
"$LAKE" env lean "$RESEARCH_DIR/emit_sysml_from_frozen_v4.lean" \
  2>&1 | tee "$RUN/emit-original-sysml.log"
SRC="$JPL/.lake/build/sysml/claim-audit-v4"

cp "$SRC"/{no_statement,false_statement}.sysml "$RUN/"
for test_case in no_statement false_statement; do
  model="$SRC/$test_case.sysml"
  "$SYSML" -validate "$JPL/sysml/PKC.sysml" "$model" \
    > "$RUN/convert-${test_case}-validate.log" 2>&1
  "$SYSML" -convert api-json "$JPL/sysml/PKC.sysml" "$model" \
    > "$RUN/convert-${test_case}-api.json" \
    2> "$RUN/convert-${test_case}-stderr.log"
  python3 - "$RUN/convert-${test_case}-api.json" "$test_case" <<'PY'
import json,sys
p,case=sys.argv[1:]
d=json.load(open(p))
if not isinstance(d,list): raise SystemExit("NOT_API_ELEMENT_ARRAY")
texts=[x.get("value") for x in d if x.get("@type")=="LiteralString"]
want="False" if case=="false_statement" else "width"
if want not in texts: raise SystemExit(f"CONVERTER_DROPPED_LITERAL case={case}: {texts}")
citation="PropertyKindCalculus.Iso80000.Part3.Edge.width_length"
if citation not in texts: raise SystemExit(f"CONVERTER_DROPPED_PROOF_CITATION case={case}")
print(f"CONVERTER_RETAINED_METADATA case={case} source_literals={len(texts)}")
PY
done

run_case() {
  local lane="$1" kind="$2"
  local input="$SRC/$kind.sysml"
  local result="$RUN/${lane}-${kind}.log"
  local ret
  if SYSML="$SYSML" bash scripts/ingest-sysml.sh "$input" > "$result" 2>&1; then
    ret=0
  else
    ret=$?
  fi
  printf '%s\t%s\t%d\n' "$lane" "$kind" "$ret" >> "$RUN/native-results.tsv"
  printf 'FULL_TEXT_RESULT lane=%s case=%s exit=%d\n' "$lane" "$kind" "$ret"
}
: > "$RUN/native-results.tsv"
run_case original no_statement
run_case original false_statement
grep -F -- '-- checked: PropertyKindCalculus.Iso80000.Part3.Edge.width_length — False' \
  .lake/build/sysml/Generated/M.lean
cp .lake/build/sysml/Generated/M.lean "$RUN/OriginalFalseGenerated.lean"
"$LAKE" env lean "$RUN/OriginalFalseGenerated.lean" \
  2>&1 | tee "$RUN/original-Lean-kernel.log"

python3 "$WORKSPACE/research/jpl_pkc_statement_v4/strict_patch.py" "$JPL" \
  --receipt "$RUN/policy-patch.json"
"$LAKE" build Interchange 2>&1 | tee "$RUN/strict-build.log"
run_case strict no_statement
run_case strict false_statement

git checkout -- interchange/PropertyKindCalculus/Interchange/Harvest.lean
test -z "$(git diff --name-only)"
"$LAKE" build Interchange 2>&1 | tee "$RUN/withdraw-build.log"
run_case withdrawn false_statement

python3 "$RESEARCH_DIR/verify_results.py" "$RUN"
echo "V5_FULL_SYSML_TO_LEAN_CAUSAL_AUDIT_COMPLETE"
