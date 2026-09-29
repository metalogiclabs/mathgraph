#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from mathgraph.lean_bridge_discovery import run_manifest


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("manifest")
    p.add_argument("--out", required=True)
    args = p.parse_args()
    result = run_manifest(args.manifest, out_path=args.out)
    print(json.dumps({
        "declaration_count": result["declaration_count"],
        "alias_rules": len(result["alias_rules"]),
        "implication_rules": len(result["implication_rules"]),
        "equivalence_candidates": len(result["equivalence_candidates"]),
        "implication_candidates": len(result["implication_candidates"]),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
