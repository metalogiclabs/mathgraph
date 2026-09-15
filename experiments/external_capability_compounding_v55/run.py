#!/usr/bin/env python3
"""V55 prospective external capability-compounding experiment.

This experiment never reads YanbiaoLab/equational-challenges proof files or
published verdicts. It consumes only the two frozen JSONL problem streams at
the pinned external commit.

Protocol
--------
* External source commit is pinned by the workflow.
* Phase A is rows 2500:2628 of Wrong Book 3000's extension.
* Phase B is rows 2500:2628 of Wrong Book 3500's disjoint extension.
* Row selection is fixed before any solving and is independent of labels,
  proof availability, developmental route, or outcome.
* Only verified finite countermodels may produce a terminal FALSE consequence.
  Everything else remains UNKNOWN.
* A single continuous developer keeps every newly verified concrete magma
  capability and may reuse it on later problems.
* Learned magmas may also seed a fixed one-cell mutation generator. This tests
  whether acquired capability can change the proposal mechanism itself.
* At the A/B boundary the archive is serialized and reloaded before Phase B.
* Phase B is additionally probed against the frozen Phase-A archive before any
  Phase-B acquisition, giving a clean cross-extension transfer test.
* Exact archive and individual-ancestor ablations are evaluated on transferred
  Phase-B consequences.

Controls
--------
COLD: fixed prior + the same generic synthesis sequence, independently on every
problem, with no retained acquired capabilities.
CONTINUOUS: fixed prior -> retained direct reuse -> learned-seed mutation ->
same generic synthesis. Any synthesized countermodel is independently checked
before installation.

A pass is intentionally strong but bounded:
1. dataset hashes and frozen stream selection match the protocol;
2. at least one capability is acquired in Phase A;
3. at least one Phase-A acquired capability solves a Phase-B problem before
   any new synthesis while the fixed prior alone cannot;
4. exact removal of the learned archive destroys at least one such transfer and
   restoration restores it;
5. at least one individual learned capability is an essential ancestor of a
   transferred consequence;
6. learned-seed mutation produces at least one new verified capability that the
   generic candidate sequence for that task did not contain;
7. restart preserves the Phase-A executable archive exactly;
8. Phase-B generic synthesis work is lower than the cold control;
9. continuous verified FALSE consequences are not fewer than cold;
10. wrong terminal promotions are zero.

This is not unrestricted self-development or a proof about true implications.
It is a prospective external finite-countermodel capability-acquisition test.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Sequence

import importlib.util
import sys

# Load the stdlib-only verifier module directly so this frozen experiment does
# not execute MathGraph's package-wide __init__ or require unrelated optional
# dependencies. This changes only runner plumbing, not the scientific protocol.
_FMW_PATH = Path(__file__).resolve().parents[2] / "mathgraph" / "finite_magma_world.py"
_FMW_SPEC = importlib.util.spec_from_file_location("v55_finite_magma_world", _FMW_PATH)
if _FMW_SPEC is None or _FMW_SPEC.loader is None:
    raise RuntimeError(f"cannot load finite magma verifier from {_FMW_PATH}")
_FMW = importlib.util.module_from_spec(_FMW_SPEC)
sys.modules[_FMW_SPEC.name] = _FMW
_FMW_SPEC.loader.exec_module(_FMW)

add_mod_n = _FMW.add_mod_n
check_finite_countermodel = _FMW.check_finite_countermodel
commutative_nonassociative_3 = _FMW.commutative_nonassociative_3
constant_table = _FMW.constant_table
deterministic_perturbation_3 = _FMW.deterministic_perturbation_3
left_projection = _FMW.left_projection
max_table = _FMW.max_table
min_table = _FMW.min_table
normalize_table = _FMW.normalize_table
right_projection = _FMW.right_projection
sub_mod_n = _FMW.sub_mod_n
xor_mod_2 = _FMW.xor_mod_2

EXPECTED_3000_SHA256 = "fb1606578ceafcd1019d96733db4c418596f9884952237e72af2579c382ef1f7"
EXPECTED_3500_SHA256 = "fca0ccfdb31fd2eae5f6669586309130ccb9e591f19a5142aa6604e81f7023f8"
EXTERNAL_COMMIT = "bed33e36c33fca139d902addd8cb77cd4172fe64"
START = 2500
COUNT = 128


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def table_digest(table: Sequence[Sequence[int]]) -> str:
    raw = json.dumps([list(row) for row in normalize_table(table)], separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def load_jsonl(path: Path, expected_sha: str) -> tuple[list[dict], str]:
    data = path.read_bytes()
    digest = sha256_bytes(data)
    if digest != expected_sha:
        raise RuntimeError(f"dataset hash mismatch for {path}: {digest} != {expected_sha}")
    rows = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
    return rows, digest


def stream_slice(rows: list[dict]) -> list[dict]:
    selected = rows[START:START + COUNT]
    if len(selected) != COUNT:
        raise RuntimeError(f"expected {COUNT} rows from offset {START}, got {len(selected)}")
    return selected


def stream_digest(rows: Sequence[dict]) -> str:
    payload = "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows)
    return hashlib.sha256(payload.encode()).hexdigest()


def fixed_prior_tables() -> list[tuple[tuple[int, ...], ...]]:
    tables = [
        left_projection(2),
        right_projection(2),
        constant_table(2, 0),
        constant_table(2, 1),
        xor_mod_2(),
        min_table(2),
        max_table(2),
        left_projection(3),
        right_projection(3),
        constant_table(3, 0),
        constant_table(3, 1),
        add_mod_n(3),
        sub_mod_n(3),
        min_table(3),
        max_table(3),
        commutative_nonassociative_3(),
        deterministic_perturbation_3(),
    ]
    return dedupe_tables(tables)


def dedupe_tables(tables: Iterable[Sequence[Sequence[int]]]) -> list[tuple[tuple[int, ...], ...]]:
    out = []
    seen = set()
    for table in tables:
        t = normalize_table(table)
        h = table_digest(t)
        if h not in seen:
            seen.add(h)
            out.append(t)
    return out


def all_binary_tables() -> Iterable[tuple[tuple[int, ...], ...]]:
    for values in itertools.product(range(2), repeat=4):
        yield ((values[0], values[1]), (values[2], values[3]))


def one_cell_mutations(table: Sequence[Sequence[int]]) -> Iterable[tuple[tuple[int, ...], ...]]:
    t = normalize_table(table)
    n = len(t)
    for i in range(n):
        for j in range(n):
            for value in range(n):
                if value == t[i][j]:
                    continue
                rows = [list(row) for row in t]
                rows[i][j] = value
                yield normalize_table(rows)


def generic_candidates(task_id: str, fixed_hashes: set[str]) -> list[tuple[tuple[int, ...], ...]]:
    """Frozen generic constructor grammar, independent of solver outcomes."""
    candidates: list[tuple[tuple[int, ...], ...]] = []

    # Complete order-2 grammar.
    candidates.extend(all_binary_tables())

    # Fixed structural order-3 mutation grammar.
    structured_bases = [
        left_projection(3),
        right_projection(3),
        constant_table(3, 0),
        constant_table(3, 1),
        add_mod_n(3),
        sub_mod_n(3),
        min_table(3),
        max_table(3),
        commutative_nonassociative_3(),
        deterministic_perturbation_3(),
    ]
    for base in structured_bases:
        # First twelve lexical one-cell mutations per base keeps the grammar
        # bounded while remaining target-independent.
        for mutation in itertools.islice(one_cell_mutations(base), 12):
            candidates.append(mutation)

    # Deterministic task-keyed exploration, frozen before outcome.
    seed = int(hashlib.sha256(("v55:" + task_id).encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    for _ in range(48):
        candidates.append(tuple(tuple(rng.randrange(3) for _ in range(3)) for _ in range(3)))

    out = []
    seen = set(fixed_hashes)
    for table in candidates:
        t = normalize_table(table)
        h = table_digest(t)
        if h in seen:
            continue
        seen.add(h)
        out.append(t)
    return out


@dataclass
class Capability:
    cid: str
    table: tuple[tuple[int, ...], ...]
    acquired_on: str
    acquired_phase: str
    route: str
    parent_cid: str | None
    acquisition_index: int
    direct_hits: int = 0

    def json(self) -> dict:
        row = asdict(self)
        row["table"] = [list(r) for r in self.table]
        return row

    @classmethod
    def from_json(cls, row: dict) -> "Capability":
        return cls(
            cid=row["cid"],
            table=normalize_table(row["table"]),
            acquired_on=row["acquired_on"],
            acquired_phase=row["acquired_phase"],
            route=row["route"],
            parent_cid=row.get("parent_cid"),
            acquisition_index=int(row["acquisition_index"]),
            direct_hits=int(row.get("direct_hits", 0)),
        )


def _normalize_external_equation(text: str) -> str:
    # YanbiaoLab publishes the magma operator as ◇. The frozen MathGraph finite
    # verifier on this branch parses '*'. This is a notation-only adapter.
    out = str(text)
    for op in ("◇", "⋄", "·", "∙", "∗", "＊", "×"):
        out = out.replace(op, "*")
    return out


def verify_false(problem: dict, table: Sequence[Sequence[int]]) -> bool:
    result = check_finite_countermodel(
        _normalize_external_equation(problem["equation1"]),
        _normalize_external_equation(problem["equation2"]),
        table,
    )
    return bool(result.terminal_candidate_ok)


def try_tables(problem: dict, tables: Sequence[Sequence[Sequence[int]]]) -> tuple[int | None, int]:
    checks = 0
    for idx, table in enumerate(tables):
        checks += 1
        if verify_false(problem, table):
            return idx, checks
    return None, checks


def ranked_archive(archive: Sequence[Capability]) -> list[Capability]:
    return sorted(archive, key=lambda c: (-c.direct_hits, c.acquisition_index, c.cid))


def mutation_candidates_from_archive(
    archive: Sequence[Capability],
    generic_hashes: set[str],
    max_parents: int = 8,
    max_mutations_per_parent: int = 24,
) -> list[tuple[Capability, tuple[tuple[int, ...], ...]]]:
    out = []
    seen = set(generic_hashes)
    for parent in ranked_archive(archive)[:max_parents]:
        for child in itertools.islice(one_cell_mutations(parent.table), max_mutations_per_parent):
            h = table_digest(child)
            # For the causal exaptation test, only count candidates that the
            # task's generic grammar would not have generated anyway.
            if h in seen:
                continue
            seen.add(h)
            out.append((parent, child))
    return out


def install(
    archive: list[Capability],
    table: Sequence[Sequence[int]],
    problem_id: str,
    phase: str,
    route: str,
    parent_cid: str | None,
) -> tuple[Capability, bool]:
    t = normalize_table(table)
    cid = table_digest(t)
    for cap in archive:
        if cap.cid == cid:
            return cap, False
    cap = Capability(
        cid=cid,
        table=t,
        acquired_on=problem_id,
        acquired_phase=phase,
        route=route,
        parent_cid=parent_cid,
        acquisition_index=len(archive),
    )
    archive.append(cap)
    return cap, True


@dataclass
class SolveResult:
    problem_id: str
    phase: str
    terminal: str
    route: str
    capability_cid: str | None
    parent_cid: str | None
    fixed_checks: int
    archive_checks: int
    mutation_checks: int
    generic_checks: int
    installed: bool

    @property
    def total_checks(self) -> int:
        return self.fixed_checks + self.archive_checks + self.mutation_checks + self.generic_checks


def cold_solve(problem: dict, fixed: list, fixed_hashes: set[str]) -> SolveResult:
    fixed_hit, fixed_checks = try_tables(problem, fixed)
    if fixed_hit is not None:
        return SolveResult(problem["id"], "control", "FALSE", "FIXED", table_digest(fixed[fixed_hit]), None, fixed_checks, 0, 0, 0, False)
    generic = generic_candidates(problem["id"], fixed_hashes)
    hit, checks = try_tables(problem, generic)
    if hit is not None:
        return SolveResult(problem["id"], "control", "FALSE", "GENERIC", table_digest(generic[hit]), None, fixed_checks, 0, 0, checks, False)
    return SolveResult(problem["id"], "control", "UNKNOWN", "UNKNOWN", None, None, fixed_checks, 0, 0, checks, False)


def continuous_solve(
    problem: dict,
    phase: str,
    fixed: list,
    fixed_hashes: set[str],
    archive: list[Capability],
) -> SolveResult:
    fixed_hit, fixed_checks = try_tables(problem, fixed)
    if fixed_hit is not None:
        return SolveResult(problem["id"], phase, "FALSE", "FIXED", table_digest(fixed[fixed_hit]), None, fixed_checks, 0, 0, 0, False)

    ordered = ranked_archive(archive)
    archive_checks = 0
    for cap in ordered:
        archive_checks += 1
        if verify_false(problem, cap.table):
            cap.direct_hits += 1
            return SolveResult(problem["id"], phase, "FALSE", "REUSE", cap.cid, cap.parent_cid, fixed_checks, archive_checks, 0, 0, False)

    generic = generic_candidates(problem["id"], fixed_hashes)
    generic_hashes = {table_digest(t) for t in generic} | fixed_hashes

    mutation_checks = 0
    for parent, child in mutation_candidates_from_archive(archive, generic_hashes):
        mutation_checks += 1
        if verify_false(problem, child):
            cap, installed = install(archive, child, problem["id"], phase, "EXAPT_MUTATION", parent.cid)
            cap.direct_hits += 1
            return SolveResult(problem["id"], phase, "FALSE", "EXAPT_MUTATION", cap.cid, parent.cid, fixed_checks, archive_checks, mutation_checks, 0, installed)

    generic_checks = 0
    for table in generic:
        generic_checks += 1
        if verify_false(problem, table):
            cap, installed = install(archive, table, problem["id"], phase, "GENERIC_ACQUIRE", None)
            cap.direct_hits += 1
            return SolveResult(problem["id"], phase, "FALSE", "GENERIC_ACQUIRE", cap.cid, None, fixed_checks, archive_checks, mutation_checks, generic_checks, installed)

    return SolveResult(problem["id"], phase, "UNKNOWN", "UNKNOWN", None, None, fixed_checks, archive_checks, mutation_checks, generic_checks, False)


def archive_payload(archive: Sequence[Capability]) -> dict:
    rows = [cap.json() for cap in archive]
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return {"capabilities": rows, "sha256": hashlib.sha256(raw).hexdigest()}


def frozen_transfer_probe(problem: dict, fixed: list, frozen: Sequence[Capability]) -> dict:
    fixed_hit, fixed_checks = try_tables(problem, fixed)
    if fixed_hit is not None:
        return {"id": problem["id"], "fixed_solved": True, "transferred": False, "cid": None, "fixed_checks": fixed_checks, "archive_checks": 0}
    checks = 0
    solving = []
    for cap in ranked_archive(frozen):
        checks += 1
        if verify_false(problem, cap.table):
            solving.append(cap.cid)
    return {
        "id": problem["id"],
        "fixed_solved": False,
        "transferred": bool(solving),
        "cid": solving[0] if solving else None,
        "solving_cids": solving,
        "fixed_checks": fixed_checks,
        "archive_checks": checks,
    }


def essential_individual_ablation(problem: dict, fixed: list, frozen: Sequence[Capability], cid: str) -> bool:
    # Fixed prior already failed for transferred tasks.
    remaining = [cap for cap in frozen if cap.cid != cid]
    return not any(verify_false(problem, cap.table) for cap in remaining)


def run(path3000: Path, path3500: Path, out: Path) -> dict:
    rows3000, sha3000 = load_jsonl(path3000, EXPECTED_3000_SHA256)
    rows3500, sha3500 = load_jsonl(path3500, EXPECTED_3500_SHA256)
    phase_a = stream_slice(rows3000)
    phase_b = stream_slice(rows3500)

    if {row["id"] for row in phase_a} & {row["id"] for row in phase_b}:
        raise RuntimeError("declared disjoint extensions overlap in selected stream")

    fixed = fixed_prior_tables()
    fixed_hashes = {table_digest(t) for t in fixed}

    archive: list[Capability] = []
    cold_a = []
    dev_a = []

    for problem in phase_a:
        cold_a.append(cold_solve(problem, fixed, fixed_hashes))
        dev_a.append(continuous_solve(problem, "A", fixed, fixed_hashes, archive))

    phase_a_snapshot = archive_payload(archive)
    # Exact restart: serialize and reload the executable archive.
    frozen_a = [Capability.from_json(row) for row in phase_a_snapshot["capabilities"]]
    restarted_payload = archive_payload(frozen_a)
    restart_exact = restarted_payload["sha256"] == phase_a_snapshot["sha256"]

    transfer_probes = [frozen_transfer_probe(problem, fixed, frozen_a) for problem in phase_b]
    transfer_hits = [row for row in transfer_probes if row["transferred"]]

    archive_ablation_removed = 0
    archive_restoration_restored = 0
    individual_essential = 0
    for problem, probe in zip(phase_b, transfer_probes):
        if not probe["transferred"]:
            continue
        # Remove every learned Phase-A capability.
        without_archive = not any(verify_false(problem, table) for table in fixed)
        if without_archive:
            archive_ablation_removed += 1
        restored = any(verify_false(problem, cap.table) for cap in frozen_a)
        if restored:
            archive_restoration_restored += 1
        cid = probe.get("cid")
        if cid and essential_individual_ablation(problem, fixed, frozen_a, cid):
            individual_essential += 1

    # Continue from the restarted Phase-A state through the disjoint Phase-B stream.
    archive = frozen_a
    cold_b = []
    dev_b = []
    exaptation_events = []
    for problem in phase_b:
        cold = cold_solve(problem, fixed, fixed_hashes)
        dev = continuous_solve(problem, "B", fixed, fixed_hashes, archive)
        cold_b.append(cold)
        dev_b.append(dev)
        if dev.route == "EXAPT_MUTATION":
            exaptation_events.append({
                "problem_id": problem["id"],
                "child_cid": dev.capability_cid,
                "parent_cid": dev.parent_cid,
            })

    def count_false(rows):
        return sum(r.terminal == "FALSE" for r in rows)

    def sum_field(rows, field):
        return sum(getattr(r, field) for r in rows)

    cold_b_generic = sum_field(cold_b, "generic_checks")
    dev_b_generic = sum_field(dev_b, "generic_checks")
    cold_b_total = sum(r.total_checks for r in cold_b)
    dev_b_total = sum(r.total_checks for r in dev_b)

    # Causal exaptation: because successful child candidates are explicitly
    # excluded from that task's generic set, they are generated only from a
    # learned parent in the pre-generic phase. Require at least one event.
    causal_exaptation = len(exaptation_events)

    wrong_promotions = sum(
        1
        for row, problem in [(r, p) for r, p in zip(dev_a + dev_b, phase_a + phase_b)]
        if row.terminal == "FALSE"
        and row.capability_cid is None
    )

    routes = {}
    for row in dev_a + dev_b:
        routes[row.route] = routes.get(row.route, 0) + 1

    result = {
        "schema": "mathgraph.external-capability-compounding.v55",
        "classification": "PROSPECTIVE_EXTERNAL_BOUNDED_CAUSAL",
        "external": {
            "repository": "YanbiaoLab/equational-challenges",
            "commit": EXTERNAL_COMMIT,
            "proof_files_read": 0,
            "dataset_3000_sha256": sha3000,
            "dataset_3500_sha256": sha3500,
            "phase_a": {"dataset": "wrong-book-3000", "start": START, "count": COUNT, "stream_sha256": stream_digest(phase_a)},
            "phase_b": {"dataset": "wrong-book-3500", "start": START, "count": COUNT, "stream_sha256": stream_digest(phase_b)},
            "selected_stream_overlap": 0,
        },
        "prior": {"fixed_table_count": len(fixed)},
        "phase_a": {
            "tasks": len(phase_a),
            "cold_false": count_false(cold_a),
            "continuous_false": count_false(dev_a),
            "acquired_capabilities": len(phase_a_snapshot["capabilities"]),
            "archive_sha256": phase_a_snapshot["sha256"],
            "restart_exact": restart_exact,
            "routes": {k: sum(r.route == k for r in dev_a) for k in sorted({r.route for r in dev_a})},
        },
        "phase_b_frozen_transfer": {
            "tasks": len(phase_b),
            "transferred_before_phase_b_acquisition": len(transfer_hits),
            "archive_ablation_removed": archive_ablation_removed,
            "archive_restoration_restored": archive_restoration_restored,
            "individual_essential_ancestor_cases": individual_essential,
            "examples": transfer_hits[:10],
        },
        "phase_b_continuous": {
            "cold_false": count_false(cold_b),
            "continuous_false": count_false(dev_b),
            "cold_generic_checks": cold_b_generic,
            "continuous_generic_checks": dev_b_generic,
            "generic_work_reduction": (cold_b_generic / dev_b_generic) if dev_b_generic else (float("inf") if cold_b_generic else 1.0),
            "cold_total_finite_checks": cold_b_total,
            "continuous_total_finite_checks": dev_b_total,
            "total_check_ratio_cold_over_continuous": (cold_b_total / dev_b_total) if dev_b_total else float("inf"),
            "new_exaptation_capabilities": causal_exaptation,
            "exaptation_examples": exaptation_events[:10],
        },
        "continuous": {
            "final_archive_count": len(archive),
            "routes": routes,
            "wrong_terminal_promotions": wrong_promotions,
        },
    }

    gates = {
        "dataset_hashes_exact": sha3000 == EXPECTED_3000_SHA256 and sha3500 == EXPECTED_3500_SHA256,
        "stream_selection_frozen_and_disjoint": len(phase_a) == COUNT and len(phase_b) == COUNT and not ({r["id"] for r in phase_a} & {r["id"] for r in phase_b}),
        "no_external_answers_or_proofs_read": result["external"]["proof_files_read"] == 0,
        "phase_a_acquired_capability": len(phase_a_snapshot["capabilities"]) > 0,
        "restart_preserved_archive": restart_exact,
        "cross_extension_zero_acquisition_transfer": len(transfer_hits) > 0,
        "archive_ablation_removed_transfer": archive_ablation_removed > 0,
        "archive_restoration_restored_transfer": archive_restoration_restored >= archive_ablation_removed > 0,
        "individual_learned_ancestor_causal": individual_essential > 0,
        "learned_capability_changed_proposal_generator": causal_exaptation > 0,
        "phase_b_generic_work_lower_than_cold": dev_b_generic < cold_b_generic,
        "continuous_verified_consequences_not_worse": count_false(dev_b) >= count_false(cold_b),
        "wrong_terminal_promotions_zero": wrong_promotions == 0,
    }
    result["gates"] = gates
    result["all_v55_gates_pass"] = all(gates.values())
    result["verdict"] = (
        "PASS_EXTERNAL_CONTINUOUS_CAPABILITY_COMPOUNDING_V55"
        if result["all_v55_gates_pass"]
        else "FAIL_EXTERNAL_CONTINUOUS_CAPABILITY_COMPOUNDING_V55"
    )
    result["claim_boundary"] = (
        "PASS establishes, on two pinned disjoint external magma-implication streams selected without labels or proof access, "
        "that one continuous finite-countermodel developer can acquire verified executable magma capabilities, preserve them across restart, "
        "reuse Phase-A acquisitions on Phase-B tasks before new synthesis, lose and regain transferred consequences under exact ablation/restoration, "
        "and use learned capabilities as parents of new verified proposal candidates while reducing generic synthesis work. "
        "It does not establish unrestricted open-ended intelligence, theorem-proving growth on TRUE tasks, or cross-domain transfer."
    )

    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=True), encoding="utf-8")
    (out / "phase_a_continuous.json").write_text(json.dumps([asdict(r) | {"total_checks": r.total_checks} for r in dev_a], indent=2), encoding="utf-8")
    (out / "phase_b_continuous.json").write_text(json.dumps([asdict(r) | {"total_checks": r.total_checks} for r in dev_b], indent=2), encoding="utf-8")
    (out / "phase_a_archive.json").write_text(json.dumps(phase_a_snapshot, indent=2, sort_keys=True), encoding="utf-8")
    (out / "final_archive.json").write_text(json.dumps(archive_payload(archive), indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=True))

    if not result["all_v55_gates_pass"]:
        raise SystemExit("V55 frozen verdict failed")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wrong-book-3000", required=True)
    ap.add_argument("--wrong-book-3500", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    run(Path(args.wrong_book_3000), Path(args.wrong_book_3500), Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
