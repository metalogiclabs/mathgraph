#!/usr/bin/env python
"""Render a read-only MathGraph epistemic status card from JSON artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from _bootstrap import ensure_repo_root_on_path
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
else:
    ensure_repo_root_on_path(__file__)

from mathgraph.epistemic_status import (
    audit_epistemic_status_view,
    build_epistemic_status_view,
    epistemic_status_to_markdown,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--sidecar")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--out")
    parser.add_argument("--fail-on-critical", action="store_true")
    args = parser.parse_args(argv)

    artifact = json.loads(Path(args.artifact).read_text(encoding="utf-8"))
    sidecar = (
        json.loads(Path(args.sidecar).read_text(encoding="utf-8"))
        if args.sidecar
        else None
    )
    view = build_epistemic_status_view(artifact, sidecar=sidecar)
    findings = audit_epistemic_status_view(view)
    criticals = [item for item in findings if item["severity"] == "CRITICAL"]

    if args.format == "json":
        text = json.dumps(
            {"epistemic_status": view, "audit_findings": findings},
            sort_keys=True,
            indent=2,
        ) + "\n"
    else:
        text = epistemic_status_to_markdown(view)
        if findings:
            text += "\n## Audit\n" + "\n".join(
                f"- {item['severity']}: {item['code']} — {item['message']}"
                for item in findings
            ) + "\n"

    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    else:
        print(text, end="")

    return 1 if args.fail_on_critical and criticals else 0


if __name__ == "__main__":
    raise SystemExit(main())
