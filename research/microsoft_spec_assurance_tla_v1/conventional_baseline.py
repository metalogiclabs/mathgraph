#!/usr/bin/env python3
"""Actually-run strong baseline: author source + invariant-config diff + TLC.

No MathGraph imports. Gives a competent source-aware reviewer the same safety
requirement, native TLC results, and exact finite-model context.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def compare(source: Path, results: Path) -> dict[str, str]:
    known_source_hashes = {
        "README.md": "b2e9bf1e40eac6f6b46be646367f69df3f5a70de78d7ea36ea69b7b56da5fbb6",
        "LamportMutex.tla": "dfa726da541fb0515ad482c3b5ca82c81b6f54df6626c3b9edfcebedc2a9c05a",
        "MCLamportMutex.cfg": "b91d46fb0a2f3af22fa65147c4c971d5cb9e42d141f63ad9035aa30cad51d118",
    }
    for file, expected in known_source_hashes.items():
        if not (source / file).is_file() or hashlib.sha256(
                (source / file).read_bytes()).hexdigest() != expected:
            return {"relative_advantage": "UNKNOWN", "reason": "SOURCE_DRIFT"}
    source_model = (source / "LamportMutex.tla").read_text()
    source_cfg = (source / "MCLamportMutex.cfg").read_text()
    source_readme = (source / "README.md").read_text()
    if not ("Mutex ==" in source_model and "mutual exclusion" in source_readme.lower()
            and "INVARIANTS TypeOK BoundedNetwork Mutex" in source_cfg):
        return {"relative_advantage": "UNKNOWN", "reason": "NO_AUTHOR_INTENT_BINDING"}
    decisions = {}
    for name in ("author", "mutant_checked", "mutant_weakened"):
        folder = results / name
        try:
            config = (folder / "MCLamportMutex.cfg").read_text()
            log = (folder / "tlc.log").read_text()
            code = int((folder / "tlc.exit").read_text().strip())
        except (OSError, ValueError):
            decisions[name] = "WITHDRAWN"
            continue
        config_checks_mutex = "Mutex" in config.split("INVARIANTS", 1)[1].splitlines()[0]
        if not config_checks_mutex:
            decisions[name] = "REFUSED_UNCHECKED_PROPERTY"
        elif code == 0 and "Model checking completed. No error has been found." in log:
            decisions[name] = "WARRANTED_BOUNDED"
        elif code != 0 and "Error: Invariant Mutex is violated." in log:
            decisions[name] = "COUNTERMODEL"
        else:
            decisions[name] = "UNKNOWN"
    decisions["relative_advantage"] = (
        "BASELINE_TIE" if [decisions[n] for n in
        ("author", "mutant_checked", "mutant_weakened")] ==
        ["WARRANTED_BOUNDED", "COUNTERMODEL", "REFUSED_UNCHECKED_PROPERTY"]
        else "NO_BASELINE_TIE")
    decisions["qualification"] = (
        "Same source-aware property selection and native evidence; "
        "not a measured accuracy, labor or cost advantage.")
    return decisions


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--results", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    report = compare(args.source, args.results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("CONVENTIONAL_COMPARATOR", report)
    if report["relative_advantage"] != "BASELINE_TIE":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
