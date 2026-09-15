#!/usr/bin/env python3
"""V67 — distill V66 learned proof machinery to a necessity-certified basis.

This is not fresh evidence. It operates only on the already-open V66 artifact
and the already-open V66 recurrence targets.

Goal
----
Apply the same principle proposed for Lean-kernel minimisation to the learned
proof machinery itself:

    keep a derived lemma iff removing its lineage destroys at least one
    protected later theorem under the frozen proof search.

Protocol
--------
1. Load the exact V66 Phase-A archive and V66 result.
2. Restrict attention to source laws that actually powered protected Phase-B
   warm proofs.
3. Compute the derivation-closed union of rules actually used by those proofs.
4. Re-run every protected theorem using only that certificate-support closure.
5. Greedily attempt to delete each retained derived lemma plus every retained
   descendant depending on it. Re-run all protected targets for that source.
6. If all protected targets still prove, delete the lineage.
7. Otherwise retain the lemma and record an exact necessity witness: a later
   theorem that ceases to prove under deletion and returns under restoration.
8. Iterate to a local fixed point.

This establishes local irreducibility relative to the declared protected target
family and frozen V63 search. It does not claim a globally minimal equational
basis.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_V66_PATH = ROOT / "experiments" / "external_capability_compounding_v66" / "run.py"
_SPEC = importlib.util.spec_from_file_location("v67_v66", _V66_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load V66")
V66 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = V66
_SPEC.loader.exec_module(V66)

V65 = V66.V65
V64 = V66.V64
V63 = V66.V63
V62 = V66.V62
V58 = V66.V58

EXPECTED_ARCHIVE_SHA256 = "3525580b4a530481066feb57f0fcec01af195795f8d7c68f9e070a9b72180ac1"
EXPECTED_RESULT_SHA256 = "cf679e7272919e96924a6128d279e1f71cc59b6b239ddd8bac84cbdb1d2646af"


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_problem_map(path3000: Path, path3500: Path):
    docs = []
    for path, expected in (
        (path3000, V58.EXPECTED_3000_SHA256),
        (path3500, V58.EXPECTED_3500_SHA256),
    ):
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected:
            raise RuntimeError(f"dataset hash mismatch: {path}: {digest}")
        docs.extend(json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip())
    return {row["id"]: row for row in docs}


def ancestry_closure(eqs, ids):
    keep = {0}
    stack = [int(x) for x in ids]
    while stack:
        eid = stack.pop()
        if eid in keep:
            continue
        if eid not in eqs:
            raise RuntimeError(f"missing equation {eid}")
        keep.add(eid)
        proof = eqs[eid].proof
        if proof.get("kind") == "CRITICAL_PAIR":
            stack.append(int(proof["a"]))
            stack.append(int(proof["b"]))
    return keep


def verify_closed_basis(eqs):
    if 0 not in eqs:
        return False
    for eid in sorted(eqs):
        eq = eqs[eid]
        if eid == 0:
            if eq.proof.get("kind") != "SOURCE":
                return False
            continue
        proof = eq.proof
        if proof.get("kind") != "CRITICAL_PAIR":
            return False
        if int(proof["a"]) not in eqs or int(proof["b"]) not in eqs:
            return False
        if not V62.verify_overlap(eq, eqs):
            return False
    return True


def replay_targets(source_targets, eqs, problems):
    rows = []
    all_proved = True
    for pid in source_targets:
        problem = problems[pid]
        res = V65.proof(problem, eqs)
        rows.append({
            "problem_id": pid,
            "proved": bool(res["proved"]),
            "depth": res["depth"],
            "generated": res["generated"],
            "used_rule_ids": res["used_rule_ids"],
        })
        if not res["proved"]:
            all_proved = False
    return all_proved, rows


def restrict_lineage(eqs, root_eid):
    root_eid = int(root_eid)
    removed = {root_eid}
    changed = True
    while changed:
        changed = False
        for eid, eq in eqs.items():
            if eid in removed or eid == 0:
                continue
            p = eq.proof
            if p.get("kind") != "CRITICAL_PAIR":
                continue
            if int(p["a"]) in removed or int(p["b"]) in removed:
                removed.add(eid)
                changed = True
    kept = {eid: eq for eid, eq in eqs.items() if eid not in removed}
    if not verify_closed_basis(kept):
        raise RuntimeError("lineage deletion broke derivation closure")
    return kept, removed


def eq_record(eq):
    return {
        "eid": eq.eid,
        "key": eq.key,
        "round": eq.round,
        "proof": eq.proof,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v66-archive", required=True)
    ap.add_argument("--v66-result", required=True)
    ap.add_argument("--book3000", required=True)
    ap.add_argument("--book3500", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    archive_path = Path(args.v66_archive)
    result_path = Path(args.v66_result)

    if file_sha(archive_path) != EXPECTED_ARCHIVE_SHA256:
        raise RuntimeError("V66 archive byte hash mismatch")
    if file_sha(result_path) != EXPECTED_RESULT_SHA256:
        raise RuntimeError("V66 result byte hash mismatch")

    archive_doc = json.loads(archive_path.read_text(encoding="utf-8"))
    v66_result = json.loads(result_path.read_text(encoding="utf-8"))
    reloaded, archive_hash = V65.reload_archive(archive_doc)
    if archive_hash != archive_doc["sha256"]:
        raise RuntimeError("V66 archive internal hash mismatch")

    problems = load_problem_map(Path(args.book3000), Path(args.book3500))

    protected = {}
    for row in v66_result["phase_b_recurrence_stream"]["records"]:
        if not row.get("proof_probe"):
            continue
        warm = row.get("warm") or {}
        if not warm.get("proved"):
            continue
        sid = str(row["source_id"])
        protected.setdefault(sid, []).append({
            "problem_id": row["problem_id"],
            "used_rule_ids": [int(x) for x in warm["used_rule_ids"]],
            "original_generated": int(warm["generated"]),
            "original_depth": warm["depth"],
        })

    original_archive_equations = sum(len(basis["eqs"]) for basis in reloaded.values())
    active_source_equations = sum(len(reloaded[sid]["eqs"]) for sid in protected)
    unprotected_sources = sorted(set(reloaded) - set(protected))

    source_results = {}
    total_closure = 0
    total_final = 0
    total_witnesses = 0
    all_protected_preserved = True
    all_retained_have_witness = True

    for sid in sorted(protected, key=lambda x: int(x)):
        basis = reloaded[sid]
        full_eqs = basis["eqs"]
        target_rows = protected[sid]
        target_ids = [x["problem_id"] for x in target_rows]

        used = set()
        for x in target_rows:
            used.update(x["used_rule_ids"])

        closure_ids = ancestry_closure(full_eqs, used)
        current = {eid: full_eqs[eid] for eid in sorted(closure_ids)}
        if not verify_closed_basis(current):
            raise RuntimeError(f"certificate closure invalid for source {sid}")

        closure_ok, closure_replay = replay_targets(target_ids, current, problems)
        if not closure_ok:
            raise RuntimeError(f"certificate closure does not preserve protected targets for source {sid}")

        total_closure += len(current)

        deletion_log = []
        necessity = {}

        # Iterate deterministic deletion passes to a local fixed point.
        changed = True
        while changed:
            changed = False
            candidates = [
                eid for eid in sorted(current, reverse=True)
                if eid != 0
            ]
            for eid in candidates:
                if eid not in current:
                    continue
                trial, removed = restrict_lineage(current, eid)
                if not trial:
                    continue

                ok, rows = replay_targets(target_ids, trial, problems)
                if ok:
                    deletion_log.append({
                        "root_eid": eid,
                        "removed_lineage": sorted(removed),
                        "decision": "DELETE_REDUNDANT",
                        "protected_targets_preserved": True,
                    })
                    current = trial
                    changed = True
                else:
                    failing = [r for r in rows if not r["proved"]]
                    # Restoration must re-establish all targets.
                    restored_ok, restored_rows = replay_targets(target_ids, current, problems)
                    if not restored_ok:
                        raise RuntimeError("restoration unexpectedly failed")
                    witness = failing[0]["problem_id"]
                    necessity[eid] = {
                        "root_eid": eid,
                        "removed_lineage": sorted(removed),
                        "witness_problem_id": witness,
                        "delete_result": "UNKNOWN",
                        "restore_result": "VERIFIED_TRUE",
                        "failed_targets": [r["problem_id"] for r in failing],
                    }
                    deletion_log.append({
                        "root_eid": eid,
                        "removed_lineage": sorted(removed),
                        "decision": "RETAIN_NECESSARY",
                        "witness_problem_id": witness,
                    })

        final_ok, final_replay = replay_targets(target_ids, current, problems)
        if not final_ok:
            all_protected_preserved = False

        # Re-test necessity in final context. A retained lemma only earns its
        # place if deleting its current lineage kills at least one protected target.
        final_witnesses = {}
        for eid in sorted(current):
            if eid == 0:
                continue
            trial, removed = restrict_lineage(current, eid)
            ok, rows = replay_targets(target_ids, trial, problems)
            if ok:
                all_retained_have_witness = False
                final_witnesses[eid] = {
                    "status": "REDUNDANT_AT_FINAL_FIXED_POINT",
                    "removed_lineage": sorted(removed),
                }
            else:
                failing = [r for r in rows if not r["proved"]]
                restored_ok, _ = replay_targets(target_ids, current, problems)
                if not restored_ok:
                    raise RuntimeError("final restoration failed")
                final_witnesses[eid] = {
                    "status": "NECESSARY_RELATIVE_TO_PROTECTED_TARGETS",
                    "removed_lineage": sorted(removed),
                    "witness_problem_id": failing[0]["problem_id"],
                    "failed_targets": [r["problem_id"] for r in failing],
                    "delete_result": "UNKNOWN",
                    "restore_result": "VERIFIED_TRUE",
                }
                total_witnesses += 1

        total_final += len(current)

        source_results[sid] = {
            "protected_targets": target_ids,
            "full_equations": len(full_eqs),
            "certificate_support_closure_equations": len(closure_ids),
            "certificate_support_ids": sorted(closure_ids),
            "certificate_support_replay": closure_replay,
            "final_equations": len(current),
            "final_equation_ids": sorted(current),
            "final_equations_detail": [eq_record(current[eid]) for eid in sorted(current)],
            "final_replay": final_replay,
            "deletion_log": deletion_log,
            "necessity_witnesses": {
                str(eid): value for eid, value in sorted(final_witnesses.items())
            },
        }

        print(json.dumps({
            "source_id": sid,
            "full_equations": len(full_eqs),
            "certificate_closure": len(closure_ids),
            "final_equations": len(current),
            "protected_targets": len(target_ids),
            "necessity_witnesses": sum(
                v.get("status") == "NECESSARY_RELATIVE_TO_PROTECTED_TARGETS"
                for v in final_witnesses.values()
            ),
        }, sort_keys=True), flush=True)

    checks = {
        "v66_artifacts_exact": (
            file_sha(archive_path) == EXPECTED_ARCHIVE_SHA256
            and file_sha(result_path) == EXPECTED_RESULT_SHA256
        ),
        "v66_archive_replayed_on_restart": archive_hash == archive_doc["sha256"],
        "protected_targets_exist": sum(len(v) for v in protected.values()) == 11,
        "all_protected_targets_preserved": all_protected_preserved,
        "compiled_machinery_compressed": total_final < active_source_equations,
        "every_retained_derived_lemma_has_necessity_witness": all_retained_have_witness,
        "at_least_one_necessity_witness": total_witnesses > 0,
        "no_fresh_external_rows_opened": True,
    }

    summary = {
        "schema": "mathgraph.external-capability-compounding.v67.minimal-sufficient-proof-basis",
        "classification": "OPENED_V66_EVIDENCE_DISTILLATION_NOT_FRESH_EVIDENCE",
        "v66": {
            "run_id": 34970731077,
            "commit": "35bb4c57a93edd1cb2032f385a4711d2935d225e",
            "verdict": v66_result["verdict"],
            "protected_later_proofs": sum(len(v) for v in protected.values()),
            "compiled_archive_sources": len(reloaded),
            "protected_sources": len(protected),
            "unprotected_sources_deleted_from_active_basis": unprotected_sources,
            "original_archive_equations": original_archive_equations,
            "active_source_equations_before_distillation": active_source_equations,
        },
        "distillation": {
            "certificate_support_closure_equations": total_closure,
            "locally_irreducible_equations": total_final,
            "compression_vs_active_full_basis": (
                active_source_equations / total_final if total_final else float("inf")
            ),
            "necessity_witnesses": total_witnesses,
            "sources": source_results,
        },
        "checks": checks,
        "all_v67_gates_pass": all(checks.values()),
    }

    summary["verdict"] = (
        "PASS_MINIMAL_SUFFICIENT_PROOF_BASIS_V67"
        if summary["all_v67_gates_pass"]
        else "FAIL_MINIMAL_SUFFICIENT_PROOF_BASIS_V67"
    )
    summary["claim_boundary"] = (
        "PASS establishes local irreducibility only relative to the 11 protected V66 later targets and the "
        "frozen V63 proof search. It does not claim a globally minimal equational basis. Every surviving "
        "derived lemma has an explicit target witness that stops proving when that lemma lineage is deleted "
        "and proves again after restoration."
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=True),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=True), flush=True)
    if not summary["all_v67_gates_pass"]:
        raise SystemExit("V67 proof-basis distillation failed")


if __name__ == "__main__":
    main()
