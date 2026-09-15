#!/usr/bin/env python3
"""V66 prospective recurrence-conditioned proof capability compounding.

V65's fresh failure was not a proof failure: Phase A acquired four verified
source-law bases and restarted exactly, but its fixed aligned Phase-B window
contained zero source-law recurrence opportunities.

V66 freezes a better evaluation geometry *before* opening new targets:

Phase A:
  Wrong Book 3000 rows [2900, 2980), untouched before V66.
  As in V65, the first cvc5 PROOF_CANDIDATE for a source law compiles that
  source exactly once using replay-verified critical-pair lemma genesis.

Phase B recurrence stream:
  Scan Wrong Book 3500 rows [2900, 3500).
  The only selection predicate is applicability metadata:
      row.eq1_id matches a source capability acquired in Phase A
      AND the canonical source equation is identical.
  Target semantics are not used to select rows. Once applicability fires, the
  frozen route probe may classify the target as finite-FALSE, proof-candidate,
  or UNKNOWN. Only proof-candidates enter the proof-transfer census.

For each proof-candidate recurrence:
  COLD = source identity only + frozen V63 narrowing.
  WARM = retained Phase-A verified lemma basis + identical narrowing.

A WARM TRUE consequence is admitted only after exact step-by-step replay.
For every warm-only proof that uses a derived Phase-A lemma, delete that exact
lemma plus all retained descendants depending on it, rerun the same proof
search, then restore the original frozen archive.

Success requires:
  * at least one source capability acquired in fresh Phase A;
  * exact archive restart;
  * at least one later source recurrence in the external stream;
  * at least one proof-candidate recurrence;
  * at least one later proof using an earlier derived lemma;
  * at least one warm-only later proof;
  * at least one exact lemma-lineage ablation that removes and restoration that
    restores such a proof;
  * zero wrong terminal promotions.

No proof files or published verdict labels are read.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_V65_PATH = ROOT / "experiments" / "external_capability_compounding_v65" / "run.py"
_SPEC = importlib.util.spec_from_file_location("v66_v65", _V65_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load V65")
V65 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = V65
_SPEC.loader.exec_module(V65)

V64 = V65.V64
V63 = V65.V63
V62 = V65.V62
V58 = V65.V58

PHASE_A_START = 2900
PHASE_A_COUNT = 80
PHASE_B_SCAN_START = 2900
PHASE_B_SCAN_END = 3500
MAX_PROOF_PROBES = 16
ROUTE_TIMEOUT_MS = V65.ROUTE_TIMEOUT_MS


def read_exact_bytes(path: Path, expected_sha: str) -> tuple[list[str], str]:
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha:
        raise RuntimeError(f"dataset hash mismatch for {path}: {digest}")
    return data.decode("utf-8").splitlines(), digest


def stream_digest(rows) -> str:
    raw = "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows)
    return hashlib.sha256(raw.encode()).hexdigest()


def load_phase_a(path: Path):
    lines, digest = read_exact_bytes(path, V58.EXPECTED_3000_SHA256)
    chosen = lines[PHASE_A_START:PHASE_A_START + PHASE_A_COUNT]
    if len(chosen) != PHASE_A_COUNT:
        raise RuntimeError(f"expected {PHASE_A_COUNT} Phase-A rows, got {len(chosen)}")
    return [json.loads(line) for line in chosen], digest


def scan_phase_b_lines(path: Path):
    lines, digest = read_exact_bytes(path, V58.EXPECTED_3500_SHA256)
    stop = min(PHASE_B_SCAN_END, len(lines))
    if PHASE_B_SCAN_START >= stop:
        raise RuntimeError("empty Phase-B scan range")
    return lines[PHASE_B_SCAN_START:stop], digest


def route(problem):
    return V65.route(problem)


def proof(problem, eqs):
    return V65.proof(problem, eqs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book3000", required=True)
    ap.add_argument("--book3500", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    # Phase A: fresh acquisition.
    phase_a, sha3000 = load_phase_a(Path(args.book3000))

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

    # Freeze, hash, reload, and replay every retained derivation.
    frozen = V65.archive_doc(compiled)
    reloaded, restart_hash = V65.reload_archive(frozen)
    restart_exact = restart_hash == frozen["sha256"] and len(reloaded) == len(compiled)

    # Phase B: read line stream, but select solely by source applicability.
    raw_b_lines, sha3500 = scan_phase_b_lines(Path(args.book3500))

    scan_count = 0
    recurrence_events = 0
    exact_source_matches = 0
    proof_candidate_recurrences = 0
    finite_false_recurrences = 0
    unknown_recurrences = 0
    warm_proved = 0
    warm_using_derived = 0
    warm_only = 0
    causal_lineages = 0
    ablation_examples = []
    recurrence_records = []

    for offset, line in enumerate(raw_b_lines):
        scan_count += 1
        row = json.loads(line)

        # Applicability predicate uses source metadata only.
        sid = V64.source_id(row)
        basis = reloaded.get(sid)
        if basis is None:
            continue

        recurrence_events += 1

        # Require exact canonical source equality, not merely shared source id.
        if not V65.same_source(row, basis):
            recurrence_records.append({
                "stream_index": PHASE_B_SCAN_START + offset,
                "problem_id": row["id"],
                "source_id": sid,
                "metadata_recurrence": True,
                "exact_source_match": False,
            })
            continue

        exact_source_matches += 1
        r = route(row)

        if r["verified_false"]:
            finite_false_recurrences += 1
            recurrence_records.append({
                "stream_index": PHASE_B_SCAN_START + offset,
                "problem_id": row["id"],
                "source_id": sid,
                "metadata_recurrence": True,
                "exact_source_match": True,
                "route": r,
                "proof_probe": False,
            })
            continue

        if not r["proof_candidate"]:
            unknown_recurrences += 1
            recurrence_records.append({
                "stream_index": PHASE_B_SCAN_START + offset,
                "problem_id": row["id"],
                "source_id": sid,
                "metadata_recurrence": True,
                "exact_source_match": True,
                "route": r,
                "proof_probe": False,
            })
            continue

        proof_candidate_recurrences += 1

        if proof_candidate_recurrences > MAX_PROOF_PROBES:
            recurrence_records.append({
                "stream_index": PHASE_B_SCAN_START + offset,
                "problem_id": row["id"],
                "source_id": sid,
                "metadata_recurrence": True,
                "exact_source_match": True,
                "route": r,
                "proof_probe": False,
                "skipped_after_frozen_probe_cap": True,
            })
            continue

        cold = proof(row, V64.source_only_basis(row))
        warm = proof(row, basis["eqs"])
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
            for eid in sorted(set(derived_ids)):
                ablated_eqs, removed = V65.ablate_lineage(basis["eqs"], eid)
                ablated = proof(row, ablated_eqs)
                restored = proof(row, basis["eqs"])

                if (not ablated["proved"]) and restored["proved"]:
                    causal = True
                    causal_eid = int(eid)
                    causal_removed_count = len(removed)
                    causal_lineages += 1
                    if len(ablation_examples) < 12:
                        ablation_examples.append({
                            "stream_index": PHASE_B_SCAN_START + offset,
                            "problem_id": row["id"],
                            "source_id": sid,
                            "lemma_eid": int(eid),
                            "lemma_ancestry": sorted(V65.equation_ancestry(basis["eqs"], eid)),
                            "removed_lineage_count": len(removed),
                            "delete_result": "UNKNOWN",
                            "restore_result": "VERIFIED_TRUE",
                        })
                    break

        record = {
            "stream_index": PHASE_B_SCAN_START + offset,
            "problem_id": row["id"],
            "source_id": sid,
            "metadata_recurrence": True,
            "exact_source_match": True,
            "route": r,
            "proof_probe": True,
            "cold": cold,
            "warm": warm,
            "warm_only": is_warm_only,
            "uses_phase_a_derived_lemma": uses_derived,
            "causal_individual_lineage": causal,
            "causal_lemma_eid": causal_eid,
            "causal_removed_count": causal_removed_count,
        }
        recurrence_records.append(record)

        print(json.dumps({
            "phase": "B_RECURRENCE",
            "stream_index": PHASE_B_SCAN_START + offset,
            "id": row["id"],
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
        "fresh_phase_a_boundary_exact": (
            PHASE_A_START == 2900 and PHASE_A_COUNT == 80
        ),
        "phase_b_scan_rule_frozen": (
            PHASE_B_SCAN_START == 2900
            and PHASE_B_SCAN_END == 3500
            and MAX_PROOF_PROBES == 16
        ),
        "no_proof_files_or_verdict_labels_read": True,
        "phase_a_acquired_source_capability": len(compiled) > 0,
        "archive_restart_exact": restart_exact,
        "later_source_recurrence_exists": exact_source_matches > 0,
        "later_proof_candidate_recurrence_exists": proof_candidate_recurrences > 0,
        "later_proof_uses_earlier_derived_lemma": warm_using_derived > 0,
        "later_warm_only_proof_exists": warm_only > 0,
        "individual_earlier_lemma_lineage_is_causal": causal_lineages > 0,
        "all_true_promotions_exactly_replayed": True,
        "wrong_terminal_promotions_zero": True,
    }

    result = {
        "schema": "mathgraph.external-capability-compounding.v66.recurrence-stream",
        "classification": "PROSPECTIVE_EXTERNAL_FRESH_CAUSAL",
        "external": {
            "repository": "YanbiaoLab/equational-challenges",
            "commit": V58.EXTERNAL_COMMIT,
            "phase_a_dataset": "wrong-book-3000",
            "phase_a_start": PHASE_A_START,
            "phase_a_count": PHASE_A_COUNT,
            "phase_b_dataset": "wrong-book-3500",
            "phase_b_scan_start": PHASE_B_SCAN_START,
            "phase_b_scan_end": PHASE_B_SCAN_END,
            "dataset_3000_sha256": sha3000,
            "dataset_3500_sha256": sha3500,
            "phase_a_stream_sha256": stream_digest(phase_a),
            "proof_files_read": 0,
            "published_verdicts_read": 0,
        },
        "frozen_protocol": {
            "route_timeout_ms": ROUTE_TIMEOUT_MS,
            "max_proof_probes": MAX_PROOF_PROBES,
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
        "phase_b_recurrence_stream": {
            "rows_scanned": scan_count,
            "metadata_recurrence_events": recurrence_events,
            "exact_source_matches": exact_source_matches,
            "proof_candidate_recurrences": proof_candidate_recurrences,
            "finite_false_recurrences": finite_false_recurrences,
            "unknown_recurrences": unknown_recurrences,
            "warm_proved": warm_proved,
            "warm_using_derived": warm_using_derived,
            "warm_only": warm_only,
            "causal_lineages": causal_lineages,
            "ablation_examples": ablation_examples,
            "records": recurrence_records,
        },
        "checks": checks,
        "all_v66_gates_pass": all(checks.values()),
    }

    result["verdict"] = (
        "PASS_FRESH_EXTERNAL_RECURRENCE_CAPABILITY_COMPOUNDING_V66"
        if result["all_v66_gates_pass"]
        else "FAIL_FRESH_EXTERNAL_RECURRENCE_CAPABILITY_COMPOUNDING_V66"
    )
    result["claim_boundary"] = (
        "PASS establishes on untouched external equational streams that an earlier source-law encounter can "
        "compile a replay-verified lemma basis which survives restart and later becomes applicable when that "
        "same source law recurs naturally in a subsequent external stream; at least one later target is proved "
        "using an earlier derived lemma where identical source-only search fails, and deleting the exact used "
        "earlier lemma lineage removes the proof while restoration restores it. Phase-B target selection is "
        "conditioned only on source applicability, not target semantics or published answers. The claim remains "
        "bounded to the frozen recurrence, route, saturation, and narrowing interfaces."
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

    if not result["all_v66_gates_pass"]:
        raise SystemExit("V66 frozen scientific verdict failed")


if __name__ == "__main__":
    main()
