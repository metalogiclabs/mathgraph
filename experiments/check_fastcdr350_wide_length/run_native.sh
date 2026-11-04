#!/usr/bin/env bash
set -euo pipefail

# Independent, no-secret replay of two immutable public Fast-CDR revisions.
# Exit 1 of the original binaries is the expected negative result, never a build failure.
BASE_SHA=e92fa060825c21572f56a44656c02cbe2b06069c
HEAD_SHA=48f0a809f7b04566ef5c1e96ad216ba76fb8c68a
FIXTURE_SHA=619c068b48c95439818f630d47ee2de88d48e0034311c503182639b22bb7fd84
CONFIG_SHA=13ef0f78d2bf5b57627bbd1f9b2cadc4057fead7873e3780381d6ae96e49eea3
PATCH_SHA=4ec98b70295a05decf5e745971fa57ffa39fb68471c3a61ee8e164fd6758958c

CHECK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$CHECK_DIR/../.." && pwd)"
OUTPUT_DIR="$PROJECT_DIR/artifacts/check_fastcdr350_wide_length_v1"
TRIAL_DIR="$(mktemp -d)"
mkdir -p "$OUTPUT_DIR"

require_digest() {
    local actual
    actual="$(sha256sum "$1" | cut -d ' ' -f 1)"
    [[ "$actual" == "$2" ]] || { echo "Fixture hash mismatch: $1" >&2; exit 3; }
}
require_count() {
    local actual
    actual="$(grep -c "^$2" "$1" || true)"
    [[ "$actual" == "$3" ]] || {
        echo "Wrong count in $1: $2 got=$actual expected=$3" >&2
        exit 4
    }
}

require_digest "$CHECK_DIR/wide_length_boundary.cpp" "$FIXTURE_SHA"
require_digest "$CHECK_DIR/config/fastcdr/config.h" "$CONFIG_SHA"
require_digest "$CHECK_DIR/wide_length_guard.patch" "$PATCH_SHA"

git init -q "$TRIAL_DIR/source"
git -C "$TRIAL_DIR/source" remote add origin https://github.com/eProsima/Fast-CDR.git
git -C "$TRIAL_DIR/source" fetch -q --depth 1 --no-tags origin "$BASE_SHA" "$HEAD_SHA"
git -C "$TRIAL_DIR/source" checkout -q --detach "$HEAD_SHA"
git -C "$TRIAL_DIR/source" worktree add -q --detach "$TRIAL_DIR/base" "$BASE_SHA"
git -C "$TRIAL_DIR/source" worktree add -q --detach "$TRIAL_DIR/fixed" "$HEAD_SHA"

[[ "$(git -C "$TRIAL_DIR/base" rev-parse HEAD)" == "$BASE_SHA" ]]
[[ "$(git -C "$TRIAL_DIR/source" rev-parse HEAD)" == "$HEAD_SHA" ]]
[[ "$(git -C "$TRIAL_DIR/fixed" rev-parse HEAD)" == "$HEAD_SHA" ]]
[[ -z "$(git -C "$TRIAL_DIR/base" status --porcelain)" ]]
[[ -z "$(git -C "$TRIAL_DIR/source" status --porcelain)" ]]

git -C "$TRIAL_DIR/fixed" apply "$CHECK_DIR/wide_length_guard.patch"
git -C "$TRIAL_DIR/fixed" diff --check
git -C "$TRIAL_DIR/fixed" diff -- src/cpp/Cdr.cpp > "$OUTPUT_DIR/local-candidate-only.patch"

{
    echo "Subject: eProsima/Fast-CDR PR #350"
    echo "Base: $BASE_SHA"
    echo "Head: $HEAD_SHA"
    echo "Fixture SHA256: $FIXTURE_SHA"
    echo "Generated config SHA256: $CONFIG_SHA"
    echo "Candidate guard SHA256: $PATCH_SHA"
    echo "Compiler: $(g++ --version | head -1)"
    echo "System: $(uname -srm)"
    echo "No PR code, upstream branch or maintainer status was changed."
} > "$OUTPUT_DIR/source-manifest.txt"

SOURCES=(
    src/cpp/Cdr.cpp
    src/cpp/CdrSizeCalculator.cpp
    src/cpp/FastCdr.cpp
    src/cpp/FastBuffer.cpp
    src/cpp/exceptions/BadOptionalAccessException.cpp
    src/cpp/exceptions/BadParamException.cpp
    src/cpp/exceptions/Exception.cpp
    src/cpp/exceptions/LockedExternalAccessException.cpp
    src/cpp/exceptions/NotEnoughMemoryException.cpp
    src/cpp/helpers/memory_helpers.cpp
)

for arm in base head fixed; do
    expected_violations=12
    expected_roundtrips=8
    expected_pointer=4
    use_new_api=1
    if [[ "$arm" == base ]]; then
        expected_violations=4
        expected_roundtrips=4
        expected_pointer=0
        use_new_api=0
    fi
    worktree="$TRIAL_DIR/$arm"
    if [[ "$arm" == head ]]; then
        worktree="$TRIAL_DIR/source"
    fi
    if [[ "$arm" == fixed ]]; then
        expected_violations=0
    fi

    (
        cd "$worktree"
        g++ -std=c++17 -O0 -g0 -Wall -Wextra \
            "-DFASTCDR350_PR_HEAD=$use_new_api" \
            -Iinclude -I"$CHECK_DIR/config" \
            "${SOURCES[@]}" "$CHECK_DIR/wide_length_boundary.cpp" \
            -o "$OUTPUT_DIR/$arm.bin"
    ) > "$OUTPUT_DIR/$arm.build.log" 2>&1

    set +e
    timeout 30s "$OUTPUT_DIR/$arm.bin" > "$OUTPUT_DIR/$arm.native.log" 2>&1
    native_rc=$?
    set -e
    expected_rc=1
    [[ "$arm" == fixed ]] && expected_rc=0
    [[ "$native_rc" == "$expected_rc" ]] || {
        echo "Unexpected $arm native exit: got=$native_rc expected=$expected_rc" >&2
        exit 5
    }
    require_count "$OUTPUT_DIR/$arm.native.log" 'ROUNDTRIP_PASS' "$expected_roundtrips"
    require_count "$OUTPUT_DIR/$arm.native.log" 'REJECT count=1 ' "$expected_roundtrips"
    require_count "$OUTPUT_DIR/$arm.native.log" 'REJECT_POINTER count=1 ' "$expected_pointer"
    require_count "$OUTPUT_DIR/$arm.native.log" 'ROUNDTRIP_FAIL' 0
    require_count "$OUTPUT_DIR/$arm.native.log" "VIOLATIONS=$expected_violations$" 1
    if [[ "$arm" == fixed ]]; then
        require_count "$OUTPUT_DIR/$arm.native.log" 'REJECT count=2147483648 ' 8
        require_count "$OUTPUT_DIR/$arm.native.log" 'REJECT_POINTER count=2147483648 ' 4
    else
        require_count "$OUTPUT_DIR/$arm.native.log" 'ACCEPT count=2147483648 ' "$expected_roundtrips"
        require_count "$OUTPUT_DIR/$arm.native.log" 'ACCEPT_POINTER count=2147483648 ' "$expected_pointer"
    fi
    printf '%s: exit=%s, violations=%s, valid_roundtrips=%s\n' \
        "$arm" "$native_rc" "$expected_violations" "$expected_roundtrips" \
        | tee -a "$OUTPUT_DIR/source-manifest.txt"
    sha256sum "$worktree/src/cpp/Cdr.cpp" >> "$OUTPUT_DIR/source-manifest.txt"
done

sha256sum "$CHECK_DIR/wide_length_boundary.cpp" "$CHECK_DIR/config/fastcdr/config.h" \
    "$CHECK_DIR/wide_length_guard.patch" "$OUTPUT_DIR"/*.native.log \
    "$OUTPUT_DIR"/*.build.log "$OUTPUT_DIR/local-candidate-only.patch" \
    > "$OUTPUT_DIR/artifact-digests.sha256"
echo 'BOUNDED_SOURCE_NATIVE_QUALIFICATION_PASS' | tee -a "$OUTPUT_DIR/source-manifest.txt"
