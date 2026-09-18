from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from mathgraph.abgp.confirmatory import (
    aggregate_confirmatory,
    build_execution_lock,
    run_confirmatory_a,
    run_confirmatory_b,
    run_confirmatory_g,
    run_confirmatory_p_shard,
)


def _tree() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], text=True).strip()


def _write(path: Path, value) -> None:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n", encoding="utf-8")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="MathGraph ABGP one-shot confirmatory runner")
    parser.add_argument("--expected-tree", required=True)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plan")
    p.add_argument("--output", type=Path, required=True)

    for name in ("a", "b", "g"):
        p = sub.add_parser(name)
        p.add_argument("--output", type=Path, required=True)

    p = sub.add_parser("p-shard")
    p.add_argument("--start", type=int, required=True)
    p.add_argument("--count", type=int, required=True)
    p.add_argument("--output", type=Path, required=True)

    p = sub.add_parser("aggregate")
    p.add_argument("--a", type=Path, required=True)
    p.add_argument("--b", type=Path, required=True)
    p.add_argument("--g", type=Path, required=True)
    p.add_argument("--p-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    actual_tree = _tree()
    if actual_tree != args.expected_tree:
        raise SystemExit(f"tree mismatch: expected {args.expected_tree}, got {actual_tree}")
    lock = build_execution_lock(actual_tree)

    if args.command == "plan":
        value = lock
    elif args.command == "a":
        value = run_confirmatory_a(lock)
    elif args.command == "b":
        value = run_confirmatory_b(lock)
    elif args.command == "g":
        value = run_confirmatory_g(lock)
    elif args.command == "p-shard":
        value = run_confirmatory_p_shard(lock, start_index=args.start, episode_count=args.count)
    else:
        shards = [_load(path) for path in sorted(args.p_dir.glob("p-*.json"))]
        value = aggregate_confirmatory(
            lock,
            a=_load(args.a),
            b_records=_load(args.b),
            g=_load(args.g),
            p_shards=shards,
        )
    _write(args.output, value)
    print("command", args.command)
    print("namespace", lock["confirmatory_namespace_identifier"])
    print("lock_digest", lock["lock_digest"])
    if args.command == "plan":
        print("ABGP_CONFIRMATORY_PLAN_VALIDATED_NO_SEEDS_DERIVED")
    elif args.command == "aggregate":
        print("combined_verdict", value["combined_verdict"])
        print("result_digest", value["result_digest"])
        print("ABGP_CONFIRMATORY_RESULT_COMPLETE")
    else:
        print("ABGP_CONFIRMATORY_ARM_COMPLETE")


if __name__ == "__main__":
    main()
