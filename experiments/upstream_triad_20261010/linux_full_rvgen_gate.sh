#!/usr/bin/env bash
# Qualify an isolated Linux upstream rvgen patch; never modifies upstream.
set -euo pipefail
LINUX_SHA=af32da41b0327b9c6a37856ba82b6760d6c8d10e
ROOT="$GITHUB_WORKSPACE"
TREE="$RUNNER_TEMP/linux-rvgen-upstream-af32da41"
OUT="$ROOT/experiments/upstream_triad_20261010/linux_upstream_out"
mkdir -p "$OUT"
rm -rf "$TREE"
mkdir -p "$TREE"
git -C "$TREE" init -q
git -C "$TREE" remote add origin https://github.com/torvalds/linux.git
git -C "$TREE" sparse-checkout init --cone
git -C "$TREE" sparse-checkout set tools/verification/rvgen tools/verification/tests kernel/trace/rv scripts
git -C "$TREE" -c protocol.version=2 fetch --depth=1 --filter=blob:none origin "$LINUX_SHA"
git -C "$TREE" checkout --detach --force FETCH_HEAD
test "$(git -C "$TREE" rev-parse HEAD)" = "$LINUX_SHA"
echo "PINNED_LINUX_CHECKOUT $LINUX_SHA"
export PYTHONHASHSEED=0
cd "$TREE/tools/verification/rvgen"
# First check the untouched upstream generator against ALL official tests.
make check 2>&1 | tee "$OUT/rvgen-baseline-make-check.log"
echo "UPSTREAM_ORIGINAL_RVGEN_FULL_TESTS_PASS"
# Generate two DISTINCT-edge ambiguous event specimens from official tests.
python3 - <<'PY'
from pathlib import Path
specs=Path("tests/specs")
da=(specs/"test_da.dot").read_text()
old='"state_a" -> "state_b" [ label = "event_1" ];'
assert da.count(old)==1
(specs/"test_nondeterministic_da.dot").write_text(
    da.replace(old, '"state_a" -> "state_b" [ label = "event_2" ];'))
ha=(specs/"test_ha.dot").read_text()
old='"S2" -> "S2" [ label = "event1;clk < foo_ns" ];'
assert ha.count(old)==1
(specs/"test_nondeterministic_ha.dot").write_text(
    ha.replace(old, '"S2" -> "S2" [ label = "event2;clk < foo_ns" ];'))
PY
# Negative controls: unpatched generator accepts both ambiguous models.
python3 ../rvgen monitor -c da -s tests/specs/test_nondeterministic_da.dot -t per_cpu -n ambiguous_da_original > "$OUT/orig-da-ambiguous.log" 2>&1
python3 ../rvgen monitor -c ha -s tests/specs/test_nondeterministic_ha.dot -t per_task -n ambiguous_ha_original > "$OUT/orig-ha-ambiguous.log" 2>&1
echo "UPSTREAM_ORIGINAL_RVGEN_ACCEPTED_BOTH_AMBIGUOUS_MODELS"
rm -rf ambiguous_da_original ambiguous_ha_original
# Minimal fail-closed source patch, plus black-box CLI regression tests.
python3 - <<'PY'
from pathlib import Path
file=Path("rvgen/automata.py")
src=file.read_text()
anchor="            matrix[states_dict[src]][events_dict[event]] = dst"
assert src.count(anchor)==1
guard=('            if matrix[states_dict[src]][events_dict[event]] != self.invalid_state_str:\n'
       '                raise AutomataError(\n'
       '                    f"Non-deterministic transition for event {event} in state {src}")\n')
file.write_text(src.replace(anchor,guard+anchor))
t=Path("tests/rvgen_monitor.t")
orig=t.read_text()
sentinel="\ntest_end\n"
assert orig.count(sentinel)==1
additional='''
# A single state/event must not have conflicting destinations even when
# a hybrid automaton supplies a guard for one of the transitions.
check "reject conflicting deterministic automaton transitions" \\
    "$RVGEN monitor -c da -s tests/specs/test_nondeterministic_da.dot -t per_cpu" 1 \\
    "Non-deterministic transition for event event_2 in state state_a" "Traceback"

check "reject conflicting guarded hybrid transitions" \\
    "$RVGEN monitor -c ha -s tests/specs/test_nondeterministic_ha.dot -t per_task" 1 \\
    "Non-deterministic transition for event event2 in state S2" "Traceback"
'''
t.write_text(orig.replace(sentinel, "\n"+additional+sentinel))
PY
git -C "$TREE" add -N tools/verification/rvgen/tests/specs/test_nondeterministic_da.dot tools/verification/rvgen/tests/specs/test_nondeterministic_ha.dot
git -C "$TREE" diff --check
git -C "$TREE" diff --stat | tee "$OUT/patch-stat.txt"
git -C "$TREE" diff --binary > "$OUT/linux-rvgen-reject-ambiguous-transitions.patch"
# Explicit matrix-level regression checks for shipped DOTs.
python3 "$ROOT/experiments/upstream_triad_20261010/linux_patch_probe.py" > "$OUT/rvgen-matrix-fixtures.log" 2>&1
# Full official golden suite plus our two error cases.
make check 2>&1 | tee "$OUT/rvgen-patched-make-check.log"
echo "LINUX_RVGEN_UPSTREAM_PATCH_AND_FULL_TESTS_PASS"
git -C "$TREE" status --short | tee "$OUT/git-status.txt"
if [ -f "$TREE/scripts/checkpatch.pl" ]; then
  perl "$TREE/scripts/checkpatch.pl" --no-tree --terse "$OUT/linux-rvgen-reject-ambiguous-transitions.patch" 2>&1 | tee "$OUT/checkpatch.log"
else
  echo "checkpatch.pl unavailable" | tee "$OUT/checkpatch.log"
fi
sha256sum "$OUT/linux-rvgen-reject-ambiguous-transitions.patch" | tee "$OUT/patch-sha256.txt"
