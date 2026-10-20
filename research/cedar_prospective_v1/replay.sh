#!/usr/bin/env bash
set -euo pipefail
ROOT="$(pwd)"
DIR="$ROOT/research/cedar_prospective_v1"
EV="$DIR/evidence"
UP="$RUNNER_TEMP/cedar-prospective-source"
SPEC="$UP/cedar-spec"
RUST="$SPEC/cedar"
CORPUS="$SPEC/cedar-integration-tests"
SPEC_PIN="7893e685a91a6a391d609fd9940a1c13dcdf2472"
RUST_PIN="34db4c67641172b98e876ce79ef41277e29af433"
CORPUS_PIN="b157547fb8856911b293b7214768922c731878de"
mkdir -p "$EV"
echo "STAGE=LOCKED_METHOD_PREFLIGHT"
python3 -m py_compile "$DIR/audit.py" "$DIR/snapshot_fixture.py"
PYTHONPATH="$ROOT" python3 -c 'from mathgraph_check.warrant_resolution import Claim,Receipt,Route,resolve_graph; print("UNCHANGED_MATHGRAPH_RESOLVER_OK")'
sha256sum "$DIR/PROTOCOL.md" "$DIR/METADATA_LOCK.json" "$DIR/CORPUS_LOCK.json" "$DIR/audit.py" "$DIR/snapshot_fixture.py" "$DIR/replay.sh" > "$EV/method_sha256.txt"
python3 -c 'import json; print(json.dumps({"cedar_spec":"7893e685a91a6a391d609fd9940a1c13dcdf2472","cedar_rust":"34db4c67641172b98e876ce79ef41277e29af433","author_corpus":"b157547fb8856911b293b7214768922c731878de"},sort_keys=True))' > "$EV/pins.json"

echo "STAGE=PINNED_SOURCE_FETCH"
mkdir -p "$UP"
git clone -q --filter=blob:none --no-checkout https://github.com/cedar-policy/cedar-spec.git "$SPEC"
git -C "$SPEC" fetch -q --no-tags origin "$SPEC_PIN"
git -C "$SPEC" checkout -q --detach "$SPEC_PIN"
git clone -q --filter=blob:none --no-checkout https://github.com/cedar-policy/cedar.git "$RUST"
git -C "$RUST" fetch -q --no-tags origin "$RUST_PIN"
git -C "$RUST" checkout -q --detach "$RUST_PIN"
git clone -q --filter=blob:none --no-checkout https://github.com/cedar-policy/cedar-integration-tests.git "$CORPUS"
git -C "$CORPUS" fetch -q --no-tags origin "$CORPUS_PIN"
git -C "$CORPUS" checkout -q --detach "$CORPUS_PIN"
test "$(git -C "$SPEC" rev-parse HEAD)" = "$SPEC_PIN"
test "$(git -C "$RUST" rev-parse HEAD)" = "$RUST_PIN"
test "$(git -C "$CORPUS" rev-parse HEAD)" = "$CORPUS_PIN"
cp "$SPEC/lean-toolchain" "$EV/lean_version.txt"
grep -Fx 'leanprover/lean4:v4.34.1' "$EV/lean_version.txt"
python3 "$DIR/snapshot_fixture.py" "$CORPUS" "$EV" | tee "$EV/fixture_selection.log"

echo "STAGE=NATIVE_DEPENDENCY_SETUP"
sudo apt-get update -qq
sudo apt-get install -y -qq protobuf-compiler z3 cvc5 libgmp-dev clang > "$EV/apt.log" 2>&1
curl -fsSL "https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh" -o "$EV/elan_init.sh"
sh "$EV/elan_init.sh" -y --default-toolchain none
export PATH="$HOME/.elan/bin:$PATH"
rustup update stable > "$EV/rustup.log" 2>&1
rustup default stable >> "$EV/rustup.log" 2>&1
rustc --version | tee "$EV/rustc_version.txt"
cargo --version | tee "$EV/cargo_version.txt"
export CARGO_TARGET_DIR="$UP/target"
export CARGO_BUILD_JOBS=3

echo "STAGE=RUST_ORIGINAL_FIRST_AUTHOR_FIXTURE"
cd "$RUST"
cargo test -p cedar-testing --features integration-testing --test cedar-policy decimal_1 -- --nocapture > "$EV/rust_first.log" 2>&1 ||
  { tail -100 "$EV/rust_first.log"; echo "FAIL_RUST_FIRST_NATIVE"; exit 1; }
grep -F "tests/decimal/1.json" "$EV/rust_first.log"
grep -F "test result: ok." "$EV/rust_first.log"
echo "RUST_FIRST_FIXTURE_GREEN"

echo "STAGE=RUST_UNRELATED_NATIVE_CONTROL"
cargo test -p cedar-testing --features integration-testing --test cedar-policy decimal_2 -- --nocapture > "$EV/rust_unrelated.log" 2>&1 ||
  { tail -100 "$EV/rust_unrelated.log"; echo "FAIL_RUST_UNRELATED_CONTROL"; exit 1; }
grep -F "test result: ok." "$EV/rust_unrelated.log"
echo "RUST_UNRELATED_CONTROL_GREEN"

echo "STAGE=ORIGINAL_LEAN_FFI_STATIC_BUILD"
cd "$SPEC/cedar-lean"
bash "$SPEC/cedar-lean-ffi/build_lean_lib.sh" > "$EV/lean_build.log" 2>&1 ||
  { tail -120 "$EV/lean_build.log"; echo "FAIL_LEAN_ORIGINAL_BUILD"; exit 1; }
echo "LEAN_SOURCE_STATIC_BUILD_GREEN"
cp "$SPEC/cedar-lean/lake-manifest.json" "$EV/lean_dependency_manifest.json"

echo "STAGE=ORIGINAL_LEAN_AUTHORIZATION_FIXTURES"
cd "$SPEC/cedar-lean-ffi"
source ./set_env_vars.sh
cargo test --features integration-testing --test integration_tests integration_tests -- --nocapture > "$EV/lean_integration.log" 2>&1 ||
  { tail -120 "$EV/lean_integration.log"; echo "FAIL_LEAN_ORIGINAL_INTEGRATION"; exit 1; }
grep -F "tests/decimal/1.json" "$EV/lean_integration.log"
grep -F "test result: ok." "$EV/lean_integration.log"
echo "LEAN_FIRST_FIXTURE_GREEN"

echo "STAGE=MATHGRAPH_EXISTING_CONSEQUENCE_RESOLVER"
cd "$ROOT"
PYTHONPATH="$ROOT" python3 "$DIR/audit.py" "$EV" | tee "$EV/audit_stdout.log"
echo "STAGE=FINISHED"
