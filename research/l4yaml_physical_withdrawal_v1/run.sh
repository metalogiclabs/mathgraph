#!/usr/bin/env bash
# Real source-native L4YAML three-lane physical configuration change:
# BASE -> exact one-line MUTANT -> byte-exact RESTORED.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$ROOT/target"
FROZEN="$ROOT/frozen-original/research/l4yaml_schema_style_v1"
OWN="$ROOT/research/l4yaml_physical_withdrawal_v1"
OUT="$OWN/results"
PIN="fdef03caf19e8862792034793da11020b39d6110"
test "$(git -C "$SRC" rev-parse HEAD)" = "$PIN"
test "$(git -C "$SRC" hash-object L4YAML/Output/Dump.lean)" = "e6495cba339246b1954f3d4be9dd286a564cb4c0"
test -z "$(git -C "$SRC" diff --name-only)"
test "$(git -C "$FROZEN" rev-parse HEAD 2>/dev/null || true)" != "replaced"
test "$(git -C "$ROOT/frozen-original" rev-parse HEAD)" = "03f8b16d24f4641483f7b3cc1004812dfefb4dbc"
test "$(git -C "$ROOT/frozen-original" hash-object research/l4yaml_schema_style_v1/Probe.lean)" = "81659ba21ccfdf6e1a43879c2318a8010f58ae55"
test "$(git -C "$ROOT/frozen-original" hash-object research/l4yaml_schema_style_v1/analyze.py)" = "1e701edbfac8ef6cd6f2b92dac28d6bc6639e7e2"
mkdir -p "$OUT"
export PATH="$HOME/.elan/bin:$PATH"
cd "$SRC"

lane() {
  local lane="$1"
  echo "L4YAML_V8_REAL_NATIVE_BUILD_BEGIN lane=$lane"
  lake build L4YAML.Schema.Api L4YAML.Schema.Deriving L4YAML.Output.Dump \
    > "$OUT/$lane-build.log" 2>&1 || {
      cat "$OUT/$lane-build.log"; exit 1; }
  grep -F 'Build completed successfully' "$OUT/$lane-build.log"
  echo "L4YAML_V8_REAL_NATIVE_BUILD_COMPLETE lane=$lane"
  lake env lean "$FROZEN/Probe.lean" \
    > "$OUT/$lane-lean.log" 2>&1 || {
      cat "$OUT/$lane-lean.log"; exit 1; }
  python3 "$OWN/audit.py" check \
    --root "$OUT" --target "$SRC" --original "$FROZEN" --lane "$lane"
}

lane BASE
python3 "$FROZEN/analyze.py" \
  --lean-log "$OUT/BASE-lean.log" \
  --out "$OUT/BASE-original-red-check.json" --expect original-red \
  > "$OUT/BASE-original-red-verifier.log" 2>&1
echo "L4YAML_V8_ORIGINAL_RED_VERIFIER_BASE_PASSED"
python3 "$OWN/mutate.py" --source "$SRC" --lane MUTANT --output "$OUT/physical-mutant.json"
test "$(git diff --name-only)" = "L4YAML/Output/Dump.lean"
lane MUTANT

# Mutant must NOT be mistaken for original RED or proposed fixed GREEN;
# each rejection is an expected *negative verifier* result.
if python3 "$FROZEN/analyze.py" \
  --lean-log "$OUT/MUTANT-lean.log" \
  --out "$OUT/MUTANT-invalid-original-red.json" --expect original-red \
  > "$OUT/MUTANT-original-red-verifier.log" 2>&1; then
  echo "SCIENTIFIC_FAILURE: mutant falsely admitted as unchanged original RED"; exit 1
fi
test ! -f "$OUT/MUTANT-invalid-original-red.json"
echo "L4YAML_V8_MUTANT_NOT_ORIGINAL_RED_VERIFIER_PASS"
if python3 "$FROZEN/analyze.py" \
  --lean-log "$OUT/MUTANT-lean.log" \
  --out "$OUT/MUTANT-invalid-fixed-green.json" --expect fixed-green \
  > "$OUT/MUTANT-fixed-green-verifier.log" 2>&1; then
  echo "SCIENTIFIC_FAILURE: policy mutant falsely admitted as fixed GREEN"; exit 1
fi
test ! -f "$OUT/MUTANT-invalid-fixed-green.json"
echo "L4YAML_V8_MUTANT_NOT_FIXED_GREEN_VERIFIER_PASS"

python3 "$OWN/mutate.py" --source "$SRC" --lane RESTORED --output "$OUT/physical-restored.json"
test -z "$(git diff --name-only)"
lane RESTORED
python3 "$FROZEN/analyze.py" \
  --lean-log "$OUT/RESTORED-lean.log" \
  --out "$OUT/RESTORED-original-red-check.json" --expect original-red \
  > "$OUT/RESTORED-original-red-verifier.log" 2>&1
echo "L4YAML_V8_ORIGINAL_RED_VERIFIER_RESTORED_PASSED"

python3 "$OWN/audit.py" finalize --root "$OUT"
python3 "$OWN/link_v1.py" --root "$OUT" \
  --core "$ROOT/research/cross_domain_correspondence_v1/protocol.py"
test -z "$(git diff --name-only)"
echo "L4YAML_V8_FULL_NATIVE_SELECTIVE_WARRANT_REQUALIFICATION_COMPLETE"
