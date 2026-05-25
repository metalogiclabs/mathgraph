#!/usr/bin/env python3
"""Audit the public MathGraph repository architecture surface.

This script is intentionally read-only and dependency-light. It does not judge
legacy modules as failures; it reports module shape, large files, duplicate
concept pressure, canonical spine presence, optional dependency status, and
README command coverage.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11 fallback
    tomllib = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_MODULES = (
    "mathgraph/certificates.py",
    "mathgraph/kernel.py",
    "mathgraph/verification.py",
    "mathgraph/verifier_execution.py",
    "mathgraph/invariants.py",
    "mathgraph/evidence_manifest.py",
    "mathgraph/evidence_replay.py",
    "mathgraph/lawbook.py",
    "mathgraph/lawbook_acceptance.py",
    "mathgraph/reason_atlas.py",
    "mathgraph/semantic_validation.py",
    "mathgraph/finite_magma_world.py",
    "mathgraph/compounding_engine.py",
    "mathgraph/autonomous_compounding_engine.py",
    "mathgraph/autonomous_finite_recovery.py",
    "mathgraph/recursive_residual_compounding.py",
    "mathgraph/etp_terms.py",
    "mathgraph/quotient_state.py",
    "mathgraph/polarized_quotient_ir.py",
)
CANONICAL_COMMANDS = (
    "python scripts/run_release_check.py --quick",
    "python scripts/run_repo_architecture_audit.py",
    "python scripts/run_mathgraph_compounding_loop.py --allow-fallback-demo --out-dir /tmp/mathgraph_compounding_demo",
)
CONCEPT_KEYWORDS = (
    "certificate",
    "lawbook",
    "reason",
    "verifier",
    "verification",
    "terminal",
    "semantic",
    "manifest",
    "route",
    "htilt",
    "sair",
    "compounding",
)


def run_audit(root: Path = ROOT) -> dict[str, Any]:
    modules = sorted((root / "mathgraph").glob("*.py"))
    scripts = sorted((root / "scripts").glob("*.py"))
    tests = sorted((root / "tests").glob("test_*.py"))
    large_files = _large_python_files(root)
    duplicate_warnings = _duplicate_concept_warnings(modules + scripts + tests)
    canonical_presence = {path: (root / path).exists() for path in CANONICAL_MODULES}
    readme = (root / "README.md").read_text(encoding="utf-8") if (root / "README.md").exists() else ""
    readme_commands = {command: command in readme for command in CANONICAL_COMMANDS}
    optional_deps = _optional_dependency_status(root)
    status = "PASS" if all(canonical_presence.values()) and all(readme_commands.values()) else "WARN"
    return {
        "status": status,
        "module_count": len(modules),
        "script_count": len(scripts),
        "test_count": len(tests),
        "large_files_over_1000_lines": large_files,
        "duplicate_concept_warnings": duplicate_warnings,
        "canonical_module_presence": canonical_presence,
        "pyproject_optional_dependency_status": optional_deps,
        "readme_canonical_command_presence": readme_commands,
        "notes": [
            "Legacy modules are reported, not deleted.",
            "Duplicate concept warnings are orientation signals, not automatic failures.",
            "Reason Atlas and scheduler modules remain advisory unless linked to verifier-backed evidence.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# MathGraph Repository Architecture Audit",
        "",
        f"- Status: `{report['status']}`",
        f"- Module count: {report['module_count']}",
        f"- Script count: {report['script_count']}",
        f"- Test count: {report['test_count']}",
        "",
        "## Canonical Module Presence",
    ]
    for path, present in report["canonical_module_presence"].items():
        lines.append(f"- [{'x' if present else ' '}] `{path}`")
    lines.extend(["", "## README Canonical Commands"])
    for command, present in report["readme_canonical_command_presence"].items():
        lines.append(f"- [{'x' if present else ' '}] `{command}`")
    lines.extend(["", "## Large Python Files Over 1,000 Lines"])
    for item in report["large_files_over_1000_lines"][:40]:
        lines.append(f"- `{item['path']}`: {item['lines']} lines")
    if len(report["large_files_over_1000_lines"]) > 40:
        lines.append(f"- ... {len(report['large_files_over_1000_lines']) - 40} more")
    lines.extend(["", "## Duplicate Concept Warnings"])
    for warning in report["duplicate_concept_warnings"]:
        lines.append(f"- `{warning['concept']}` appears in {warning['count']} filenames")
    lines.extend(["", "## Optional Dependencies"])
    optional = report["pyproject_optional_dependency_status"]
    lines.append(f"- Groups: {', '.join(optional.get('groups', [])) or 'none'}")
    lines.append(f"- Runtime dependencies: {optional.get('runtime_dependency_count', 0)}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    parser.add_argument("--out-json")
    parser.add_argument("--out-markdown")
    args = parser.parse_args(argv)
    report = run_audit(ROOT)
    if args.out_json:
        _write(Path(args.out_json), json.dumps(report, indent=2, sort_keys=True) + "\n")
    if args.out_markdown:
        _write(Path(args.out_markdown), render_markdown(report))
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_markdown(report), end="")
    return 0


def _large_python_files(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(list((root / "mathgraph").glob("*.py")) + list((root / "scripts").glob("*.py")) + list((root / "tests").glob("test_*.py"))):
        try:
            count = sum(1 for _line in path.open("r", encoding="utf-8"))
        except UnicodeDecodeError:
            continue
        if count > 1000:
            rows.append({"path": str(path.relative_to(root)), "lines": count})
    return sorted(rows, key=lambda row: (-int(row["lines"]), str(row["path"])))


def _duplicate_concept_warnings(paths: list[Path]) -> list[dict[str, Any]]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        name = path.stem.lower()
        for concept in CONCEPT_KEYWORDS:
            if concept in name:
                buckets[concept].append(str(path.relative_to(ROOT)))
    warnings = []
    for concept, matches in sorted(buckets.items()):
        if len(matches) >= 6:
            warnings.append({"concept": concept, "count": len(matches), "examples": matches[:8]})
    return warnings


def _optional_dependency_status(root: Path) -> dict[str, Any]:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists() or tomllib is None:
        return {"available": False, "reason": "pyproject missing or tomllib unavailable"}
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data.get("project", {})
    optional = dict(project.get("optional-dependencies", {}) or {})
    runtime = list(project.get("dependencies", []) or [])
    return {
        "available": True,
        "groups": sorted(optional),
        "optional_dependency_counts": {key: len(value) for key, value in sorted(optional.items())},
        "runtime_dependency_count": len(runtime),
        "runtime_dependencies": runtime,
    }


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
