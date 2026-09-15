#!/usr/bin/env python3
"""V56 opened-data diagnostic: exact finite-model construction.

This script is deliberately NOT fresh evidence. It uses only the 256 external
rows already opened by V55 (rows 2500:2628 of each frozen corpus) to answer one
engineering question:

    can a generic exact finite-model constructor reach any external capability
    that V55's bounded table grammar could not?

No published verdicts or proof files are read. A synthesized table is accepted
only if MathGraph's independent finite checker verifies that the source identity
holds globally and the target identity is violated.

The output is diagnostic input for a later prospectively frozen V56 test on
untouched rows >= 2628.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Sequence

from z3 import Array, Int, IntSort, Select, Solver, sat, unknown

EXPECTED_3000_SHA256 = "fb1606578ceafcd1019d96733db4c418596f9884952237e72af2579c382ef1f7"
EXPECTED_3500_SHA256 = "fca0ccfdb31fd2eae5f6669586309130ccb9e591f19a5142aa6604e81f7023f8"
EXTERNAL_COMMIT = "bed33e36c33fca139d902addd8cb77cd4172fe64"
OPEN_START = 2500
OPEN_COUNT = 128

# Load the stdlib-only finite verifier without executing package-wide imports.
_FMW_PATH = Path(__file__).resolve().parents[2] / "mathgraph" / "finite_magma_world.py"
_SPEC = importlib.util.spec_from_file_location("v56_finite_magma_world", _FMW_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load finite magma verifier from {_FMW_PATH}")
_FMW = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _FMW
_SPEC.loader.exec_module(_FMW)


def normalize_eq(text: str) -> str:
    out = str(text)
    for op in ("◇", "⋄", "·", "∙", "∗", "＊", "×"):
        out = out.replace(op, "*")
    return out


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def table_digest(table: Sequence[Sequence[int]]) -> str:
    raw = json.dumps([list(row) for row in _FMW.normalize_table(table)], separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def load_slice(path: Path, expected_sha: str) -> tuple[list[dict], str]:
    data = path.read_bytes()
    digest = sha256_bytes(data)
    if digest != expected_sha:
        raise RuntimeError(f"dataset hash mismatch: {path}: {digest} != {expected_sha}")
    rows = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
    selected = rows[OPEN_START:OPEN_START + OPEN_COUNT]
    if len(selected) != OPEN_COUNT:
        raise RuntimeError(f"expected {OPEN_COUNT} opened rows, got {len(selected)}")
    return selected, digest


def eval_symbolic(term, op, n: int, env: dict[str, object]):
    if term.name is not None:
        return env[term.name]
    return Select(op, eval_symbolic(term.left, op, n, env) * n + eval_symbolic(term.right, op, n, env))


def all_envs(names: Sequence[str], n: int):
    names = tuple(names)
    for vals in itertools.product(range(n), repeat=len(names)):
        yield dict(zip(names, vals))


def independently_verified(problem: dict, table: Sequence[Sequence[int]]) -> bool:
    result = _FMW.check_finite_countermodel(
        normalize_eq(problem["equation1"]),
        normalize_eq(problem["equation2"]),
        table,
    )
    return bool(result.terminal_candidate_ok)


@dataclass
class ExactAttempt:
    problem_id: str
    n: int
    status: str
    elapsed_ms: int
    source_assignments: int
    verified: bool
    table_sha256: str | None


@dataclass
class Capability:
    cid: str
    table: tuple[tuple[int, ...], ...]
    acquired_problem: str
    acquired_phase: str
    n: int
    reuse_hits: int = 0

    def to_json(self):
        row = asdict(self)
        row["table"] = [list(r) for r in self.table]
        return row


def exact_model(problem: dict, n: int, timeout_ms: int) -> tuple[tuple[tuple[int, ...], ...] | None, ExactAttempt]:
    source = _FMW.parse_equation(normalize_eq(problem["equation1"]))
    target = _FMW.parse_equation(normalize_eq(problem["equation2"]))

    op = Array(f"op_{problem['id']}_{n}", IntSort(), IntSort())
    s = Solver()
    s.set(timeout=timeout_ms)

    for idx in range(n * n):
        cell = Select(op, idx)
        s.add(cell >= 0, cell < n)

    source_vars = tuple(sorted(source.variables()))
    source_count = n ** len(source_vars)
    for env in all_envs(source_vars, n):
        s.add(eval_symbolic(source.lhs, op, n, env) == eval_symbolic(source.rhs, op, n, env))

    # Existential target witness remains symbolic.
    target_vars = tuple(sorted(target.variables()))
    witness = {name: Int(f"w_{problem['id']}_{n}_{name}") for name in target_vars}
    for value in witness.values():
        s.add(value >= 0, value < n)
    s.add(eval_symbolic(target.lhs, op, n, witness) != eval_symbolic(target.rhs, op, n, witness))

    started = time.monotonic()
    status = s.check()
    elapsed_ms = int(round((time.monotonic() - started) * 1000))

    if status == sat:
        m = s.model()
        table = tuple(
            tuple(int(m.eval(Select(op, i * n + j), model_completion=True).as_long()) for j in range(n))
            for i in range(n)
        )
        verified = independently_verified(problem, table)
        if not verified:
            raise RuntimeError(f"independent verifier rejected SAT model for {problem['id']} n={n}")
        return table, ExactAttempt(problem["id"], n, "sat", elapsed_ms, source_count, True, table_digest(table))

    label = "unknown" if status == unknown else "unsat"
    return None, ExactAttempt(problem["id"], n, label, elapsed_ms, source_count, False, None)


def try_archive(problem: dict, archive: list[Capability]) -> Capability | None:
    # Reuse order is deterministic and consequence-driven: most prior verified
    # reuse first, then acquisition order.
    ordered = sorted(enumerate(archive), key=lambda x: (-x[1].reuse_hits, x[0], x[1].cid))
    for _, cap in ordered:
        if independently_verified(problem, cap.table):
            cap.reuse_hits += 1
            return cap
    return None


def install(archive: list[Capability], table, problem_id: str, phase: str) -> Capability:
    cid = table_digest(table)
    for cap in archive:
        if cap.cid == cid:
            return cap
    cap = Capability(cid, _FMW.normalize_table(table), problem_id, phase, len(table), 0)
    archive.append(cap)
    return cap


def develop(problem: dict, phase: str, archive: list[Capability], max_n: int, timeout_ms: int):
    reused = try_archive(problem, archive)
    if reused is not None:
        return {
            "problem_id": problem["id"],
            "phase": phase,
            "terminal": "FALSE",
            "route": "REUSE",
            "cid": reused.cid,
            "n": reused.n,
            "attempts": [],
        }

    attempts = []
    for n in range(2, max_n + 1):
        table, attempt = exact_model(problem, n, timeout_ms)
        attempts.append(asdict(attempt))
        if table is not None:
            cap = install(archive, table, problem["id"], phase)
            return {
                "problem_id": problem["id"],
                "phase": phase,
                "terminal": "FALSE",
                "route": "EXACT_ACQUIRE",
                "cid": cap.cid,
                "n": cap.n,
                "attempts": attempts,
            }

    return {
        "problem_id": problem["id"],
        "phase": phase,
        "terminal": "UNKNOWN",
        "route": "UNKNOWN",
        "cid": None,
        "n": None,
        "attempts": attempts,
    }


def archive_payload(archive: list[Capability]) -> dict:
    rows = [c.to_json() for c in archive]
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "capabilities": rows}


def run(path_a: Path, path_b: Path, out: Path, max_n: int, timeout_ms: int):
    phase_a, sha_a = load_slice(path_a, EXPECTED_3000_SHA256)
    phase_b, sha_b = load_slice(path_b, EXPECTED_3500_SHA256)

    if {r["id"] for r in phase_a} & {r["id"] for r in phase_b}:
        raise RuntimeError("opened extension slices unexpectedly overlap")

    archive: list[Capability] = []
    rows_a = []
    for problem in phase_a:
        rows_a.append(develop(problem, "OPENED_A", archive, max_n, timeout_ms))

    frozen_a = archive_payload(archive)
    frozen_caps = [
        Capability(
            row["cid"],
            _FMW.normalize_table(row["table"]),
            row["acquired_problem"],
            row["acquired_phase"],
            int(row["n"]),
            int(row.get("reuse_hits", 0)),
        )
        for row in frozen_a["capabilities"]
    ]
    restart = archive_payload(frozen_caps)
    restart_exact = restart["sha256"] == frozen_a["sha256"]

    transfer = []
    for problem in phase_b:
        hit = try_archive(problem, frozen_caps)
        if hit is not None:
            transfer.append({"problem_id": problem["id"], "cid": hit.cid, "n": hit.n})

    # Continue through B from the restarted A archive after the zero-acquisition probe.
    archive = frozen_caps
    rows_b = []
    for problem in phase_b:
        rows_b.append(develop(problem, "OPENED_B", archive, max_n, timeout_ms))

    all_rows = rows_a + rows_b
    exact_rows = [attempt for row in all_rows for attempt in row["attempts"]]
    status_counts = {}
    n_sat_counts = {}
    for row in exact_rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
        if row["status"] == "sat":
            n_sat_counts[str(row["n"])] = n_sat_counts.get(str(row["n"]), 0) + 1

    result = {
        "schema": "mathgraph.external-capability-compounding.v56.opened-diagnostic",
        "classification": "OPENED_DATA_DIAGNOSTIC_NOT_FRESH_EVIDENCE",
        "external_commit": EXTERNAL_COMMIT,
        "proof_files_read": 0,
        "published_verdicts_read": 0,
        "dataset_hashes": {"3000": sha_a, "3500": sha_b},
        "opened_rows": {"start": OPEN_START, "count_each": OPEN_COUNT, "total": 2 * OPEN_COUNT},
        "constructor": {"kind": "exact_finite_model_z3", "max_n": max_n, "timeout_ms_per_n": timeout_ms},
        "phase_a": {
            "verified_false": sum(r["terminal"] == "FALSE" for r in rows_a),
            "exact_acquisitions": sum(r["route"] == "EXACT_ACQUIRE" for r in rows_a),
            "reuse_hits": sum(r["route"] == "REUSE" for r in rows_a),
            "archive_count": len(frozen_a["capabilities"]),
            "archive_sha256": frozen_a["sha256"],
            "restart_exact": restart_exact,
        },
        "cross_extension_probe": {
            "phase_a_capabilities_solving_opened_b_before_b_acquisition": len(transfer),
            "examples": transfer[:20],
        },
        "phase_b": {
            "verified_false": sum(r["terminal"] == "FALSE" for r in rows_b),
            "exact_acquisitions": sum(r["route"] == "EXACT_ACQUIRE" for r in rows_b),
            "reuse_hits": sum(r["route"] == "REUSE" for r in rows_b),
        },
        "exact_attempts": {
            "count": len(exact_rows),
            "status_counts": status_counts,
            "sat_by_n": n_sat_counts,
            "elapsed_ms_total": sum(r["elapsed_ms"] for r in exact_rows),
        },
        "final_archive_count": len(archive),
        "diagnostic_conclusion": (
            "SMALL_FINITE_CAPABILITY_REACHABLE"
            if frozen_a["capabilities"] or any(r["route"] == "EXACT_ACQUIRE" for r in rows_b)
            else "NO_SMALL_FINITE_CAPABILITY_REACHED"
        ),
    }

    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    (out / "opened_a.json").write_text(json.dumps(rows_a, indent=2), encoding="utf-8")
    (out / "opened_b.json").write_text(json.dumps(rows_b, indent=2), encoding="utf-8")
    (out / "phase_a_archive.json").write_text(json.dumps(frozen_a, indent=2, sort_keys=True), encoding="utf-8")
    (out / "final_archive.json").write_text(json.dumps(archive_payload(archive), indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wrong-book-3000", required=True)
    ap.add_argument("--wrong-book-3500", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-n", type=int, default=4)
    ap.add_argument("--timeout-ms", type=int, default=1500)
    args = ap.parse_args()
    run(Path(args.wrong_book_3000), Path(args.wrong_book_3500), Path(args.out), args.max_n, args.timeout_ms)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
