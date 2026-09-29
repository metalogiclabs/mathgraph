#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mathgraph.lean_bridge_discovery import SourcePin, fetch_pin
from mathgraph.lean_corpus_bridge_scout import (
    build_scout_report,
    load_corpus_manifest,
    write_report,
)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("manifest")
    p.add_argument("--corpus-root", action="append", default=[], help="corpus=/path")
    p.add_argument("--out", required=True)
    p.add_argument("--top-k", type=int)
    args = p.parse_args()

    roots = {}
    for item in args.corpus_root:
        corpus, sep, root = item.partition("=")
        if not sep:
            raise SystemExit(f"bad --corpus-root {item!r}; expected corpus=/path")
        roots[corpus] = root

    manifest = load_corpus_manifest(args.manifest)
    bridges = []
    for row in manifest.get("bridge_files", []):
        pin = SourcePin.from_mapping(row)
        bridges.append((pin, fetch_pin(pin)))

    report = build_scout_report(
        corpus_roots=roots,
        manifest=manifest,
        bridge_texts=bridges,
        top_k=args.top_k,
    )
    write_report(report, args.out)
    print(json.dumps(report["totals"], sort_keys=True))


if __name__ == "__main__":
    main()
