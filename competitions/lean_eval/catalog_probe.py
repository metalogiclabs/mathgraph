#!/usr/bin/env python3
"""Cheap, deterministic probe of a pinned LeanEval generated/index.json."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: catalog_probe.py PATH/TO/generated/index.json")

    path = Path(sys.argv[1])
    data = json.loads(path.read_text())
    if not isinstance(data, list):
        raise SystemExit("LeanEval index is not a JSON array")

    groups = Counter(str(p.get("group", "unknown")) for p in data)
    statuses = Counter(str(p.get("status", "unknown")) for p in data)
    visible = [p for p in data if p.get("visible", True)]

    # Shortlist is a triage aid, not a difficulty claim. Prefer visible,
    # single-hole, non-Annals problems; exclude obvious starter/sandbox ids.
    starters = {"two_plus_two", "list_append_singleton_length"}
    candidates = []
    for p in visible:
        pid = str(p.get("id", ""))
        holes = p.get("holes") or []
        tags = set(map(str, p.get("tags") or []))
        if not pid or pid in starters or pid.startswith("sandbox"):
            continue
        score = (
            1 if "annals" in tags else 0,
            len(holes),
            pid,
        )
        candidates.append((score, p))

    candidates.sort(key=lambda x: x[0])
    shortlist = [p for _, p in candidates[:12]]

    print(f"catalog_total={len(data)}")
    print(f"catalog_visible={len(visible)}")
    print("groups=" + json.dumps(dict(sorted(groups.items())), sort_keys=True))
    print("statuses=" + json.dumps(dict(sorted(statuses.items())), sort_keys=True))
    print("shortlist:")
    for p in shortlist:
        print(
            f"- {p.get('id')} | holes={len(p.get('holes') or [])} | "
            f"group={p.get('group')} | title={p.get('title')}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
