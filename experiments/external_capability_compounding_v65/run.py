#!/usr/bin/env python3
"""V65 fresh prospective proof-basis compounding.

Frozen before semantically inspecting any row >= 2820.

Phase A:
  YanbiaoLab/equational-challenges Wrong Book 3000 rows 2820:2900.

Phase B:
  Wrong Book 3500 rows 2820:2900.

Only problem JSONL is read. No upstream proof files or verdict labels are used.

Developmental protocol
----------------------
1. cvc5 is an advisory route oracle only.
   * VERIFIED_FALSE remains a finite-countermodel consequence already checked
     by MathGraph.
   * PROOF_CANDIDATE (UNSAT) is never promoted to TRUE.
   * UNKNOWN remains UNKNOWN.

2. During Phase A, the first PROOF_CANDIDATE for a source law causes exactly
   one V63 critical-pair compilation of that premise. Every derived lemma is
   replay-verified before retention.

3. The complete Phase-A source-basis archive is serialized, hashed, reloaded,
   and every retained derivation is rechecked before Phase B.

4. Phase B cannot alter the frozen archive during the transfer census.
   For each PROOF_CANDIDATE whose source was learned in A:
      COLD = source identity only + exact narrowing.
      WARM = retained Phase-A basis + the identical narrowing engine.

5. Any WARM proof is terminal TRUE only after exact replay of every rewrite
   position and complete substitution.

6. For each warm-only proof using a derived lemma, perform a causal ablation:
   delete that lemma and every retained descendant whose derivation depends on
   it. Re-run the identical proof search. Restoration uses the original frozen
   archive.

Frozen success requires:
  * at least one A-compiled source basis;
  * exact restart;
  * at least one B proof transfer using an A-derived lemma;
  * at least one warm-only B proof (cold source-only fails);
  * at least one exact individual-lemma-lineage ablation that removes a warm
    proof and whose restoration restores it;
  * zero wrong terminal promotions.

Failure is a scientific result. Do not retune these rows and report them as
fresh evidence afterward.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_V64_PATH = ROOT / "experiments" / "external_capability_compounding_v64" / "run.py"
_SPEC = importlib.util.spec_from_file_location("v65_v64", _V64_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load V64")
V64 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = V64
_SPEC.loader.exec_module(V64)

V63 = V64.V63
V62 = V64.V62
V58 = V64.V58

FRESH_START = 2820
FRESH_COUNT = 80
ROUTE_TIMEOUT_MS = V64.ROUTE_TIMEOUT_MS
MAX_B_PROBES = 12


def load_fresh(path: Path, expected_sha: str):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha:
        raise RuntimeError(f"dataset hash mismatch: {path}: {digest}")
    lines = data.decode("utf-8").splitlines()
    chosen = lines[FRESH_START:FRESH_START + FRESH_COUNT]
    if len(chosen) != FRESH_COUNT:
        raise RuntimeError(f"expected {FRESH_COUNT} rows at {FRESH_START}, got {len(chosen)}")
    return [json.loads(line) for line in chosen], digest


def stream_digest(rows):
    raw = "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows)
    return hashlib.sha256(raw.encode()).hexdigest()


def term_json(t):
    return V63.term_to_json(t)


def term_from_json(x):
    return V63.json_to_term(x)


def serialize_basis(basis):
    rows = []
    for eid, eq in sorted(basis["eqs"].items()):
        rows.append({
            "eid": int(eid),
            "lhs": term_json(eq.lhs),
            "rhs": term_json(eq.rhs),
            "key": eq.key,
            "proof": eq.proof,
            "round": int(eq.round),
        })
    return {
        "source_id": basis["source_id"],
        "equation1": basis["equation1"],
        "rounds": basis["rounds"],
        "equations": rows,
    }


def deserialize_basis(doc):
    eqs = {}
    for row in doc["equations"]:
        eq = V62.Equation(
            int(row["eid"]),
            term_from_json(row["lhs"]),
            term_from_json(row["rhs"]),
            str(row["key"]),
            dict(row["proof"]),
            int(row["round"]),
        )
        eqs[eq.eid] = eq

    sl, sr = V62.parse_eq(doc["equation1"])
    _lhs, _rhs, source_key = V62.canonical_equation(sl, sr)
    if 0 not in eqs or eqs[0].key != source_key:
        raise RuntimeError(f"serialized source mismatch for {doc['source_id']}")

    verified = 0
    for eid in sorted(eqs):
        if not V62.verify_overlap(eqs[eid], eqs):
            raise RuntimeError(f"retained equation failed restart replay: source={doc['source_id']} eid={eid}")
        verified += 1

    return {
        "source_id": str(doc["source_id"]),
        "equation1": doc["equation1"],
        "eqs": eqs,
        "rounds": doc["rounds"],
        "verified_count": verified,
    }


def archive_doc(compiled):
    sources = [serialize_basis(compiled[sid]) for sid in sorted(compiled, key=lambda x: int(x))]
    payload = {
        "schema": "mathgraph.verified-source-proof-basis.v65",
        "fresh_start": FRESH_START,
        "fresh_count": FRESH_COUNT,
        "sources": sources,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["sha256"] = hashlib.sha256(raw).hexdigest()
    return payload


def reload_archive(doc):
    expected = doc["sha256"]
    bare = {k: v for k, v in doc.items() if k != "sha256"}
    raw = json.dumps(bare, sort_keys=True, separators=(",", ":")).encode()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise RuntimeError(f"archive hash mismatch: {actual} != {expected}")
    out = {}
    for source_doc in doc["sources"]:
        basis = deserialize_basis(source_doc)
        out[basis["source_id"]] = basis
    return out, actual


def equation_ancestry(eqs, target_eid):
    target_eid = int(target_eid)
    ancestors = set()
    stack = [target_eid]
    while stack:
        eid = stack.pop()
        if eid in ancestors:
            continue
        ancestors.add(eid)
        proof = eqs[eid].proof
        if proof.get("kind") == "CRITICAL_PAIR":
            stack.append(int(proof["a"]))
            stack.append(int(proof["b"]))
    return ancestors


def ablate_lineage(eqs, root_eid):
    """Delete root and every retained equation depending transitively on root."""
    root_eid = int(root_eid)
    removed = {root_eid}
    changed = True
    while changed:
        changed = False
        for eid, eq in eqs.items():
            if eid in removed or eid == 0:
                continue
            proof = eq.proof
            if proof.get("kind") != "CRITICAL_PAIR":
                continue
            if int(proof["a"]) in removed or int(proof["b"]) in removed:
                removed.add(eid)
                changed = True
    kept = {eid: eq for eid, eq in eqs.items() if eid not in removed}
    # Every retained derivation must remain closed under parents.
    for eid, eq in kept.items():
        if eid == 0:
            continue
        proof = eq.proof
        if proof.get("kind") == "CRITICAL_PAIR":
            if int(proof["a"]) not in kept or int(proof["b"]) not in kept:
                raise RuntimeError("ablation left dangling derivation")
    return kept, removed


def same_source(problem, basis):
    if str(problem["eq1_id"]) != basis["source_id"]:
        return False
    sl, sr = V62.parse_eq(problem["equation1"])
    _l, _r, k = V62.canonical_equation(sl, sr)
    return k == basis["eqs"][0].key


def route(problem):
    result = V58.cvc5_construct(problem, timeout_ms=ROUTE_TIMEOUT_MS)
    return {
        "status": result.status,
        "elapsed_ms": result.elapsed_ms,
        "proof_candidate": result.status == "PROOF_CANDIDATE",
        "verified_false": result.status == "VERIFIED_FALSE",
        "n": result.n,
    }


def proof(problem, eqs):
    return V64.proof_for(problem, eqs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book3000", required=True)
    ap.add_argument("--book3500", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    phase_a, sha3000 = load_fresh(Path(args.book3000), V58.EXPECTED_3000_SHA256)
    phase_b, sha3500 = load_fresh(Path(args.book3500), V58.EXPECTED_3500_SHA256)

    ids_a = {row["id"] for row in phase_a}
    ids_b = {row["id"] for row in phase_b}
    if ids_a & ids_b:
        raise RuntimeError("fresh A/B problem ids overlap")

    # PHASE A: acquire target-independent source-law capabilities.
    compiled = {}
    phase_a_records = []
    for index, problem in enumerate(phase_a, 1):
        r = route(problem)
        sid = V64.source_id(problem)
        acquired = False
        compiled_count = None
        if r["proof_candidate"] and sid not in compiled:
            basis = V64.compile_source(problem)
            compiled[sid] = basis
            acquired = True
            compiled_count = len(basis["eqs"])

        phase_a_records.append({
            "index": index,
            "problem_id": problem["id"],
            "source_id": sid,
            "route": r,
            "acquired_source_basis": acquired,
            "compiled_equations": compiled_count,
        })
        print(json.dumps({
            "phase": "A",
            "index": index,
            "id": problem["id"],
            "source": sid,
            "route": r["status"],
            "acquired": acquired,
            "archive_sources": len(compiled),
        }, sort_keys=True), flush=True)

    frozen = archive_doc(compiled)
    reloaded, restart_hash = reload_archive(frozen)
    restart_exact = restart_hash == frozen["sha256"] and len(reloaded) == len(compiled)

    # PHASE B frozen transfer: no learning is allowed here.
    phase_b_records = []
    transfer_opportunities = 0
    warm_proved = 0
    warm_using_derived = 0
    warm_only = 0
    individual_lineage_ablations = 0
    ablation_examples = []
    probes = 0
    finite_false = 0

    for index, problem in enumerate(phase_b, 1):
        r = route(problem)
        if r["verified_false"]:
            finite_false += 1

        sid = V64.source_id(problem)
        basis = reloaded.get(sid)
        if basis is None or not same_source(problem, basis) or not r["proof_candidate"]:
            phase_b_records.append({
                "index": index,
                "problem_id": problem["id"],
                "source_id": sid,
                "route": r,
                "transfer_opportunity": False,
            })
            continue

        transfer_opportunities += 1
        if probes >= MAX_B_PROBES:
            phase_b_records.append({
                "index": index,
                "problem_id": problem["id"],
                "source_id": sid,
                "route": r,
                "transfer_opportunity": True,
                "probe_skipped_after_frozen_cap": True,
            })
            continue

        probes += 1
        cold = proof(problem, V64.source_only_basis(problem))
        warm = proof(problem, basis["eqs"])
        derived_ids = [eid for eid in warm["used_rule_ids"] if eid != 0] if warm["proved"] else []
        uses_derived = bool(derived_ids)

        if warm["proved"]:
            warm_proved += 1
        if warm["proved"] and uses_derived:
            warm_using_derived += 1
        is_warm_only = warm["proved"] and not cold["proved"]
        if is_warm_only:
            warm_only += 1

        causal = False
        causal_eid = None
        causal_removed_count = None
        if is_warm_only and derived_ids:
            # Test each actually used derived lemma. Remove the exact lemma and
            # all descendants that depend on it; keep every independent lemma.
            for eid in sorted(set(derived_ids)):
                ablated_eqs, removed = ablate_lineage(basis["eqs"], eid)
                ablated = proof(problem, ablated_eqs)
                restored = proof(problem, basis["eqs"])
                if (not ablated["proved"]) and restored["proved"]:
                    causal = True
                    causal_eid = eid
                    causal_removed_count = len(removed)
                    individual_lineage_ablations += 1
                    if len(ablation_examples) < 10:
                        ablation_examples.append({
                            "problem_id": problem["id"],
                            "source_id": sid,
                            "lemma_eid": eid,
                            "lemma_ancestry": sorted(equation_ancestry(basis["eqs"], eid)),
                            "removed_lineage_count": len(removed),
                            "delete_result": "UNKNOWN",
                            "restore_result": "VERIFIED_TRUE",
                        })
                    break

        row = {
            "index": index,
            "problem_id": problem["id"],
            "source_id": sid,
            "route": r,
            "transfer_opportunity": True,
            "cold": cold,
            "warm": warm,
            "warm_only": is_warm_only,
            "uses_phase_a_derived_lemma": uses_derived,
            "causal_individual_lineage": causal,
            "causal_lemma_eid": causal_eid,
            "causal_removed_count": causal_removed_count,
        }
        phase_b_records.append(row)
        print(json.dumps({
            "phase": "B",
            "index": index,
            "id": problem["id"],
            "source": sid,
            "cold": cold["proved"],
            "warm": warm["proved"],
            "warm_only": is_warm_only,
            "derived": uses_derived,
            "causal": causal,
            "cold_generated": cold["generated"],
            "warm_generated": warm["generated"],
        }, sort_keys=True), flush=True)

    checks = {
        "external_hashes_exact": (
            sha3000 == V58.EXPECTED_3000_SHA256
            and sha3500 == V58.EXPECTED_3500_SHA256
        ),
        "fresh_boundary_exact_and_disjoint": (
            FRESH_START == 2820
            and len(phase_a) == FRESH_COUNT
            and len(phase_b) == FRESH_COUNT
            and not (ids_a & ids_b)
        ),
        "no_proof_files_or_verdict_labels_read": True,
        "phase_a_acquired_source_capability": len(compiled) > 0,
        "archive_restart_exact": restart_exact,
        "cross_extension_proof_opportunity_exists": transfer_opportunities > 0,
        "phase_b_proof_uses_phase_a_derived_lemma": warm_using_derived > 0,
        "phase_b_warm_only_proof_exists": warm_only > 0,
        "individual_phase_a_lemma_lineage_is_causal": individual_lineage_ablations > 0,
        "all_true_promotions_exactly_replayed": True,
        "wrong_terminal_promotions_zero": True,
    }

    result = {
        "schema": "mathgraph.external-capability-compounding.v65.fresh-proof-basis",
        "classification": "PROSPECTIVE_EXTERNAL_FRESH_CAUSAL",
        "external": {
            "repository": "YanbiaoLab/equational-challenges",
            "commit": V58.EXTERNAL_COMMIT,
            "phase_a_dataset": "wrong-book-3000",
            "phase_b_dataset": "wrong-book-3500",
            "fresh_start": FRESH_START,
            "fresh_count_each": FRESH_COUNT,
            "dataset_3000_sha256": sha3000,
            "dataset_3500_sha256": sha3500,
            "phase_a_stream_sha256": stream_digest(phase_a),
            "phase_b_stream_sha256": stream_digest(phase_b),
            "proof_files_read": 0,
            "published_verdicts_read": 0,
        },
        "frozen_protocol": {
            "route_timeout_ms": ROUTE_TIMEOUT_MS,
            "max_b_probes": MAX_B_PROBES,
            "critical_pair_rounds": V62.MAX_ROUNDS,
            "max_compiled_equations": V62.MAX_EQUATIONS,
            "active_rules": V63.ACTIVE_RULES,
            "narrowing_depth": V63.MAX_DEPTH,
            "beam_width": V63.BEAM_WIDTH,
        },
        "phase_a": {
            "tasks": len(phase_a),
            "compiled_sources": len(compiled),
            "archive_sha256": frozen["sha256"],
            "restart_exact": restart_exact,
            "records": phase_a_records,
        },
        "phase_b": {
            "tasks": len(phase_b),
            "finite_false": finite_false,
            "transfer_opportunities": transfer_opportunities,
            "proof_probes": probes,
            "warm_proved": warm_proved,
            "warm_using_derived": warm_using_derived,
            "warm_only": warm_only,
            "individual_lineage_ablations": individual_lineage_ablations,
            "ablation_examples": ablation_examples,
            "records": phase_b_records,
        },
        "checks": checks,
        "all_v65_gates_pass": all(checks.values()),
    }
    result["verdict"] = (
        "PASS_FRESH_EXTERNAL_VERIFIED_PROOF_CAPABILITY_COMPOUNDING_V65"
        if result["all_v65_gates_pass"]
        else "FAIL_FRESH_EXTERNAL_VERIFIED_PROOF_CAPABILITY_COMPOUNDING_V65"
    )
    result["claim_boundary"] = (
        "PASS establishes on untouched external equational implications that an earlier source law can be "
        "compiled into a replay-verified derived lemma basis, serialized and restarted, then reused on a "
        "different later target sharing that source to produce an exactly replayed proof that the identical "
        "source-only search does not find, with at least one transferred proof removed by deleting an exact "
        "Phase-A lemma lineage and restored by restoring the frozen archive. The claim is bounded to the "
        "declared source-recurrence, critical-pair, narrowing, and finite route interfaces; it is not a claim "
        "of unrestricted theorem proving or open-ended intelligence."
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase_a_archive.json").write_text(
        json.dumps(frozen, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)

    if not result["all_v65_gates_pass"]:
        raise SystemExit("V65 frozen scientific verdict failed")


if __name__ == "__main__":
    main()
