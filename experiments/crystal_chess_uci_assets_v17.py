#!/usr/bin/env python3
"""Compile frozen Crystal Chess runtime assets for UCI V17.

The runtime must not relearn from the target game. This compiler consumes exact
Syzygy only to reconstruct the already-qualified frozen KPvK policy, then emits
an immutable role map. The UCI engine itself uses no tablebase or labels to
decide whether Crystal may fire.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import chess
import chess.syzygy

from crystal_chess_kpvk_v0 import coordinate_feature_bank
from crystal_chess_kppvk_complete_census_v12 import acquire_policy, precompute_roles

SCHEMA = "mathgraph.crystal-chess.uci-assets.v17"
V15_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-hybrid-guard-transfer-v15"
    "@7f258e22057e8ffe1bb51c72ddca5d1ca3316949"
)


def sha256_uncompressed_gzip(path: Path) -> str:
    h = hashlib.sha256()
    with gzip.open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--roles-output", type=Path, required=True)
    args = ap.parse_args()

    bank = coordinate_feature_bank()
    feature_fns = [fn for _name, fn in bank]
    pawn_squares = [
        chess.square(f, r)
        for f in range(8)
        for r in range(1, 6)  # ranks 2..6: full V14 runtime boundary
    ]

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tb:
        policy, frequency, enumeration, nonterminal = acquire_policy(tb, feature_fns)
        role_map = precompute_roles(policy, feature_fns, pawn_squares)

    args.roles_output.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with gzip.open(args.roles_output, "wt", encoding="utf-8") as out:
        header = {
            "schema": SCHEMA,
            "v15_authority": V15_AUTHORITY,
            "contexts": len(role_map),
            "kpvk_nonterminal_states": nonterminal,
            "role_frequency": frequency,
            "enumeration": enumeration,
            "guard_uncompressed_sha256": sha256_uncompressed_gzip(args.guard),
        }
        line = json.dumps(header, sort_keys=True, separators=(",", ":"))
        out.write(line + "\n")
        digest.update((line + "\n").encode())
        for (wk, bk, anchor, turn), role in sorted(role_map.items()):
            row = [wk, bk, anchor, turn, role]
            line = json.dumps(row, separators=(",", ":"))
            out.write(line + "\n")
            digest.update((line + "\n").encode())

    print("CRYSTAL_CHESS_UCI_ASSETS_V17=PASS")
    print(f"contexts={len(role_map)}")
    print(f"roles_sha256={digest.hexdigest()}")
    print(f"guard_sha256={sha256_uncompressed_gzip(args.guard)}")
    print(f"artifact={args.roles_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
