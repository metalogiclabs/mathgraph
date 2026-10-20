#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"
DIR="$ROOT/research/strata_bridge_v1"
EV="$DIR/evidence"
UP="$RUNNER_TEMP/strata-upstream"
ORIG="0bbe12d22650dc12dc4adc15249c965ba5ade8e3"
PATCH="4016549f846065b5cab405fc09cff9a35d13512f"
mkdir -p "$EV"

echo "STAGE=PREEXISTING_METHOD_PREFLIGHT"
python3 -m py_compile "$DIR/audit.py" "$DIR/baseline.py"
PYTHONPATH="$ROOT" python3 -c 'from mathgraph_check.warrant_resolution import Claim, Receipt, Route, resolve_graph; print("MATHGRAPH_ORIGINAL_RESOLVER_IMPORTED")'
sha256sum "$DIR/PROTOCOL.md" "$DIR/DenotationControl.lean" "$DIR/UnsafeBridge.lean" "$DIR/audit.py" "$DIR/baseline.py" "$DIR/replay.sh" > "$EV/method_sha256.txt"
python3 -c 'import json; print(json.dumps({"original":"0bbe12d22650dc12dc4adc15249c965ba5ade8e3","patched":"4016549f846065b5cab405fc09cff9a35d13512f","issue":1488,"patch_pr":1490,"lean":"v4.31.0"},sort_keys=True))' > "$EV/pins.json"

echo "STAGE=PREPARE_LEAN_AND_SOLVERS"
sudo apt-get update -qq
sudo apt-get install -y -qq z3 cvc5 libgmp-dev > "$EV/apt_packages.log" 2>&1
curl --fail --location --silent --show-error "https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh" -o "$EV/elan-init.sh"
sh "$EV/elan-init.sh" -y --default-toolchain none
export PATH="$HOME/.elan/bin:$PATH"

echo "STAGE=FETCH_PINNED_NATIVE_SOURCES"
git clone --quiet --filter=blob:none --no-checkout "https://github.com/strata-org/Strata.git" "$UP"
git -C "$UP" fetch --quiet --no-tags origin "$ORIG" "$PATCH"
git -C "$UP" checkout --quiet --detach "$ORIG"
test "$(git -C "$UP" rev-parse HEAD)" = "$ORIG"
cp "$UP/lean-toolchain" "$EV/upstream_lean_toolchain.txt"
grep -F 'v4.31.0' "$EV/upstream_lean_toolchain.txt"
cd "$UP"
lake --version | tee "$EV/lake_version.txt"

echo "STAGE=ORIGINAL_BUILD"
lake build Strata.MetaVerifier > "$EV/original_build.log" 2>&1 ||
  { tail -100 "$EV/original_build.log"; echo "FAIL_ORIGINAL_BUILD"; exit 1; }
echo "ORIGINAL_BUILD_GREEN"

echo "STAGE=ORIGINAL_DENOTATION_ORACLE"
lake env lean "$DIR/DenotationControl.lean" > "$EV/original_oracle.log" 2>&1 ||
  { cat "$EV/original_oracle.log"; echo "FAIL_ORIGINAL_ORACLE"; exit 1; }
cat "$EV/original_oracle.log"
grep -F "MATHGRAPH_SMT_DIV0=255" "$EV/original_oracle.log"
grep -F "MATHGRAPH_LEAN_DIV0=0" "$EV/original_oracle.log"

echo "STAGE=ORIGINAL_AXIOM_ASSISTED_PROBE"
lake env lean "$DIR/UnsafeBridge.lean" > "$EV/original_bridge.log" 2>&1 ||
  { cat "$EV/original_bridge.log"; echo "FAIL_ORIGINAL_EXPOSED_REPRO"; exit 1; }
cat "$EV/original_bridge.log"
grep -F '_genSMTVCs_tcbBridge' "$EV/original_bridge.log"
if grep -F 'sorryAx' "$EV/original_bridge.log"; then
  echo "FAIL_NON_KERNEL_ORIGINAL_PROBE"
  exit 1
fi
sed -n '/private def mkBitVecDiv /,/^$/p' "$UP/Strata/DL/SMT/Translate.lean" > "$EV/original_translate_excerpt.txt"
grep -F 'mkBitVecDiv' "$EV/original_translate_excerpt.txt"

echo "STAGE=PATCH_BUILD"
git -C "$UP" checkout --quiet --detach "$PATCH"
test "$(git -C "$UP" rev-parse HEAD)" = "$PATCH"
lake build Strata.MetaVerifier > "$EV/patched_build.log" 2>&1 ||
  { tail -100 "$EV/patched_build.log"; echo "FAIL_PATCH_BUILD"; exit 1; }
echo "PATCH_BUILD_GREEN"

echo "STAGE=PATCH_DENOTATION_CONTROL"
lake env lean "$DIR/DenotationControl.lean" > "$EV/patched_oracle.log" 2>&1 ||
  { cat "$EV/patched_oracle.log"; echo "FAIL_PATCH_ORACLE"; exit 1; }
cat "$EV/patched_oracle.log"

echo "STAGE=PATCH_UNCHANGED_NEGATIVE_PROBE"
set +e
lake env lean "$DIR/UnsafeBridge.lean" > "$EV/patched_bridge.log" 2>&1
probe_code=$?
set -e
printf '%s\n' "$probe_code" > "$EV/patched_bridge.exit"
cat "$EV/patched_bridge.log"
if [ "$probe_code" -eq 0 ]; then
  echo "FAIL_PATCH_ACCEPTED_FALSE_PROOF"
  exit 1
fi
grep -Eq 'error:|error\(' "$EV/patched_bridge.log" ||
  { echo "FAIL_PATCH_NO_LEAN_ERROR"; exit 1; }
grep -n -C 4 'smtUDiv' "$UP/Strata/DL/SMT/Translate.lean" > "$EV/patched_translate_excerpt.txt"
grep -F 'BitVec.smtUDiv' "$EV/patched_translate_excerpt.txt"
echo "PATCH_REJECTED_OLD_FALSE_PROOF"

echo "STAGE=MATHGRAPH_SELECTIVE_WARRANT_CLOSURE"
cd "$ROOT"
PYTHONPATH="$ROOT" python3 "$DIR/audit.py" "$EV" | tee "$EV/audit_stdout.log"
echo "STAGE=FINISHED"
