"""Frozen LeanIn primitive-authority withdrawal probe.

Requires the *unchanged* MathGraph mathgraph_check.warrant_resolution resolver.
This is an evidence-conditioned documentation/axiom-dependency test, NOT
verification that LeanIn's native FFI implements its model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from mathgraph_check.warrant_resolution import (
    Claim, Receipt, Route, QualifiedRelation, compare_snapshots, resolve_graph,
)

SOURCE_COMMIT = "a7e8e9ca4fef75b6eff665925ff17aaf9ff35029"
UPSTREAM_CI_RUN = 39486730021
# Frozen independently of the probe's dynamic construction: prevents a parser
# from passing simply by faithfully repeating its own erroneous input.
EXPECTED = {
    "LeanIn.lock_wait_unlock_postcondition": {"lock_spec", "unlock_spec", "wait_spec"},
    "LeanIn.readings_monotone_across_a_call": {"clock_spec", "lock_spec"},
    "LeanIn.wait_cycle_reachable": {"propext", "Quot.sound"},
    "LeanIn.notifyOne_no_additions": {"propext", "notifyOne_spec"},
    "LeanIn.Model.reachable_noDrop": {"propext", "Classical.choice", "Quot.sound"},
}
LOGICAL_AXIOMS = {"propext", "Quot.sound", "Classical.choice"}
PRIMITIVES = set().union(*(a - LOGICAL_AXIOMS for a in EXPECTED.values()))
FORMAL_SCOPE = f"LeanIn@{SOURCE_COMMIT}:conditional-kernel-proof"
DOCUMENTARY_SCOPE = f"LeanIn@{SOURCE_COMMIT}:source-conditional-descriptions"
RUNTIME_SCOPE = f"LeanIn@{SOURCE_COMMIT}:native-implementation-refinement"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_axioms(log: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for line in log.splitlines():
        if m := re.search(r"'(LeanIn\.[^']+)' depends on axioms: \[([^\]]*)\]", line):
            key = m.group(1)
            require(key not in out, f"DUPLICATED_AXIOM_AUDIT:{key}")
            raw = set(m.group(2).split(", ")) if m.group(2) else set()
            # Lean prints primitive names fully qualified outside the source
            # namespace. Normalize only names anchored to the pinned contract.
            out[key] = {a.removeprefix("LeanIn.") if a.startswith("LeanIn.")
                        and a.removeprefix("LeanIn.") in PRIMITIVES else a
                        for a in raw}
        elif m := re.search(r"'(LeanIn\.[^']+)' does not depend on any axioms", line):
            key = m.group(1)
            require(key not in out, f"DUPLICATED_AXIOM_AUDIT:{key}")
            out[key] = set()
    # Enforce exact signature, rejecting silent new axioms (including sorryAx).
    require(set(out) == set(EXPECTED), f"MISSING_OR_EXTRA_PROOF_LINES:{set(out)^set(EXPECTED)}")
    for key, expected in EXPECTED.items():
        require(out[key] == expected, f"AXIOM_DEPENDENCY_DRIFT:{key}:{out[key]^expected}")
    return out


def check_bridge_declarations(content: str, dependencies: dict[str, set[str]]) -> None:
    for primitive in set().union(*(a - LOGICAL_AXIOMS for a in dependencies.values())):
        matches = re.findall(rf"(?m)^axiom\s+{re.escape(primitive)}\b", content)
        require(len(matches) == 1, f"UNAUTHENTICATED_BRIDGE_DECLARATION:{primitive}:{len(matches)}")
    for theorem in list(EXPECTED)[:-1]:
        name = theorem.rsplit(".", 1)[-1]
        require(re.search(rf"(?m)^#print axioms LeanIn\.{re.escape(name)}\s*$", content) is not None,
                f"MISSING_SOURCE_AXIOM_AUDIT:{theorem}")


def create_graph(dependencies: dict[str, set[str]]):
    """No fake native adapter: operational claims stay UNKNOWN, even at baseline."""
    claims: list[Claim] = []
    routes: list[Route] = []
    receipts = [
        Receipt("native.lean.probe", "formal", FORMAL_SCOPE),
        Receipt("source.proof.provenance", "documentary", DOCUMENTARY_SCOPE),
        Receipt("source.ci.job", "documentary", DOCUMENTARY_SCOPE),
        Receipt("source.readme.benchmark", "documentary", DOCUMENTARY_SCOPE),
    ]
    for primitive in sorted(PRIMITIVES):
        receipts.append(Receipt(f"declared.{primitive}", "documentary", DOCUMENTARY_SCOPE))
    for theorem in sorted(dependencies):
        basename = theorem.removeprefix("LeanIn.")
        claims += [Claim(f"proof.{basename}", "formal", FORMAL_SCOPE),
                   Claim(f"conditional_source.{basename}", "documentary", DOCUMENTARY_SCOPE)]
        routes += [Route(f"proof.{basename}", ("native.lean.probe",)),
                   Route(f"conditional_source.{basename}",
                         ("source.proof.provenance",) +
                         tuple(f"declared.{p}" for p in sorted(dependencies[theorem]-LOGICAL_AXIOMS)))]
    claims += [Claim("native.model_refines_runtime", "formal", RUNTIME_SCOPE),
               Claim("observed.ci.scenarios_failed", "documentary", DOCUMENTARY_SCOPE),
               Claim("observed.readme.performance_published", "documentary", DOCUMENTARY_SCOPE)]
    routes += [Route("observed.ci.scenarios_failed", ("source.ci.job",)),
               Route("observed.readme.performance_published", ("source.readme.benchmark",))]
    # No route to native.model_refines_runtime: no independently verified model/FFI adapter exists.
    return claims, routes, receipts


def run_graph_tests(deps: dict[str, set[str]]) -> dict:
    claims, routes, receipts = create_graph(deps)
    before = resolve_graph(claims, routes, receipts)
    require(before.states["native.model_refines_runtime"] == "UNKNOWN", "FALSE_RUNTIME_PROMOTION")
    for key, val in before.states.items():
        if key.startswith("proof."):
            require(val == "WARRANTED_BOUNDED", f"MISSING_KERNEL_RECEIPT:{key}")
        elif key != "native.model_refines_runtime":
            require(val == "SOURCE_DOCUMENTED", f"DOCUMENTARY_NOT_DOCUMENTARY:{key}")

    affected = {}
    for primitive in sorted(PRIMITIVES):
        withdrawn = frozenset({f"declared.{primitive}"})
        changed = resolve_graph(claims, routes, receipts, withdrawn=withdrawn)
        delta = {k for k in before.states if changed.states[k] != before.states[k]}
        expected_delta = {"conditional_source."+t.removeprefix("LeanIn.")
                          for t, axioms in deps.items() if primitive in axioms}
        require(delta == expected_delta, f"NONSELECTIVE_WITHDRAWAL:{primitive}:{delta^expected_delta}")
        require(changed.states["native.model_refines_runtime"] == "UNKNOWN", "RUNTIME_FALSE_WARRANT")
        require(all(changed.states[k] == before.states[k]
                    for k in before.states if k.startswith("proof.")), "KERNEL_PROOF_LOST")
        require(all(compare_snapshots(before.states, changed.states)[k]["after"] == "STALE"
                    for k in delta), "DID_NOT_RETRACT")
        affected[primitive] = sorted(delta)

    # A stronger second loss must not cause accidental collateral damage.
    dual = frozenset({"declared.wait_spec", "declared.lock_spec"})
    both = resolve_graph(claims, routes, receipts, withdrawn=dual)
    union = set(affected["wait_spec"]) | set(affected["lock_spec"])
    require({k for k in before.states if both.states[k] != before.states[k]} == union,
            "NONLOCAL_TWO_AUTHORITY_WITHDRAWAL")
    # Restore deterministically, byte-exact state map, not merely matching counts.
    restored = resolve_graph(claims, routes, receipts)
    require(dict(restored.states) == dict(before.states), "RESTORATION_NOT_EXACT")

    # Failed cross-scope elevation: the source-documented claim cannot become a
    # warranted native theorem by citing a native probe from a different scope.
    attempts = 0
    for fabricated in [
        Route("native.model_refines_runtime", ("source.proof.provenance",)),
        Route("native.model_refines_runtime", ("native.lean.probe",),
              ("proof.lock_wait_unlock_postcondition",)),
    ]:
        attempts += 1
        try:
            resolve_graph(claims, routes + [fabricated], receipts)
        except ValueError as err:
            require("CROSS_BOUNDARY" in str(err), f"WRONG_ADMISSION_ERROR:{err}")
        else:
            raise AssertionError("FORGED_NATIVE_AUTHORITY_ACCEPTED")
    # A self-declared relation is not an independently qualified semantic bridge.
    invalid = QualifiedRelation(
        "fake", "documentary", DOCUMENTARY_SCOPE, "formal", RUNTIME_SCOPE,
        "source.proof.provenance", ("native.lean.probe",),
        Route("native.model_refines_runtime", ("native.lean.probe",), relation="fake"),
    )
    attempts += 1
    try:
        resolve_graph(claims, routes, receipts, relations=[invalid])
    except ValueError as err:
        require("UNQUALIFIED_RELATION" in str(err), f"WRONG_RELATION_ERROR:{err}")
    else:
        raise AssertionError("SELF_DECLARED_BRIDGE_ACCEPTED")
    return {
        "baseline_states": dict(before.states),
        "withdrawn_contract_effects": affected,
        "dual_withdrawal_effect": sorted(union),
        "runtime_refinement_before_and_after": "UNKNOWN",
        "formal_kernel_claims_preserved_under_runtime_authority_withdrawal": 5,
        "native_authority_forgery_controls_rejected": attempts,
        "reclosure_exact_restore": True,
    }


def run(args: argparse.Namespace) -> dict:
    root = args.source.resolve()
    commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    require(commit == SOURCE_COMMIT, f"UNPINNED_SOURCE:{commit}")
    source = (root / "LeanIn/Theory/Bridge.lean").read_bytes()
    log_bytes = args.axioms.read_bytes()
    deps = parse_axioms(log_bytes.decode())
    check_bridge_declarations(source.decode(), deps)
    try:
        parse_axioms(log_bytes.decode().replace("wait_spec]", "other_spec]", 1))
    except AssertionError as err:
        require("AXIOM_DEPENDENCY_DRIFT" in str(err), "WRONG_PROOF_TAMPER_REASON")
    else:
        raise AssertionError("TAMPERED_AXIOM_LOG_ACCEPTED")
    try:
        check_bridge_declarations(source.decode().replace("axiom wait_spec", "axiom other_spec", 1), deps)
    except AssertionError as err:
        require("UNAUTHENTICATED_BRIDGE_DECLARATION" in str(err), "WRONG_SOURCE_TAMPER_REASON")
    else:
        raise AssertionError("TAMPERED_SOURCE_DECLARATION_ACCEPTED")
    graph = run_graph_tests(deps)
    result = {
        "method": "Metalogic/MathGraph existing resolver, source-derived native Lean axiom probe",
        "upstream_source": f"https://github.com/scidonia/leanin/commit/{SOURCE_COMMIT}",
        "source_commit": SOURCE_COMMIT,
        "bridge_sha256": sha(source),
        "proof_axiom_log_sha256": sha(log_bytes),
        "observed_axioms": {k: sorted(v) for k,v in sorted(deps.items())},
        "upstream_ci_run": f"https://github.com/scidonia/leanin/actions/runs/{UPSTREAM_CI_RUN}",
        "tampering_negative_controls": 2,
        "graph": graph,
        "epistemic_limit": "SOURCE_DOCUMENTED is not native runtime correctness; no model-to-FFI formal adapter",
    }
    if args.upstream_ci_metadata:
        jobs = json.loads(args.upstream_ci_metadata.read_text())["jobs"]
        status = {j["name"]: j["conclusion"] for j in jobs}
        require(status.get("gate") == "success" and status.get("scenarios") == "failure",
                f"UPSTREAM_CI_OBSERVATION_CHANGED:{status}")
        result["upstream_ci_jobs"] = status
        result["upstream_ci_jobs_sha256"] = sha(args.upstream_ci_metadata.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--axioms", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--upstream-ci-metadata", type=Path)
    result = run(ap.parse_args())
    print(json.dumps({"source_commit": result["source_commit"],
                      "withdrawn_contract_effects":result["graph"]["withdrawn_contract_effects"],
                      "controls_rejected":result["graph"]["native_authority_forgery_controls_rejected"]
                          +result["tampering_negative_controls"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
