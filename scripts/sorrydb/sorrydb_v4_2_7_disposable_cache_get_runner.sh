#!/usr/bin/env bash
set -euo pipefail

echo "MATHGRAPH x SORRYDB v4.2.7 — DISPOSABLE CACHE-GET RUNNER"

WORK_ROOT="${SORRYDB_V427_WORK_ROOT:-/tmp/mathgraph_sorrydb_v427_disposable}"
MATHGRAPH_REPO="${SORRYDB_V427_MATHGRAPH_REPO:-https://github.com/metalogiclabs/mathgraph.git}"
MATHGRAPH_REF="${SORRYDB_V427_MATHGRAPH_REF:-main}"

TARGET_REPO_URL="${SORRYDB_V427_TARGET_REPO_URL:-https://github.com/siddhartha-gadgil/MetaExamples.git}"
TARGET_REPO_COMMIT="${SORRYDB_V427_TARGET_REPO_COMMIT:-edbb75e784db19846a1c19841e182b797afc18bb}"
TARGET_FILE="${SORRYDB_V427_TARGET_FILE:-MetaExamples/Fiddle.lean}"

MIN_FREE_GB="${SORRYDB_V427_MIN_FREE_GB:-25}"
CACHE_TIMEOUT="${SORRYDB_V427_CACHE_GET_TIMEOUT_SECONDS:-1200}"
BASELINE_TIMEOUT="${SORRYDB_V427_BASELINE_TIMEOUT_SECONDS:-120}"

MATHGRAPH_DIR="$WORK_ROOT/mathgraph"
CACHE_ROOT="$WORK_ROOT/repo_cache"
TARGET_DIR="$CACHE_ROOT/siddhartha-gadgil__MetaExamples__edbb75e784db"
RUN_ROOT="$WORK_ROOT/run"

free_gb() {
  python - "$1" <<'PY'
import shutil, sys
print(round(shutil.disk_usage(sys.argv[1]).free / (1024 ** 3), 3))
PY
}

echo "work_root=$WORK_ROOT"
mkdir -p "$WORK_ROOT" "$CACHE_ROOT" "$RUN_ROOT"

FREE_NOW="$(free_gb "$WORK_ROOT")"
echo "free_gb=$FREE_NOW required_gb=$MIN_FREE_GB"

python - "$FREE_NOW" "$MIN_FREE_GB" <<'PY'
import sys
free = float(sys.argv[1])
need = float(sys.argv[2])
if free < need:
    raise SystemExit(f"OBSTRUCTED_DISK_PRESSURE free_gb={free} required_gb={need}")
PY

if [ ! -d "$MATHGRAPH_DIR/.git" ]; then
  git clone "$MATHGRAPH_REPO" "$MATHGRAPH_DIR"
fi

cd "$MATHGRAPH_DIR"
git fetch origin "$MATHGRAPH_REF"
git checkout FETCH_HEAD

if [ ! -d "$TARGET_DIR/.git" ]; then
  git clone "$TARGET_REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR"
git fetch origin
git checkout "$TARGET_REPO_COMMIT"

cd "$MATHGRAPH_DIR"

SORRYDB_V426_REPO_ROOT="$TARGET_DIR" \
SORRYDB_V426_FILE_PATH="$TARGET_FILE" \
SORRYDB_V426_WORK_ROOT="$RUN_ROOT" \
SORRYDB_V426_MIN_FREE_GB="$MIN_FREE_GB" \
SORRYDB_V426_CACHE_GET_TIMEOUT_SECONDS="$CACHE_TIMEOUT" \
SORRYDB_V426_BASELINE_TIMEOUT_SECONDS="$BASELINE_TIMEOUT" \
SORRYDB_V426_ALLOW_CACHE_GET="1" \
SORRYDB_V426_RUN_BASELINE_AFTER_CACHE="1" \
python experiments/sorrydb/sorrydb_v4_2_6_cache_get_boundary_runner.py

LATEST="$(find "$RUN_ROOT" -name cache_get_manifest.json | sort | tail -1)"
echo "manifest=$LATEST"
cat "$LATEST"

python - "$LATEST" <<'PY'
import json, sys
p = sys.argv[1]
data = json.load(open(p))
print("FINAL_VERDICT=" + data.get("verdict", ""))
print("CACHE_GET_VERDICT=" + data.get("cache_get_verdict", ""))
print("BASELINE_VERDICT=" + data.get("baseline_verdict", ""))
PY
