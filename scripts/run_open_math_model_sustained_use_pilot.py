#!/usr/bin/env python3
"""Open Math Model x MathGraph sustained-use evaluation pilot.

Phase 0 is deliberately model-independent.  It establishes the evaluation
contract on an exact finite fixture, then optionally runs the existing
SAIR-capable MathGraph benchmark.  Model outputs and learned routing remain
advisory; only an independent verifier may authorize promotion.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


TOKENS = ("LT", "LE", "AND", "OR", "A", "B", "C", "D")


@dataclass(frozen=True)
class Capability:
    src: str
    dst: str

    def apply_unique(self, state: tuple[str, ...]) -> tuple[str, ...] | None:
        positions = [i for i, value in enumerate(state) if value == self.src]
        if len(positions) != 1:
            return None
        out = list(state)
        out[positions[0]] = self.dst
        return tuple(out)


@dataclass(frozen=True)
class Case:
    name: str
    broken: tuple[str, ...]
    target: tuple[str, ...]


def verifier(case: Case, candidate: tuple[str, ...] | None) -> bool:
    """Independent terminal checker for the bounded fixture."""
    return candidate == case.target


def literal_candidates(state: tuple[str, ...]) -> list[Capability]:
    out: list[Capability] = []
    for value in state:
        for dst in TOKENS:
            if dst != value:
                out.append(Capability(value, dst))
    return out


def apply_literal_at_first_match(cap: Capability, state: tuple[str, ...]) -> tuple[str, ...] | None:
    """Deterministic constructor used only in the fixture search."""
    return cap.apply_unique(state)


def verified_on(cap: Capability, cases: Iterable[Case]) -> bool:
    return all(verifier(case, cap.apply_unique(case.broken)) for case in cases)


def full_two_step_search(case: Case) -> tuple[int, list[tuple[Capability, Capability]]]:
    tested = 0
    wins: list[tuple[Capability, Capability]] = []
    for first in literal_candidates(case.broken):
        mid = apply_literal_at_first_match(first, case.broken)
        if mid is None:
            continue
        for second in literal_candidates(mid):
            tested += 1
            final = apply_literal_at_first_match(second, mid)
            if verifier(case, final):
                wins.append((first, second))
    return tested, wins


def one_step_audit(case: Case, state: tuple[str, ...]) -> tuple[int, list[Capability]]:
    wins: list[Capability] = []
    candidates = literal_candidates(state)
    for cap in candidates:
        if verifier(case, apply_literal_at_first_match(cap, state)):
            wins.append(cap)
    return len(candidates), wins


def run_mechanistic_fixture() -> dict:
    # O1 earns authority on source-distinct cases and an untouched position.
    train = (
        Case("source_pos0", ("LT", "A", "B", "C"), ("LE", "A", "B", "C")),
        Case("source_pos2", ("A", "B", "LT", "C"), ("A", "B", "LE", "C")),
    )
    heldout = Case("heldout_pos1", ("A", "LT", "B", "C"), ("A", "LE", "B", "C"))
    target = Case(
        "fresh_double_defect",
        ("A", "LT", "B", "AND"),
        ("A", "LE", "B", "OR"),
    )

    o1 = Capability("LT", "LE")
    sham = Capability("LT", "AND")

    authority_train = verified_on(o1, train)
    authority_heldout = verified_on(o1, (heldout,))
    promoted = authority_train and authority_heldout

    cold_cost, cold_wins = full_two_step_search(target)

    warm_start = o1.apply_unique(target.broken) if promoted else None
    warm_cost, warm_wins = one_step_audit(target, warm_start) if warm_start else (0, [])

    # Presence-only control: same object shape, wrong causal content.
    sham_start = sham.apply_unique(target.broken)
    sham_cost, sham_wins = one_step_audit(target, sham_start) if sham_start else (0, [])

    # Targeted ablation: remove O1 but keep the one-new-capability warm budget.
    ablation_cost, ablation_wins = one_step_audit(target, target.broken)

    # Restart: serialize only the authorized capability, reload it, and rerun.
    serialized = json.dumps(asdict(o1), sort_keys=True)
    restarted = Capability(**json.loads(serialized))
    restart_start = restarted.apply_unique(target.broken)
    restart_cost, restart_wins = one_step_audit(target, restart_start) if restart_start else (0, [])

    compression = cold_cost / warm_cost if warm_cost else 0.0
    reduction = 1.0 - (warm_cost / cold_cost) if cold_cost else 0.0

    gates = {
        "authority_train_pass": authority_train,
        "authority_heldout_pass": authority_heldout,
        "promotion_requires_authority": promoted,
        "cold_exhaustive_search_finds_solution": bool(cold_wins),
        "warm_reuse_finds_solution": bool(warm_wins),
        "warm_reuse_is_cheaper": 0 < warm_cost < cold_cost,
        "sham_memory_does_not_solve_under_warm_budget": not sham_wins,
        "targeted_ablation_restores_failure_under_warm_budget": not ablation_wins,
        "restart_preserves_reuse": bool(restart_wins),
        "restart_cost_matches_warm_cost": restart_cost == warm_cost,
        "cold_warm_terminal_outcome_matches": bool(cold_wins) == bool(warm_wins),
    }

    return {
        "fixture": "exact_finite_two_generation_reuse",
        "authority": {
            "candidate": asdict(o1),
            "train_cases": len(train),
            "heldout_cases": 1,
            "train_verified": authority_train,
            "heldout_verified": authority_heldout,
            "promoted": promoted,
        },
        "sustained_use": {
            "cost_unit": "candidate verifier calls",
            "cold_cost": cold_cost,
            "warm_cost": warm_cost,
            "sham_control_cost": sham_cost,
            "ablation_budget_cost": ablation_cost,
            "restart_cost": restart_cost,
            "compression_ratio": compression,
            "relative_cost_reduction": reduction,
            "cold_solution_count": len(cold_wins),
            "warm_solution_count": len(warm_wins),
            "sham_solution_count": len(sham_wins),
            "ablation_solution_count": len(ablation_wins),
            "restart_solution_count": len(restart_wins),
        },
        "gates": gates,
        "verdict": "PASS" if all(gates.values()) else "FAIL",
        "claim_boundary": (
            "Exact bounded mechanistic fixture only. It establishes authorized promotion, "
            "causal reuse, restart, a presence-only sham control, targeted ablation, and "
            "candidate-verifier-call compression. It does not establish token, wall-time, "
            "or model-quality gains on an external language model."
        ),
    }


def run_sair_adapter(args: argparse.Namespace) -> dict:
    from mathgraph.sair_real_compounding_benchmark import run_sair_real_compounding_benchmark

    report = run_sair_real_compounding_benchmark(
        equations_path=args.equations_path,
        matrix_path=args.matrix_path,
        out_dir=Path(args.out_dir) / "sair_adapter",
        train_size=args.train_size,
        heldout_size=args.heldout_size,
        seeds=tuple(int(x.strip()) for x in args.seeds.split(",") if x.strip()),
        max_attempts_per_mode=args.max_attempts_per_mode,
        fallback_if_missing=args.fallback_if_missing,
    )
    return {
        "real_sair_used": report.real_sair_used,
        "fallback_mode": report.fallback_mode,
        "advisory_boundary_preserved": report.advisory_boundary_preserved,
        "aggregate_metrics": report.aggregate_metrics,
        "outputs": report.outputs,
        "message": report.message,
    }


def markdown(report: dict) -> str:
    mech = report["mechanistic_fixture"]
    econ = mech["sustained_use"]
    lines = [
        "# Open Math Model × MathGraph — Sustained-Use Evaluation V1",
        "",
        f"- verdict: `{report['verdict']}`",
        f"- cold cost: `{econ['cold_cost']}` candidate verifier calls",
        f"- warm cost: `{econ['warm_cost']}` candidate verifier calls",
        f"- compression: `{econ['compression_ratio']:.3f}x`",
        f"- relative cost reduction: `{econ['relative_cost_reduction']:.2%}`",
        f"- sham control solves: `{econ['sham_solution_count']}`",
        f"- ablation solves under warm budget: `{econ['ablation_solution_count']}`",
        f"- restart solves: `{econ['restart_solution_count']}`",
        "",
        "The fixture is model-independent and exact. It validates the evaluation contract before any claim is made about an external model.",
        "",
        "## Claim boundary",
        "",
        mech["claim_boundary"],
    ]
    if "sair_adapter" in report:
        sair = report["sair_adapter"]
        lines.extend(
            [
                "",
                "## SAIR-capable adapter",
                "",
                f"- real_sair_used: `{sair['real_sair_used']}`",
                f"- fallback_mode: `{sair['fallback_mode']}`",
                f"- advisory_boundary_preserved: `{sair['advisory_boundary_preserved']}`",
                f"- compounding_signal_detected: `{sair['aggregate_metrics'].get('compounding_signal_detected')}`",
            ]
        )
        if sair.get("message"):
            lines.extend(["", f"> {sair['message']}"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="/tmp/open_math_model_sustained_use_v1")
    parser.add_argument("--run-sair", action="store_true")
    parser.add_argument("--equations-path", default="/content/equations.txt")
    parser.add_argument("--matrix-path", default="/content/etp_matrix_full_best_bool.npy")
    parser.add_argument("--train-size", type=int, default=40)
    parser.add_argument("--heldout-size", type=int, default=40)
    parser.add_argument("--seeds", default="0,1")
    parser.add_argument("--max-attempts-per-mode", type=int, default=40)
    fallback = parser.add_mutually_exclusive_group()
    fallback.add_argument("--fallback-if-missing", dest="fallback_if_missing", action="store_true", default=True)
    fallback.add_argument("--no-fallback-if-missing", dest="fallback_if_missing", action="store_false")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mechanistic = run_mechanistic_fixture()
    report = {
        "protocol": "OPEN_MATH_MODEL_SUSTAINED_USE_EVAL_V1",
        "mechanistic_fixture": mechanistic,
        "verdict": mechanistic["verdict"],
    }
    if args.run_sair:
        report["sair_adapter"] = run_sair_adapter(args)
        if not report["sair_adapter"]["advisory_boundary_preserved"]:
            report["verdict"] = "FAIL"

    (out_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
