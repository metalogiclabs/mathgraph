"""Two-ecosystem archival assurance receipt challenge.

Calls authentic original PR #261 typed resolver, original formal L4YAML
historical adapter, and unchanged 6-test rocket artifact adapter copied from
the frozen prospective-sampling branch. This does NOT rerun Lean or native C,
authenticate mission intent, or assert a customer action grant.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research/assurance/eligibility-v05"))

from mathgraph_check.boundary_warrant import (
    admitted_route, required_dependencies, resolve_boundaries, scope_identity,
)
from mathgraph_check.warrant_resolution import (
    Claim, Receipt, Route, resolve_graph,
)
import test_native_warrant_link as rocket

L4_PATH = ROOT / "experiments/check-l4-claim-consumer-v1/boundary_export.py"
L4_SPEC = importlib.util.spec_from_file_location("cross_capstone_l4_adapter", L4_PATH)
l4 = importlib.util.module_from_spec(L4_SPEC)
assert L4_SPEC.loader is not None
L4_SPEC.loader.exec_module(l4)

FORMAL = "l4yaml.empty-tail-constructors"
SOURCE = "rocket-native-source"
CHALLENGER = "rocket-native-challenger"
CLAIMS = (FORMAL, SOURCE, CHALLENGER)
STATES = {FORMAL: "WARRANTED_BOUNDED",
          SOURCE: "WARRANTED_BOUNDED_NATIVE",
          CHALLENGER: "WARRANTED_BOUNDED_NATIVE"}
UNKNOWN = "UNKNOWN"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_from_real_bytes(l4_warrant, rocket_items, l4_archive: Path, rocket_dir: Path):
    """Freshly read both archive evidence and extracted actual native files.

    The non-evidence L4 identities refer to an earlier verified *historical*
    contract. This cannot assert that historical source is currently installed.
    A missing live observation fails closed.
    """
    current = {}
    for dep in l4_warrant.dependencies:
        if dep.role == "evidence" and dep.key == "l4yaml:claim-consumer-artifact":
            if l4_archive.is_file():
                current[dep.key] = sha(l4_archive)
        else:
            current[dep.key] = dep.sha256

    # Source-side and native policy refs are read freshly from file bytes by
    # the frozen original research adapter. If any protected native observation
    # is missing, no native receipt is considered current.
    try:
        rocket_current = rocket.measured_live_dependencies(rocket_items, rocket_dir)
    except (FileNotFoundError, IsADirectoryError):
        rocket_current = {}
    for key, digest in rocket_current.items():
        if key in current and current[key] != digest:
            raise ValueError("CONFLICTING_AUTHORITIES_FOR_DEPENDENCY")
        current[key] = digest
    return current


def typed_states(items, current):
    result = resolve_boundaries(items, current)
    return {w.obligation.id: result.states["boundary:" + scope_identity(w)]
            for w, _ in items}


def conventional_independent_direct_check(items, current):
    """Equally informed conventional per-receipt checklist, not the graph.

    Both arms use the SAME already-authenticated exact evidence adapters
    and refreshed current-byte observations; only inference mechanics vary.
    This is a scripted (NOT human/arm-blinded) comparator.
    """
    direct = {}
    for w, receipt in items:
        assert receipt.id == w.verification.receipt_id
        assert receipt.kind == w.verification.method
        assert receipt.scope == scope_identity(w)
        assert w.conclusion.status == "SUPPORTED"
        fresh = all(current.get(dep.key) == dep.sha256 for dep in w.dependencies)
        direct[w.obligation.id] = (
            "WARRANTED_BOUNDED" if fresh and receipt.kind == "formal"
            else "WARRANTED_BOUNDED_NATIVE" if fresh and receipt.kind == "native"
            else UNKNOWN)
    return direct


def assert_unwarranted_cross_kind_transplant(items):
    formal_receipt = items[0][1]
    native_receipt = items[1][1]
    for evidence, target_kind, target_scope in (
        (formal_receipt, "native", "missing-mission-owner-approval"),
        (native_receipt, "formal", "not-a-Lean-proof"),
    ):
        try:
            resolve_graph(
                [Claim("unsupported-transplant", target_kind, target_scope)],
                [Route("unsupported-transplant", (evidence.id,))],
                [evidence],
            )
        except ValueError as exc:
            if "CROSS_BOUNDARY_EVIDENCE_WITHOUT_BRIDGE" not in str(exc):
                raise
        else:
            raise AssertionError("UNQUALIFIED_CROSS_KIND_EVIDENCE_TRANSPLANT")

    full = resolve_graph(
        [Claim("owner-approved-joint-mission", "native",
               "L4YAML+FRET_R2U2:unowned-operational-purpose")],
        [], [],
    )
    assert full.states["owner-approved-joint-mission"] == UNKNOWN
    return "CROSS_KIND_TRANSPLANT_REJECTED; JOINT_OPERATIONAL_PURPOSE_UNKNOWN"


def verdict(scenario, items, current, expected):
    typed = typed_states(items, current)
    ordinary = conventional_independent_direct_check(items, current)
    assert typed == expected, (scenario, typed, expected)
    assert ordinary == expected, (scenario, ordinary, expected)
    return {"scenario": scenario, "states": typed,
            "conventional": ordinary,
            "matched": typed == ordinary == expected}


def execute(l4_archive: Path, native_archive: Path, qualification_archive: Path):
    # The existing method-specific adapters authenticate the original archives
    # before any Receipt is admitted to the type/scope-only resolver.
    l4_w, l4_rec, l4_assessment = l4.export_l4_boundary(l4_archive)
    assert l4_assessment["whole_generator_correctness"] == UNKNOWN
    assert l4_assessment["axiom_free_claim"] == "REJECTED"
    assert l4_assessment["weak_offering"] == "REJECTED_AS_SUPPORT_FOR_STRONG_OBLIGATION"

    with tempfile.TemporaryDirectory(prefix="mg-cross-capstone-") as tmp:
        root = Path(tmp)
        native_dir = root / "native"
        native_dir.mkdir()
        rocket.verify_historical_artifacts(
            native_archive, qualification_archive, native_dir)
        assert json.loads((native_dir / "source-declaration.json").read_text())[
            "operational_owner_authority"] == UNKNOWN
        rocket_items = rocket.build_warrants(native_dir)
        items = [(l4_w, l4_rec), *rocket_items]
        assert len(items) == 3
        for w, receipt in items:
            admitted_route(w, receipt)
        current = current_from_real_bytes(l4_w, rocket_items, l4_archive, native_dir)
        results = []
        results.append(verdict("exact_original_archives", items, current, STATES))
        cross = assert_unwarranted_cross_kind_transplant(items)

        def altered(name, filename, replacement, expected):
            working = root / name
            shutil.copytree(native_dir, working)
            victim = working / filename
            victim.write_bytes(replacement(victim.read_bytes()))
            refreshed = current_from_real_bytes(l4_w, rocket_items, l4_archive, working)
            results.append(verdict(name, items, refreshed, expected))
            return refreshed

        source_mutation = altered(
            "actual_native_source_changed", "source.c2po",
            lambda b: b + b"\n-- mutated archived study source\n",
            {FORMAL: STATES[FORMAL], SOURCE: UNKNOWN, CHALLENGER: STATES[CHALLENGER]},
        )
        # Negative control: the real graph is only an applicability engine.
        # Trusting caller's unchanged map would be stale-green, not resolver bug.
        assert typed_states(items, current) == STATES
        assert typed_states(items, source_mutation)[SOURCE] == UNKNOWN

        altered("shared_native_source_declaration_changed", "source-declaration.json",
                lambda b: b + b" ", {FORMAL: STATES[FORMAL],
                                     SOURCE: UNKNOWN, CHALLENGER: UNKNOWN})

        altered("independent_native_qualification_changed", "independent-qualification.json",
                lambda b: b + b"\n", {FORMAL: STATES[FORMAL],
                                       SOURCE: UNKNOWN, CHALLENGER: UNKNOWN})

        altered("source_only_study_policy_changed", "policy-source.json",
                lambda b: b + b" ", {FORMAL: STATES[FORMAL],
                                     SOURCE: UNKNOWN, CHALLENGER: STATES[CHALLENGER]})

        altered("forged_inband_owner_approved", "native-result.json",
                lambda b: json.dumps({**json.loads(b), "owner_approved": True},
                                     sort_keys=True).encode(),
                {FORMAL: STATES[FORMAL], SOURCE: UNKNOWN, CHALLENGER: UNKNOWN})

        # Genuine L4 archive bytes, not in-band declared hash: changed archive
        # no longer qualifies. FRET receipts remain sound within their scope.
        l4_mutated = root / "l4-different.zip"
        l4_mutated.write_bytes(l4_archive.read_bytes() + b"\n")
        changed = current_from_real_bytes(l4_w, rocket_items, l4_mutated, native_dir)
        results.append(verdict("real_L4_archive_changed", items, changed,
                               {FORMAL: UNKNOWN, SOURCE: STATES[SOURCE],
                                CHALLENGER: STATES[CHALLENGER]}))
        try:
            l4.export_l4_boundary(l4_mutated)
        except ValueError as exc:
            assert "ARTIFACT_IDENTITY_MISMATCH" in str(exc)
        else:
            raise AssertionError("STALE_L4_ARCHIVE_RE_ADMITTED")

        # Removing actual evidence forces conservative withdrawal.
        working = root / "missing-original-native-evidence"
        shutil.copytree(native_dir, working)
        (working / "source.bin").unlink()
        missing = current_from_real_bytes(l4_w, rocket_items, l4_archive, working)
        results.append(verdict("missing_native_file_fail_closed", items, missing,
                               {FORMAL: STATES[FORMAL], SOURCE: UNKNOWN,
                                CHALLENGER: UNKNOWN}))

        working = root / "missing-original-L4-evidence"
        missing_l4 = current_from_real_bytes(
            l4_w, rocket_items, root / "nonexistent_l4.zip", native_dir)
        results.append(verdict("missing_L4_artifact_fail_closed", items, missing_l4,
                               {FORMAL: UNKNOWN, SOURCE: STATES[SOURCE],
                                CHALLENGER: STATES[CHALLENGER]}))

        # Each method source independently survives unrelated changes.
        assert all(r["matched"] for r in results)
        # Controls explicitly keep broader claims UNKNOWN rather than
        # manufacture a joint mission owner or new permission.
        return {
            "schema": "mathgraph.cross-domain-assurance-capstone.v0",
            "execution_mode": "EXACT_HISTORICAL_ARTIFACT_READBACK_NOT_FRESH_NATIVE_TOOLS",
            "status": "WARRANTED_BOUNDED_RETROSPECTIVE",
            "root_source": {"L4YAML_adapter_controller": l4.CONTROLLER,
                            "FRET_source": rocket.FRET_SHA,
                            "R2U2_source": "2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a"},
            "source_archives": {
                "l4": sha(l4_archive),
                "rocket_native": sha(native_archive),
                "rocket_independent": sha(qualification_archive),
            },
            "original_method_specific_conditions": {
                "l4_strong_lean_claim": l4_assessment["state"],
                "l4_whole_generator": UNKNOWN,
                "l4_axiom_free_claim": "REJECTED",
                "rocket_natively_observed_positions_historical": 64,
                "rocket_owner_intent": UNKNOWN,
                "rocket_repair_grant": "DENIED",
            },
            "cross_boundary": cross,
            "scenario_count": len(results),
            "scripted_baseline_ties": sum(x["matched"] for x in results),
            "scenarios": results,
            "unsupported_joint_operational_decision": UNKNOWN,
            "owner_authenticated": False,
            "independent_human_reviewer": "NOT_RUN",
            "human_cost_comparison": "NOT_MEASURED",
            "not_a_new_discovery": True,
            "production_action_permission": "NONE",
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--l4", required=True, type=Path)
    parser.add_argument("--native", required=True, type=Path)
    parser.add_argument("--qual", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    a = parser.parse_args()
    report = execute(a.l4, a.native, a.qual)
    a.output.parent.mkdir(exist_ok=True, parents=True)
    a.output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print("CROSS_DOMAIN_CAPSTONE_PASS",
          json.dumps({"scenarios":report["scenario_count"],
                      "baseline_ties":report["scripted_baseline_ties"],
                      "methods": ["Lean-formal", "FRET-C2PO-R2U2-native"],
                      "joint_mission": report["unsupported_joint_operational_decision"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
