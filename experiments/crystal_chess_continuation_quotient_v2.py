#!/usr/bin/env python3
"""Crystal Chess V2: bounded lawful-continuation action quotient.

No WDL label is used to construct the representation.

A board receives a depth-h continuation signature:
  h=0: side to move, check status, material multiset.
  h>0: h=0 signature plus the multiset of depth-(h-1) signatures of all
       legal successors.

Moves are quotiented by the signature of their child state. Exact Syzygy WDL is
used only after construction to falsify or qualify the quotient.

Discovery uses a deterministic spread of a/b/c-pawn KPvK states. The complete
d-pawn cover is untouched until final qualification at the shallowest discovery
depth with zero protected conflicts.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chess
import chess.syzygy

from experiments.crystal_chess_kpvk_v0 import make_kpvk, probe_wdl

SCHEMA = "mathgraph.crystal-chess.continuation-quotient.v2"
BASE_AUTHORITY = "metalogiclabs/mathgraph@e8ab96412c88b8175e7116081c4cae8276a890d1"


@dataclass(frozen=True)
class ChildAction:
    uci: str
    consequence: int
    child_fen: str


@dataclass(frozen=True)
class RootCase:
    state_id: int
    pawn_file: int
    root_wdl: int
    root_fen: str
    actions: tuple[ChildAction, ...]


def board_key(board: chess.Board) -> str:
    return " ".join(board.fen(en_passant="fen").split()[:4])


def base_observation(board: chess.Board) -> tuple[object, ...]:
    white = tuple(len(board.pieces(pt, chess.WHITE)) for pt in range(1, 7))
    black = tuple(len(board.pieces(pt, chess.BLACK)) for pt in range(1, 7))
    return (int(board.turn), int(board.is_check()), white, black)


class ContinuationCompiler:
    def __init__(self) -> None:
        self.cache: dict[tuple[str, int], str] = {}
        self.nodes_by_depth: Counter[int] = Counter()

    def signature(self, board: chess.Board, depth: int) -> str:
        key = (board_key(board), depth)
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        base = base_observation(board)
        if depth == 0:
            payload = ("v0", base)
        else:
            child_sigs: list[str] = []
            for move in board.legal_moves:
                child = board.copy(stack=False)
                child.push(move)
                child_sigs.append(self.signature(child, depth - 1))
            child_sigs.sort()
            payload = ("v0", base, tuple(child_sigs))

        digest = hashlib.sha256(
            repr(payload).encode("utf-8")
        ).hexdigest()
        self.cache[key] = digest
        self.nodes_by_depth[depth] += 1
        return digest


def enumerate_root_specs() -> list[tuple[int, int, int, int, bool]]:
    specs = []
    state_id = 0
    for pawn_file in range(4):
        for pawn_rank in range(1, 7):
            pawn = chess.square(pawn_file, pawn_rank)
            for wk in chess.SQUARES:
                if wk == pawn:
                    continue
                for bk in chess.SQUARES:
                    if bk in (pawn, wk):
                        continue
                    for turn in (chess.WHITE, chess.BLACK):
                        board = make_kpvk(wk, bk, pawn, turn)
                        if not board.is_valid():
                            continue
                        specs.append((state_id, wk, bk, pawn, turn))
                        state_id += 1
    return specs


def deterministic_sample(
    specs: list[tuple[int, int, int, int, bool]], limit: int
) -> list[tuple[int, int, int, int, bool]]:
    if limit <= 0 or len(specs) <= limit:
        return specs
    return [specs[(i * len(specs)) // limit] for i in range(limit)]


def build_cases(
    tablebase: chess.syzygy.Tablebase,
    specs: list[tuple[int, int, int, int, bool]],
    wdl_cache: dict[tuple[str, bool], int],
) -> list[RootCase]:
    out: list[RootCase] = []
    for state_id, wk, bk, pawn, turn in specs:
        board = make_kpvk(wk, bk, pawn, turn)
        root_wdl = probe_wdl(tablebase, board, wdl_cache)
        actions = []
        for move in board.legal_moves:
            child = board.copy(stack=False)
            child.push(move)
            actions.append(
                ChildAction(
                    move.uci(),
                    -probe_wdl(tablebase, child, wdl_cache),
                    child.fen(en_passant="fen"),
                )
            )
        if actions:
            out.append(
                RootCase(
                    state_id,
                    chess.square_file(pawn),
                    root_wdl,
                    board.fen(en_passant="fen"),
                    tuple(actions),
                )
            )
    return out


def evaluate(
    cases: list[RootCase],
    compiler: ContinuationCompiler,
    depth: int,
) -> dict[str, object]:
    raw_moves = 0
    oracle_classes = 0
    schema_classes = 0
    conflict_mass = 0
    impure_groups = 0
    impure_states = 0
    minimax_mismatches = 0
    examples = []

    for case in cases:
        groups: dict[str, list[ChildAction]] = defaultdict(list)
        for action in case.actions:
            child = chess.Board(action.child_fen)
            sig = compiler.signature(child, depth)
            groups[sig].append(action)

        raw_moves += len(case.actions)
        oracle_classes += len({a.consequence for a in case.actions})
        schema_classes += len(groups)
        state_impure = False
        representatives: list[ChildAction] = []

        for sig, group in groups.items():
            labels = Counter(a.consequence for a in group)
            majority = max(labels.values())
            conflict_mass += len(group) - majority
            if len(labels) > 1:
                impure_groups += 1
                state_impure = True
                if len(examples) < 12:
                    examples.append(
                        {
                            "state_id": case.state_id,
                            "root_fen": case.root_fen,
                            "signature": sig,
                            "moves": sorted((a.uci, a.consequence) for a in group),
                        }
                    )
            representatives.append(min(group, key=lambda a: a.uci))

        impure_states += int(state_impure)
        pruned_value = max(a.consequence for a in representatives)
        if pruned_value != case.root_wdl:
            minimax_mismatches += 1

    return {
        "states": len(cases),
        "raw_moves": raw_moves,
        "oracle_action_classes": oracle_classes,
        "schema_action_classes": schema_classes,
        "oracle_compression": raw_moves / oracle_classes if oracle_classes else 1.0,
        "schema_compression": raw_moves / schema_classes if schema_classes else 1.0,
        "overfragmentation_vs_oracle": (
            schema_classes / oracle_classes if oracle_classes else 1.0
        ),
        "conflict_mass": conflict_mass,
        "impure_groups": impure_groups,
        "impure_states": impure_states,
        "pruned_minimax_mismatches": minimax_mismatches,
        "examples": examples,
    }


def hash_files(directory: Path) -> list[dict[str, object]]:
    rows = []
    for path in sorted(directory.glob("*.rtbw")):
        rows.append(
            {
                "name": path.name,
                "size": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--discovery-states", type=int, default=20000)
    ap.add_argument("--max-depth", type=int, default=4)
    args = ap.parse_args()
    started = time.time()

    specs = enumerate_root_specs()
    discovery_specs_all = [s for s in specs if chess.square_file(s[3]) < 3]
    test_specs = [s for s in specs if chess.square_file(s[3]) == 3]
    discovery_specs = deterministic_sample(
        discovery_specs_all, args.discovery_states
    )

    wdl_cache: dict[tuple[str, bool], int] = {}
    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tablebase:
        discovery = build_cases(tablebase, discovery_specs, wdl_cache)
        test = build_cases(tablebase, test_specs, wdl_cache)

    compiler = ContinuationCompiler()
    curve = []
    selected_depth = None
    selected_discovery = None
    selected_test = None

    for depth in range(args.max_depth + 1):
        d_eval = evaluate(discovery, compiler, depth)
        t_eval = evaluate(test, compiler, depth)
        curve.append({"depth": depth, "discovery": d_eval, "test": t_eval})
        if (
            selected_depth is None
            and int(d_eval["conflict_mass"]) == 0
            and int(d_eval["pruned_minimax_mismatches"]) == 0
        ):
            selected_depth = depth
            selected_discovery = d_eval
            selected_test = t_eval

    heldout_exact = (
        selected_depth is not None
        and selected_test is not None
        and int(selected_test["conflict_mass"]) == 0
        and int(selected_test["pruned_minimax_mismatches"]) == 0
    )

    if heldout_exact:
        status = "WARRANTED_HELDOUT_BOUNDED_CONTINUATION_QUOTIENT"
    elif selected_depth is None:
        status = "REJECTED_DEPTH_BOUND_NO_DISCOVERY_PURITY"
    else:
        status = "CANDIDATE_WITH_HELDOUT_CONTINUATION_RESIDUAL"

    result = {
        "schema": SCHEMA,
        "status": status,
        "base_authority": BASE_AUTHORITY,
        "authority": {
            "kind": "Syzygy WDL",
            "tablebase_files": hash_files(args.tablebase_dir),
        },
        "construction": {
            "depth0": "turn + in_check + material_multiset",
            "successor_refinement": (
                "base observation plus multiset of depth-(h-1) legal successor signatures"
            ),
            "uses_wdl_as_feature": False,
        },
        "split": {
            "discovery": "deterministic spread over complete pawn files a,b,c",
            "discovery_states_requested": args.discovery_states,
            "discovery_states_realized": len(discovery),
            "final_test": "complete pawn file d",
            "final_test_states": len(test),
        },
        "curve": curve,
        "selected_depth": selected_depth,
        "selected_discovery": selected_discovery,
        "selected_test": selected_test,
        "compiler": {
            "cached_signatures": len(compiler.cache),
            "new_nodes_by_depth": dict(sorted(compiler.nodes_by_depth.items())),
        },
        "wdl_cache_positions": len(wdl_cache),
        "claim_boundary": {
            "if_warranted": (
                "the shallowest continuation signature exact on discovery is "
                "also consequence-pure and minimax-preserving on the complete "
                "untouched d-file KPvK cover"
            ),
            "not_claimed": [
                "unbounded future equivalence",
                "cross-material transfer",
                "general chess solution",
            ],
        },
        "elapsed_seconds": time.time() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    print(f"CRYSTAL_CHESS_CONTINUATION_V2={status}")
    print(f"selected_depth={selected_depth}")
    for row in curve:
        d = row["depth"]
        de = row["discovery"]
        te = row["test"]
        print(
            f"depth={d} "
            f"discovery(compression={de['schema_compression']:.3f}x,"
            f"over={de['overfragmentation_vs_oracle']:.3f},"
            f"conflict={de['conflict_mass']},mm={de['pruned_minimax_mismatches']}) "
            f"test(compression={te['schema_compression']:.3f}x,"
            f"over={te['overfragmentation_vs_oracle']:.3f},"
            f"conflict={te['conflict_mass']},mm={te['pruned_minimax_mismatches']})"
        )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
