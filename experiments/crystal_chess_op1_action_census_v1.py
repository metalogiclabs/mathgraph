#!/usr/bin/env python3
"""Crystal Chess: exact Op1 8-piece oracle action-consequence census.

Purpose: test whether the V0 observation that many legal moves collapse to very
few exact game-theoretic consequences persists in materially richer chess.

Boundary:
* standard chess, K+3P vs K+3P (8 pieces);
* three opposed pawn pairs on distinct files, guaranteeing that ordinary pawn
  moves leave at least one opposed pair and captures reduce to <=7 pieces;
* no castling/en-passant; halfmove clock zero;
* external authority: Lichess /standard tablebase API;
* only responses whose root and every legal move have an exact WDL category
  are admitted.

This experiment discovers no pruning schema. It is an oracle census only.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random
import time
import urllib.error
import urllib.parse
import urllib.request

import chess

SCHEMA="mathgraph.crystal-chess.op1-action-census.v1"
ENDPOINT="https://tablebase.lichess.ovh/standard"
SEED=20260928

CATEGORY_TO_WDL={
    "win": 2,
    "syzygy-win": 2,
    "cursed-win": 1,
    "draw": 0,
    "blessed-loss": -1,
    "syzygy-loss": -2,
    "loss": -2,
}


def make_candidate(rng: random.Random) -> chess.Board:
    files=sorted(rng.sample(range(8),3))
    occupied=set()
    board=chess.Board(None)
    board.castling_rights=chess.BB_EMPTY
    board.ep_square=None
    board.halfmove_clock=0
    board.fullmove_number=1

    for f in files:
        wr=rng.choice((1,2,3))
        br=rng.choice((4,5,6))
        ws=chess.square(f,wr)
        bs=chess.square(f,br)
        board.set_piece_at(ws,chess.Piece(chess.PAWN,chess.WHITE))
        board.set_piece_at(bs,chess.Piece(chess.PAWN,chess.BLACK))
        occupied.add(ws); occupied.add(bs)

    free=[sq for sq in chess.SQUARES if sq not in occupied]
    wk=rng.choice(free)
    board.set_piece_at(wk,chess.Piece(chess.KING,chess.WHITE))
    free=[sq for sq in free if sq!=wk]
    bk=rng.choice(free)
    board.set_piece_at(bk,chess.Piece(chess.KING,chess.BLACK))
    board.turn=rng.choice((chess.WHITE,chess.BLACK))
    return board


def probe(fen: str, retries: int=4) -> dict:
    query=urllib.parse.urlencode({"fen":fen})
    url=f"{ENDPOINT}?{query}"
    request=urllib.request.Request(
        url,
        headers={
            "User-Agent":"MathGraph-CrystalChess/1.0 (research; github.com/metalogiclabs/mathgraph)",
            "Accept":"application/json",
        },
    )
    delay=0.4
    last=None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request,timeout=25) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last=exc
            if exc.code not in (429,500,502,503,504):
                raise
        except urllib.error.URLError as exc:
            last=exc
        if attempt+1<retries:
            time.sleep(delay)
            delay*=2
    raise last if last is not None else RuntimeError("tablebase request failed")


def normalized_wdl(category: str) -> int|None:
    return CATEGORY_TO_WDL.get(category)


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--target",type=int,default=128)
    ap.add_argument("--max-attempts",type=int,default=1200)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()

    rng=random.Random(SEED)
    seen=set()
    accepted=[]
    stats=Counter()
    class_hist=Counter()
    raw_moves=0
    consequence_classes=0
    started=time.time()

    for _ in range(args.max_attempts):
        if len(accepted)>=args.target:
            break
        board=make_candidate(rng)
        stats["generated"]+=1
        if not board.is_valid():
            stats["invalid"]+=1
            continue
        fen=board.fen(en_passant="fen")
        key=" ".join(fen.split()[:4])
        if key in seen:
            stats["duplicate"]+=1
            continue
        seen.add(key)

        try:
            data=probe(fen)
        except urllib.error.HTTPError as exc:
            stats[f"http_{exc.code}"]+=1
            continue
        except Exception:
            stats["request_error"]+=1
            continue
        stats["responses"]+=1

        root=normalized_wdl(str(data.get("category")))
        moves=data.get("moves")
        if root is None or not isinstance(moves,list) or not moves:
            stats["root_unknown_or_terminal"]+=1
            continue

        consequences=[]
        unknown_move=False
        for move in moves:
            child=normalized_wdl(str(move.get("category")))
            if child is None:
                unknown_move=True
                break
            consequences.append(-child)
        if unknown_move:
            stats["move_unknown"]+=1
            continue

        distinct=sorted(set(consequences))
        predicted=max(consequences)
        if predicted!=root:
            stats["minimax_mismatch"]+=1

        raw_moves+=len(moves)
        consequence_classes+=len(distinct)
        class_hist[len(distinct)]+=1
        accepted.append({
            "fen":fen,
            "root_wdl":root,
            "legal_moves":len(moves),
            "consequence_classes":len(distinct),
            "consequences":distinct,
        })
        stats["accepted"]+=1
        time.sleep(0.06)

    status=(
        "WARRANTED_BOUNDED_OP1_ACTION_REDUNDANCY"
        if len(accepted)==args.target and stats["minimax_mismatch"]==0
        else "PARTIAL_OP1_CENSUS"
    )
    result={
        "schema":SCHEMA,
        "status":status,
        "authority":{
            "endpoint":ENDPOINT,
            "protected_semantics":"5-valued Syzygy WDL category normalized from exact API categories",
        },
        "generator":{
            "seed":SEED,
            "material":"KPPP v KPPP",
            "opposed_pawn_pairs":3,
            "no_castling":True,
            "no_en_passant":True,
            "halfmove_clock":0,
        },
        "stats":dict(stats),
        "accepted_positions":len(accepted),
        "raw_legal_moves":raw_moves,
        "protected_consequence_classes":consequence_classes,
        "action_compression_ratio":(
            raw_moves/consequence_classes if consequence_classes else 1.0
        ),
        "mean_legal_moves":raw_moves/len(accepted) if accepted else 0.0,
        "mean_consequence_classes":(
            consequence_classes/len(accepted) if accepted else 0.0
        ),
        "class_histogram":{str(k):v for k,v in sorted(class_hist.items())},
        "sample":accepted[:24],
        "claim_boundary":{
            "warranted_if_green":(
                "exact action-consequence redundancy exists on this deterministic "
                "sample of Op1-covered 8-piece pawn endings"
            ),
            "not_claimed":[
                "representativeness of all 8-piece chess",
                "constructive recognition of the consequence classes",
                "general chess solution",
            ],
        },
        "elapsed_seconds":time.time()-started,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")

    print(f"CRYSTAL_CHESS_OP1_CENSUS={status}")
    print(f"accepted={len(accepted)} responses={stats['responses']} attempts={stats['generated']}")
    print(
        f"actions={raw_moves}->{consequence_classes} "
        f"compression={result['action_compression_ratio']:.3f}x "
        f"means={result['mean_legal_moves']:.3f}->{result['mean_consequence_classes']:.3f}"
    )
    print(f"class_histogram={dict(sorted(class_hist.items()))}")
    print(f"minimax_mismatch={stats['minimax_mismatch']}")
    print(f"artifact={args.output}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
