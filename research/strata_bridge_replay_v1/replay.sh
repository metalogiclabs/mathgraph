#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"
DIR="$ROOT/research/strata_bridge_replay_v1"
E="$DIR/evidence"
SOURCE="${RUNNER_TEMP:-/tmp}/mathgraph-strata-upstream"
BASE="0bbe12d22650dc12dc4adc15249c965ba5ade8e3"
FIX="4016549f846065b5cab405fc09cff9a35d13512f"
mkdir -p "$E"

stage() { echo "STAGE=$1"; }
stage "PREFLIGHT"
python3 -m py_compile "$DIR/audit.py"
PYTHONPATH="$ROOT" python3 -c 'from mathgraph_check.warrant_resolution import Claim, Receipt, Route, resolve_graph; print("EXISTING_MATHGRAPH_RESOLVER_IMPORTED")'
python3 - "$DIR" <<'PY'
import pathlib, json,sys
p=pathlib.Path(sys.argv[1]); spec=json.loads((p/'protocol.json').read_text());assert spec['source_status']=='EXPOSED_TRAINING_REPLAY_NOT_PROSPECTIVE';assert spec['base_sha']!='';assert spec['repair_sha']!='';print('PINNED_PROTOCOL_VALID')
PY

echo 'STAGE=INSTALL_EXACT_TOOLS'
mkdir -p "$E/tools"
curl --fail --location --retry 3 --silent --show-error https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -o "$E/tools/elan-init.sh"
sh "$E/tools/elan-init.sh" -y --default-toolchain none
export PATH="$HOME/.elan/bin:$PATH"
# Match Strata's own action's published cvc5/z3 releases; use pinned versions.
CVC5_URL='https://github.com/cvc5/cvc5/releases/download/cvc5-1.3.4/cvc5-Linux-x86_64-static.zip'
Z3_URL='https://github.com/Z3Prover/z3/releases/download/z3-4.15.2/z3-4.15.2-x64-glibc-2.39.zip'
curl --fail --location --retry 3 --silent --show-error "$CVC5_URL" -o "$E/tools/cvc5.zip"
curl --fail --location --retry 3 --silent --show-error "$Z3_URL" -o "$E/tools/z3.zip"
sha256sum "$E/tools/cvc5.zip" "$E/tools/z3.zip" > "$E/tool_asset_hashes.txt"
unzip -q "$E/tools/cvc5.zip" -d "$E/tools"
unzip -q "$E/tools/z3.zip" -d "$E/tools"
export PATH="$E/tools/cvc5-Linux-x86_64-static/bin:$E/tools/z3-4.15.2-x64-glibc-2.39/bin:$PATH"
cvc5 --version | tee "$E/cvc5_version.txt"
z3 --version | tee "$E/z3_version.txt"

stage 'FROZEN_EXTERNAL_SMT_ORACLE'
# Two paired values of the same SMT-LIB operation: zero is UNSAT, all-ones SAT.
cvc5 --lang smt2 "$DIR/OracleClaimFalse.smt2" | tee "$E/oracle_bad.txt"
cvc5 --lang smt2 "$DIR/OracleClaimTrue.smt2" | tee "$E/oracle_good.txt"
test "$(tr -d '\r\n ' < "$E/oracle_bad.txt")" = 'unsat'
test "$(tr -d '\r\n ' < "$E/oracle_good.txt")" = 'sat'

stage 'UPSTREAM_EXACT_SOURCE'
if [ ! -e "$SOURCE/.git" ]; then
  git clone -q --filter=blob:none --no-checkout https://github.com/strata-org/Strata.git "$SOURCE"
fi
git -C "$SOURCE" fetch -q --depth=1 origin "$BASE" "$FIX"
git -C "$SOURCE" -c advice.detachedHead=false checkout -q --detach "$BASE"
test "$(git -C "$SOURCE" rev-parse HEAD)" = "$BASE"
test "$(cat "$SOURCE/lean-toolchain")" = 'leanprover/lean4:v4.31.0'
sha256sum "$SOURCE/lake-manifest.json" | tee "$E/lake_manifest_base.txt"
cp "$SOURCE/lake-manifest.json" "$E/lake_manifest_base.json"
cd "$SOURCE"
lake --version | tee "$E/lake_version.txt"

stage 'BASE_NATIVE_LEAN_BUILD'
lake build Strata 2>&1 | tee "$E/base_build.txt"
stage 'BASE_FALSE_THEOREM_REPLAY'
lake env lean "$DIR/BugBefore.lean" 2>&1 | tee "$E/base_bug_lean.txt"
grep -Fq "Strata.oops" "$E/base_bug_lean.txt"
grep -Fq "_genSMTVCs_tcbBridge" "$E/base_bug_lean.txt"
stage 'BASE_POSITIVE_CONTROL'
lake env lean StrataTest/Languages/Core/Examples/GenSMTVCsAxioms.lean 2>&1 | tee "$E/base_control_lean.txt"
grep -Fq "_genSMTVCs_tcbBridge" "$E/base_control_lean.txt"

stage 'REPAIR_EXACT_PIN'
git -c advice.detachedHead=false checkout -q --detach "$FIX"
test "$(git rev-parse HEAD)" = "$FIX"
test "$(cat lean-toolchain)" = 'leanprover/lean4:v4.31.0'
sha256sum lake-manifest.json | tee "$E/lake_manifest_fix.txt"
cmp "$E/lake_manifest_base.json" lake-manifest.json
stage 'REPAIR_NATIVE_LEAN_BUILD'
lake build Strata 2>&1 | tee "$E/repair_build.txt"

stage 'REPAIR_NATIVE_POSITIVE_AND_DATATYPE_CONTROL'
cp StrataTest/Languages/Core/Examples/GenSMTVCsDenotation.lean "$E/GenSMTVCsDenotation.fix.lean"
lake env lean StrataTest/Languages/Core/Examples/GenSMTVCsDenotation.lean 2>&1 | tee "$E/repair_good_lean.txt"

stage 'REPAIR_MUST_REJECT_FALSE_PROOF'
set +e
lake env lean "$DIR/BugBefore.lean" > "$E/repair_bad_expected_rejection.txt" 2>&1
CODE=$?
set -e
cat "$E/repair_bad_expected_rejection.txt"
if [ "$CODE" -eq 0 ]; then
  echo 'FAIL: REPAIRED STRATA STILL COMPILES FALSE THEOREM' >&2
  exit 21
fi
grep -Fq 'smtUDiv' "$E/repair_bad_expected_rejection.txt"
grep -q 'error' "$E/repair_bad_expected_rejection.txt"
printf '%s\n' "$CODE" > "$E/repair_bad_exit_code.txt"

stage 'QUALIFY_SOURCE_AND_OUTPUT_IDENTITIES'
cd "$ROOT"
python3 - "$DIR" "$E" "$BASE" "$FIX" <<'PY'
import sys, pathlib, hashlib, json
root=pathlib.Path(sys.argv[1]);ev=pathlib.Path(sys.argv[2]);base,fix=sys.argv[3:5]
files=("BugBefore.lean","OracleClaimFalse.smt2","OracleClaimTrue.smt2","protocol.json","base_bug_lean.txt","base_control_lean.txt","repair_bad_expected_rejection.txt","repair_good_lean.txt","repair_bad_exit_code.txt","oracle_bad.txt","oracle_good.txt","GenSMTVCsDenotation.fix.lean")
sha={}
for f in files:
 p=(root if f in ("BugBefore.lean","OracleClaimFalse.smt2","OracleClaimTrue.smt2","protocol.json") else ev)/f
 sha[f]=hashlib.sha256(p.read_bytes()).hexdigest()
manifest={"schema":"mathgraph.exposed-strata-source-identities.v1","base_revision":base,"repair_revision":fix,"base_toolchain":"leanprover/lean4:v4.31.0","repair_toolchain":"leanprover/lean4:v4.31.0","files_sha256":sha}
(ev/'result_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print('FROZEN_OUTPUT_SHA256',hashlib.sha256((ev/'result_manifest.json').read_bytes()).hexdigest())
PY

stage 'MATHGRAPH_PHYSICAL_AUTHORITY_WITHDRAWAL'
PYTHONPATH="$ROOT" python3 "$DIR/audit.py" "$E" | tee "$E/audit_stdout.txt"
echo 'STAGE=FULL_NATIVE_AND_WARRANT_REPLAY_PASSED'