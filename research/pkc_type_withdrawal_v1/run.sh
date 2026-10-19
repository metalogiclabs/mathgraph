#!/usr/bin/env bash
set -euo pipefail
WORKSPACE="$(cd "$(dirname "$0")/../.." && pwd)"
OWN="$WORKSPACE/research/pkc_type_withdrawal_v1"
TARGET="$WORKSPACE/target"
RESULTS="$OWN/results"
V6="$WORKSPACE/evidence-v6"
PIN="e0deb453e05ffa63297d9704ceb47d0855193824"
test -x "$SYSML"
export PATH="$HOME/.elan/bin:$PATH"
test "$(git -C "$TARGET" rev-parse HEAD)" = "$PIN"
test "$(cat "$TARGET/lean-toolchain")" = "leanprover/lean4:v4.34.0"
test -z "$(git -C "$TARGET" diff --name-only)"
mkdir -p "$RESULTS"

# The seven inputs originate in the authenticated previous SysML→API→Lean run.
python3 "$OWN/audit.py" prepare --v6-archive "$V6" --target "$TARGET" --out "$RESULTS"
MODELS="$TARGET/.lake/build/sysml/typed-v1"
SOURCE="iso80000/PropertyKindCalculus/Iso80000/Part3.lean"
test "$(git -C "$TARGET" hash-object "$SOURCE")" = "9d3359e126fd76298c99e8f9ff5bd3658ebcf5d4"

for LANE in BASE MUTANT RESTORED; do
  if test "$LANE" = MUTANT; then
    python3 "$OWN/mutate.py" --target "$TARGET" --action mutate \
      --out "$RESULTS/physical-mutant.json"
  elif test "$LANE" = RESTORED; then
    python3 "$OWN/mutate.py" --target "$TARGET" --action restore \
      --out "$RESULTS/physical-restored.json"
  fi

  cd "$TARGET"
  echo "PKC_V7_NATIVE_BUILD_BEGIN lane=$LANE"
  lake build Interchange Iso80000 PropertyKindCalculus.Tests.Interchange.ApiJson \
    2>&1 | tee "$RESULTS/$LANE-build.log"
  if test "$LANE" != BASE; then
    grep -F 'Built PropertyKindCalculus.Iso80000.Part3' "$RESULTS/$LANE-build.log" >/dev/null || {
      echo "NO_SOURCE_NATIVE_PART3_RECOMPILATION lane=$LANE"; exit 1;
    }
  fi
  echo "PKC_V7_NATIVE_BUILD_COMPLETE lane=$LANE"

  python3 "$OWN/make_probe.py" \
    --v6-check "$WORKSPACE/research/pkc_typed_statement_v1/Check.lean" \
    --lane "$LANE" --out "$RESULTS/$LANE.Check.lean"
  lake env lean "$RESULTS/$LANE.Check.lean" \
    > "$RESULTS/$LANE-typed.log" 2>&1 || {
      cat "$RESULTS/$LANE-typed.log"; exit 1;
    }
  cat "$RESULTS/$LANE-typed.log"

  # Original importer tested independently of our typed-citation interpretation.
  for case in typed_match typed_mismatch wrong_citation; do
    model="$MODELS/$case.sysml"
    if SYSML="$SYSML" bash scripts/ingest-sysml.sh "$model" \
        > "$RESULTS/$LANE-$case.ingest.log" 2>&1; then
      ret=0
    else
      ret=$?
    fi
    echo "PKC_V7_UNCHANGED_JPL_IMPORT lane=$LANE case=$case exit=$ret"
    test "$ret" -eq 0 || {
      cat "$RESULTS/$LANE-$case.ingest.log"; exit 1;
    }
    grep -F '0 unverified citation(s)' "$RESULTS/$LANE-$case.ingest.log" >/dev/null
    cp .lake/build/sysml/Generated/M.lean "$RESULTS/$LANE-$case.Generated.lean"
    lake env lean "$RESULTS/$LANE-$case.Generated.lean" \
      > "$RESULTS/$LANE-$case.kernel.log" 2>&1 || {
        cat "$RESULTS/$LANE-$case.kernel.log"; exit 1;
      }
  done

  python3 "$OWN/audit.py" check --lane "$LANE" \
    --target "$TARGET" --out "$RESULTS"
  echo "PKC_V7_SOURCE_NATIVE_LANE_ACCEPTED lane=$LANE"
done

test "$(git -C "$TARGET" hash-object "$SOURCE")" = "9d3359e126fd76298c99e8f9ff5bd3658ebcf5d4"
test -z "$(git -C "$TARGET" diff --name-only)"
python3 "$OWN/audit.py" finalize --out "$RESULTS"
echo "PKC_V7_PHYSICAL_MUTATION_SELECTIVE_WITHDRAWAL_RESTORATION_COMPLETE"
