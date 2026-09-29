#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/tmp/crystal-v60-stockfish}"
PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPSTREAM="0a215d6c9e48856ef630013b8ab8312941a59057"
EXPECTED_DIFF_SHA256="7ee31f9f8fc69589be85358af7d9e0e736ee20c55704e8f344ff4bae93a35c98"

rm -rf "$ROOT"
git clone --filter=blob:none https://github.com/official-stockfish/Stockfish.git "$ROOT"
git -C "$ROOT" checkout "$UPSTREAM"
python "$PKG_DIR/apply.py" --search-cpp "$ROOT/src/search.cpp"

git -C "$ROOT" diff -- src/search.cpp > /tmp/crystal-v60-reproduced.patch
ACTUAL="$(sha256sum /tmp/crystal-v60-reproduced.patch | awk '{print $1}')"
test "$ACTUAL" = "$EXPECTED_DIFF_SHA256"

grep -F 'if (mainThread->tm.optimum() <= 64)' "$ROOT/src/search.cpp"
grep -F 'highBestMoveEffort = 1.0;' "$ROOT/src/search.cpp"

make -C "$ROOT/src" -j2 build ARCH=x86-64
"$ROOT/src/stockfish" bench 16 1 3 default depth

echo "CRYSTAL_CHESS_EXTERNAL_PACKAGE_V60=PASS"
