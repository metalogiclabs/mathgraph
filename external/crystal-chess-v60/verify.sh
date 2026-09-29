#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/tmp/crystal-v60-stockfish}"
PATCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCH="$PATCH_DIR/stockfish-0a215d6c-crystal-v56.patch"
UPSTREAM="0a215d6c9e48856ef630013b8ab8312941a59057"

rm -rf "$ROOT"
git clone --filter=blob:none https://github.com/official-stockfish/Stockfish.git "$ROOT"
git -C "$ROOT" checkout "$UPSTREAM"
git -C "$ROOT" apply --check "$PATCH"
git -C "$ROOT" apply "$PATCH"

grep -F 'if (mainThread->tm.optimum() <= 64)' "$ROOT/src/search.cpp"
grep -F 'highBestMoveEffort = 1.0;' "$ROOT/src/search.cpp"

make -C "$ROOT/src" -j2 build ARCH=x86-64
"$ROOT/src/stockfish" bench 16 1 3 default depth

echo "CRYSTAL_CHESS_EXTERNAL_PACKAGE_V60=PASS"
