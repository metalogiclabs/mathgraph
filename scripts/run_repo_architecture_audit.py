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
    "mathgraph/discovery_candidate_sources.py",
    "mathgraph/discovery_scheduler.py",
    "mathgraph/lawbook.py",
    "mathgraph/lawbook_acceptance.py",
    "mathgraph/lean_digest_lawbook_ingestion.py",
    "mathgraph/lean_lawbook_attention.py",
    "mathgraph/lean_project_digest.py",
    "mathgraph/reason_atlas.py",
    "mathgraph/semantic_validation.py",
    "mathgraph/finite_magma_world.py",
    "mathgraph/compounding_engine.py",
    "mathgraph/compounding_lawbook_engine.py",
    "mathgraph/compounding_metrics.py",
    "mathgraph/decode_to_verify.py",
    "mathgraph/autonomous_compounding_engine.py",
    "mathgraph/autonomous_finite_recovery.py",
    "mathgraph/active_residual_discovery.py",
    "mathgraph/causal_route_selection.py",
    "mathgraph/exact_constructor_attribution.py",
    "mathgraph/microbasin_distillation.py",
    "mathgraph/persistent_exact_microbasin_lawbook.py",
    "mathgraph/proposal_constructor_synthesis.py",
    "mathgraph/residual_conditioned_synthesis.py",
    "mathgraph/source_law_repair.py",
    "mathgraph/repaired_countermodel_certificates.py",
    "mathgraph/end_to_end_breakthrough_validation.py",
    "mathgraph/sair_stage2_end_to_end.py",
    "mathgraph/sair_stage2_scorecard_diagnostics.py",
    "mathgraph/sair_stage2_policy_selector.py",
    "mathgraph/sair_stage2_breakthrough_search.py",
    "mathgraph/sair_compounding_loop.py",
    "mathgraph/recursive_residual_compounding.py",
    "mathgraph/recursive_residual_transfer.py",
    "mathgraph/compact_route_atlas.py",
    "mathgraph/evidence_packs.py",
    "mathgraph/collatz_evidence.py",
    "mathgraph/cross_world_evidence.py",
    "mathgraph/residual_obstruction_evidence.py",
    "mathgraph/root_node_evidence.py",
    "mathgraph/etp_terms.py",
    "mathgraph/quotient_state.py",
    "mathgraph/polarized_quotient_ir.py",
)
CANONICAL_COMMANDS = (
    "python scripts/run_release_check.py --quick",
    "python scripts/run_repo_architecture_audit.py",
    "python scripts/run_sair_stage2_end_to_end.py --out-dir /tmp/mathgraph_sair_stage2_end_to_end_demo --fallback-demo --strict-admission --write-report",
)
CANONICAL_SCRIPTS = (
    "scripts/run_autonomous_native_v2_benchmark.py",
    "scripts/run_heldout_lawbook_compounding_benchmark.py",
    "scripts/run_microbasin_distillation.py",
    "scripts/run_active_residual_discovery_benchmark.py",
    "scripts/run_discovery_scheduler_from_evidence.py",
    "scripts/run_discovery_scheduler.py",
    "scripts/run_proposal_constructor_synthesis.py",
    "scripts/run_residual_conditioned_synthesis.py",
    "scripts/run_source_law_repair.py",
    "scripts/run_repaired_countermodel_certificate_assimilation.py",
    "scripts/run_end_to_end_breakthrough_validation.py",
    "scripts/run_sair_stage2_end_to_end.py",
    "scripts/run_sair_stage2_breakthrough_search.py",
    "scripts/run_sair_compounding_lawbook_loop.py",
    "scripts/run_lean_digest_lawbook_ingestion.py",
    "scripts/run_lean_lawbook_attention.py",
    "scripts/run_lean_project_digest.py",
    "scripts/run_recursive_residual_transfer.py",
    "scripts/run_compounding_lawbook_loop.py",
    "scripts/replay_official_sair_stage2_breakthrough.py",
    "scripts/run_persistent_exact_microbasin_lawbook_benchmark.py",
    "scripts/run_persistent_exact_microbasin_lawbook_v2_benchmark.py",
)
CANONICAL_DOCS = (
    "SAIR_STAGE2_EVIDENCE.md",
    "WEBSITE_COPY.md",
    "docs/public/collaborator_issue_draft.md",
    "docs/public/investor_one_pager.md",
    "docs/evidence/official_sair_stage2_breakthrough_20260526.md",
    "docs/discovery_candidate_sources.md",
    "docs/discovery_scheduler.md",
    "docs/recursive_residual_transfer.md",
    "docs/lean_digest_lawbook_ingestion.md",
    "docs/lean_lawbook_attention.md",
    "docs/lean_project_digest.md",
    "docs/evidence/residual_obstruction_atlas_v8_4.md",
    "docs/evidence/collatz_primitive_divisor_v12_2.md",
    "docs/evidence/root_node_persistent_filtration_v16_3.md",
    "docs/evidence/cross_world_semantic_residual_invariant.md",
    "examples/evidence_packs/sair_stage2_breakthrough_20260526/README.md",
    "examples/evidence_packs/recursive_residual_transfer_v1_20260523/README.md",
    "examples/lean_project_digest_demo/README.md",
    "examples/lean_project_digest_demo/trust_boundary_audit.json",
)
CANONICAL_EVIDENCE_PACKS = (
    "recursive_residual_transfer_v1_20260523",
    "sair_stage2_breakthrough_20260526",
    "residual_obstruction_atlas_v8_4",
    "collatz_primitive_divisor_v12_2",
    "root_node_persistent_filtration_v16_3",
    "cross_world_semantic_residual_invariant",
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
    script_presence = {path: (root / path).exists() for path in CANONICAL_SCRIPTS}
    doc_presence = {path: (root / path).exists() for path in CANONICAL_DOCS}
    evidence_pack_presence = _evidence_pack_presence(root)
    readme = (root / "README.md").read_text(encoding="utf-8") if (root / "README.md").exists() else ""
    readme_commands = {command: command in readme for command in CANONICAL_COMMANDS}
    optional_deps = _optional_dependency_status(root)
    evidence_ok = all(item["present"] and item["metrics_present"] and item["manifest_present"] and item["trust_boundary_present"] for item in evidence_pack_presence.values())
    crossworld_wording = _crossworld_trust_boundary_wording(root)
    discovery_scheduler_wording = _discovery_scheduler_wording(root)
    lean_digest_demo_audit = _lean_digest_demo_audit(root)
    status = (
        "PASS"
        if all(canonical_presence.values())
        and all(script_presence.values())
        and all(doc_presence.values())
        and all(readme_commands.values())
        and evidence_ok
        and crossworld_wording["all_present"]
        and discovery_scheduler_wording["all_present"]
        and lean_digest_demo_audit["all_present"]
        else "WARN"
    )
    return {
        "status": status,
        "module_count": len(modules),
        "script_count": len(scripts),
        "test_count": len(tests),
        "large_files_over_1000_lines": large_files,
        "duplicate_concept_warnings": duplicate_warnings,
        "canonical_module_presence": canonical_presence,
        "canonical_script_presence": script_presence,
        "canonical_doc_presence": doc_presence,
        "canonical_evidence_pack_presence": evidence_pack_presence,
        "crossworld_trust_boundary_wording": crossworld_wording,
        "discovery_scheduler_wording": discovery_scheduler_wording,
        "lean_digest_demo_audit": lean_digest_demo_audit,
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
    lines.extend(["", "## Canonical Script Presence"])
    for path, present in report["canonical_script_presence"].items():
        lines.append(f"- [{'x' if present else ' '}] `{path}`")
    lines.extend(["", "## Canonical Evidence Docs"])
    for path, present in report["canonical_doc_presence"].items():
        lines.append(f"- [{'x' if present else ' '}] `{path}`")
    lines.extend(["", "## Canonical Evidence Packs"])
    for pack_id, status in report["canonical_evidence_pack_presence"].items():
        ok = status["present"] and status["metrics_present"] and status["manifest_present"] and status["trust_boundary_present"]
        lines.append(f"- [{'x' if ok else ' '}] `{pack_id}`")
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


def _evidence_pack_presence(root: Path) -> dict[str, dict[str, Any]]:
    evidence_root = root / "examples" / "evidence_packs"
    rows: dict[str, dict[str, Any]] = {}
    for pack_id in CANONICAL_EVIDENCE_PACKS:
        directory = evidence_root / pack_id
        metrics = directory / "metrics.json"
        manifest = directory / "manifest.json"
        trust_boundary_present = False
        if metrics.exists():
            try:
                data = json.loads(metrics.read_text(encoding="utf-8"))
                trust_boundary_present = bool(data.get("trust_boundary"))
            except json.JSONDecodeError:
                trust_boundary_present = False
        rows[pack_id] = {
            "present": directory.exists(),
            "readme_present": (directory / "README.md").exists(),
            "metrics_present": metrics.exists(),
            "manifest_present": manifest.exists(),
            "trust_boundary_present": trust_boundary_present,
        }
    return rows


def _crossworld_trust_boundary_wording(root: Path) -> dict[str, Any]:
    paths = [
        root / "docs" / "evidence" / "cross_world_semantic_residual_invariant.md",
        root / "examples" / "evidence_packs" / "cross_world_semantic_residual_invariant" / "README.md",
    ]
    text = "\n".join(path.read_text(encoding="utf-8").lower() for path in paths if path.exists())
    required = {
        "not a formal theorem": "not a formal theorem" in text,
        "not a truth oracle": "not a truth oracle" in text,
        "advisory only": "advisory only" in text,
        "failed finite search is not true": "failed finite search is not true" in text,
        "proof-route candidate only unless verified": "proof-route candidate only unless verified" in text,
    }
    return {"all_present": all(required.values()), "required": required}


def _discovery_scheduler_wording(root: Path) -> dict[str, Any]:
    path = root / "docs" / "discovery_scheduler.md"
    text = path.read_text(encoding="utf-8").lower() if path.exists() else ""
    required = {
        "advisory only": "advisory only" in text,
        "cannot promote truth": "cannot promote truth" in text,
        "descension target": "descension target" in text,
        "verifier boundary": "verifier boundary" in text,
        "residual compression": "residual compression" in text,
    }
    return {"all_present": all(required.values()), "required": required}


def _lean_digest_demo_audit(root: Path) -> dict[str, Any]:
    path = root / "examples" / "lean_project_digest_demo" / "trust_boundary_audit.json"
    if not path.exists():
        required = {
            "advisory_boundary_ok": False,
            "can_promote_truth_count": False,
            "textual_parsing_is_advisory": False,
            "lean_execution_confirmed_false": False,
        }
        return {"all_present": False, "required": required, "reason": "missing trust_boundary_audit.json"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        required = {
            "advisory_boundary_ok": False,
            "can_promote_truth_count": False,
            "textual_parsing_is_advisory": False,
            "lean_execution_confirmed_false": False,
        }
        return {"all_present": False, "required": required, "reason": str(exc)}
    required = {
        "advisory_boundary_ok": data.get("advisory_boundary_ok") is True,
        "can_promote_truth_count": int(data.get("can_promote_truth_count", -1)) == 0,
        "textual_parsing_is_advisory": data.get("textual_parsing_is_advisory") is True,
        "lean_execution_confirmed_false": data.get("lean_execution_confirmed") is False,
    }
    return {"all_present": all(required.values()), "required": required}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
