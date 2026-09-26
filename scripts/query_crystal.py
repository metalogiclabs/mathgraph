#!/usr/bin/env python3
"""Query Crystal first; optionally attack an UNKNOWN FOL residual with Vampire."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mathgraph.atp_tptp import residual_from_dict, run_vampire
from mathgraph.query_gateway import (
    CrystalQuestion,
    machine_from_dict,
    query_crystal,
    question_from_dict,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine", required=True, help="JSON protected-continuation machine")
    parser.add_argument("--question", help="JSON Crystal question")
    parser.add_argument("--source")
    parser.add_argument("--continuation")
    parser.add_argument("--outcome", action="append", default=[])
    parser.add_argument("--interface-id")
    parser.add_argument("--live-support", action="append", default=[])
    parser.add_argument("--atp-residual", help="JSON first-order residual; used only if Crystal says UNKNOWN")
    parser.add_argument("--vampire", default="vampire")
    parser.add_argument("--atp-time-limit", type=int, default=10)
    args = parser.parse_args()

    machine = machine_from_dict(json.loads(Path(args.machine).read_text(encoding="utf-8")))
    if args.question:
        question = question_from_dict(json.loads(Path(args.question).read_text(encoding="utf-8")))
    else:
        if not args.source or not args.continuation:
            parser.error("provide --question or both --source and --continuation")
        question = CrystalQuestion(
            source=args.source,
            continuation=args.continuation,
            outcome=tuple(args.outcome) if args.outcome else None,
            interface_id=args.interface_id,
            live_supports=tuple(args.live_support),
        )

    answer = query_crystal(machine, question)
    payload = {"crystal": answer.to_dict()}

    if args.atp_residual and answer.status.value == "UNKNOWN":
        residual = residual_from_dict(json.loads(Path(args.atp_residual).read_text(encoding="utf-8")))
        candidate = run_vampire(
            residual,
            executable=args.vampire,
            time_limit_seconds=args.atp_time_limit,
        )
        payload["atp_candidate"] = candidate.to_dict()
        payload["authority_note"] = (
            "ATP output is candidate evidence only; Crystal remains UNKNOWN until "
            "a declared independent checker admits the result."
        )

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
