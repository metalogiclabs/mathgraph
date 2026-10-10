"""Lightweight MathGraph Check v0 command line; zero model calls or network fetches."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .preflight import ManifestError, check_manifest, render_markdown


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare explicitly supplied source/formal claim contracts; never certify truth."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--json", dest="json_out", type=Path)
    parser.add_argument("--markdown", dest="md_out", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
        report = check_manifest(data, base_dir=args.manifest.parent)
    except (OSError, ValueError, ManifestError) as exc:
        print("MathGraph Check input rejected: " + str(exc), file=sys.stderr)
        return 2
    output = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(render_markdown(report), encoding="utf-8")
    if not args.json_out:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
