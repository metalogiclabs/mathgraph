#!/usr/bin/env python3
"""Tamper copies of actual TLC outputs; never alter original source or receipts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import tempfile

from independent_checker import assess, SOURCE_PIN, TLC_SHA256


def challenge_all(source: Path, native: Path) -> dict[str, str]:
    outcomes = {
        "original": assess(source, native, SOURCE_PIN, TLC_SHA256)["authority"],
        "stale_source": assess(source, native, "0" * 40, TLC_SHA256)["authority"],
        "changed_jar": assess(source, native, SOURCE_PIN, "0" * 64)["authority"],
    }
    for case in ("missing_author_log", "removed_original_mutex_gate",
                 "forged_mutant_green", "replaced_mutant_source"):
        with tempfile.TemporaryDirectory(prefix="mg-tla-real-negative-") as temp:
            root = Path(temp)
            for lane in ("author", "mutant_checked", "mutant_weakened"):
                shutil.copytree(native / lane, root / lane,
                                ignore=shutil.ignore_patterns("states", "*.dot", "*.bin"))
            if case == "missing_author_log":
                (root / "author" / "tlc.log").unlink()
            elif case == "removed_original_mutex_gate":
                path = root / "author" / "MCLamportMutex.cfg"
                path.write_text(path.read_text().replace(
                    "INVARIANTS TypeOK BoundedNetwork Mutex",
                    "INVARIANTS TypeOK BoundedNetwork"))
            elif case == "forged_mutant_green":
                for name in ("tlc.log", "tlc.exit"):
                    shutil.copyfile(root / "mutant_weakened" / name,
                                    root / "mutant_checked" / name)
            elif case == "replaced_mutant_source":
                shutil.copyfile(root / "author" / "LamportMutex.tla",
                                root / "mutant_weakened" / "LamportMutex.tla")
            outcomes[case] = assess(source, root, SOURCE_PIN, TLC_SHA256)["authority"]
    return outcomes


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--results", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    decisions = challenge_all(args.source, args.results)
    expected = {
        "original": "WARRANTED_BOUNDED_AUTHOR_MODEL",
        "stale_source": "WITHDRAWN",
        "changed_jar": "REJECTED_EVIDENCE",
        "missing_author_log": "WITHDRAWN",
        "removed_original_mutex_gate": "REJECTED_EVIDENCE",
        "forged_mutant_green": "REJECTED_EVIDENCE",
        "replaced_mutant_source": "REJECTED_EVIDENCE",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(decisions, indent=2, sort_keys=True) + "\n")
    print("REAL_NATIVE_NEGATIVE_CONTROLS", decisions)
    if decisions != expected:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
