#!/usr/bin/env bash
set -euo pipefail
ROOT="$(pwd)"
DIR="$ROOT/research/aeneas_drop_claim_v1"
EV="$DIR/evidence"
mkdir -p "$EV"/generated_drop "$EV"/generated_control "$EV"/verified
echo "STAGE=PINNED_NATIVE_SETUP"
printf '%s\n' "Source pin: https://github.com/AeneasVerif/aeneas/tree/d119a474f852781f8ae88a85424f2f8ba8407b82" > "$EV/source_pins.txt"
printf '%s\n' "Charon pin declared by Aeneas: 798016509139eb51f0d764645f76d068d34ba5f6" >> "$EV/source_pins.txt"
printf '%s\n' "Lean: v4.31.0; Rust: nightly-2026-09-17" >> "$EV/source_pins.txt"
sha256sum "$DIR/one_guard.rs" "$DIR/replay.sh" "$DIR/audit.py" > "$EV/local_source_hashes.txt"
rustup toolchain install nightly-2026-09-17 --profile minimal --component rustc-dev --component llvm-tools --component rust-src
rustc +nightly-2026-09-17 --version | tee "$EV/rustc_version.txt"
rustc +nightly-2026-09-17 --edition=2021 "$DIR/one_guard.rs" -o "$EV/native"
"$EV/native" | tee "$EV/native_output.txt"
grep -Fx 'NATIVE_DROP=7' "$EV/native_output.txt"
grep -Fx 'NATIVE_CONTROL=0' "$EV/native_output.txt"

echo "STAGE=RELEASE_ASSET"
mkdir -p "$EV/toolchain"
curl --fail --location --retry 3 --silent --show-error \
  "https://github.com/AeneasVerif/aeneas/releases/download/nightly-2026.10.12-d119a47/aeneas-linux-x86_64.tar.gz" \
  -o "$EV/aeneas-linux-x86_64.tar.gz"
sha256sum "$EV/aeneas-linux-x86_64.tar.gz" | tee "$EV/release_sha256.txt"
tar -xf "$EV/aeneas-linux-x86_64.tar.gz" -C "$EV/toolchain"
rm "$EV/aeneas-linux-x86_64.tar.gz"
ls -la "$EV/toolchain" | tee "$EV/release_contents.txt"
"$EV/toolchain/aeneas" -version | tee "$EV/aeneas_version.txt"
test -x "$EV/toolchain/charon"
export PATH="$EV/toolchain:$PATH"

echo "STAGE=REAL_CHARON_EXTRACTION"
mkdir -p "$EV/llbc" 
cd "$EV/llbc"
charon rustc --start-from crate::fn0 --preset aeneas --dest-file drop.llbc -- --edition 2021 "$DIR/one_guard.rs"
charon rustc --start-from crate::control --preset aeneas --dest-file control.llbc -- --edition 2021 "$DIR/one_guard.rs"
find . -maxdepth 1 -type f -printf '%f %s bytes\n' | sort | tee "$EV/llbc_inventory.txt"
test -s drop.llbc
test -s control.llbc

echo "STAGE=REAL_AENEAS_TRANSLATION"
"$EV/toolchain/aeneas" -backend lean -no-progress-bar -dest "$EV/generated_drop" "$EV/llbc/drop.llbc"
"$EV/toolchain/aeneas" -backend lean -no-progress-bar -dest "$EV/generated_control" "$EV/llbc/control.llbc"
find "$EV/generated_drop" "$EV/generated_control" -type f -printf '%p %s bytes\n' | sort | tee "$EV/generated_inventory.txt"
find "$EV/generated_drop" "$EV/generated_control" -type f -name '*.lean' -print0 | xargs -0 sha256sum > "$EV/generated_sha256.txt"
echo "STAGE=LEAN_SETUP"
curl --fail --location --retry 3 --silent --show-error \
  "https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh" \
  -o "$EV/elan-init.sh"
sh "$EV/elan-init.sh" -y --default-toolchain none
export PATH="$HOME/.elan/bin:$PATH"
cd "$EV/toolchain/backends/lean"
lake --version | tee "$EV/lake_version.txt"
lake update
# The official Aeneas release has precompiled Lean module archives.
curl --fail --location --retry 3 --silent --show-error \
  "https://github.com/AeneasVerif/aeneas/releases/download/nightly-2026.10.12-d119a47/lean-build-aeneas-x86_64-unknown-linux-gnu.tar.gz" \
  -o "$EV/lean-build-aeneas.tar.gz"
sha256sum "$EV/lean-build-aeneas.tar.gz" | tee "$EV/lean_release_sha256.txt"
lake unpack "$EV/lean-build-aeneas.tar.gz"
lake exe cache get
lake build Aeneas

echo "STAGE=LEAN_KERNEL_REPLAY"
python3 "$DIR/prepare_checks.py" "$EV"
while IFS= read -r generated_file; do
  lake env lean "$generated_file" > /dev/null
done < "$EV/drop_files.txt"
while IFS= read -r generated_file; do
  lake env lean "$generated_file" > /dev/null
done < "$EV/control_files.txt"
lake env lean "$EV/verified/DropVerified.lean" | tee "$EV/lean_drop_check.txt"
lake env lean "$EV/verified/ControlVerified.lean" | tee "$EV/lean_control_check.txt"

echo "STAGE=EXISTING_MATHGRAPH_CLOSURE"
cd "$ROOT"
python3 "$DIR/audit.py" "$EV" | tee "$EV/audit_stdout.txt"
echo "STAGE=FINISHED"
