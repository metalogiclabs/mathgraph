from __future__ import annotations

import argparse
from pathlib import Path

from mathgraph.abgp.final_candidate import (
    build_final_lock_candidate,
    write_final_lock_candidate,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build review-only ABGP final-lock candidate")
    parser.add_argument("--a-count", type=int, default=12)
    parser.add_argument("--b-worlds-per-direction", type=int, default=3)
    parser.add_argument("--g-worlds", type=int, default=6)
    parser.add_argument("--p-count", type=int, default=4)
    parser.add_argument("--output", type=Path, default=Path("abgp-final-lock-candidate.json"))
    args = parser.parse_args()
    candidate = build_final_lock_candidate(
        a_count=args.a_count,
        b_worlds_per_direction=args.b_worlds_per_direction,
        g_worlds=args.g_worlds,
        p_count=args.p_count,
    )
    write_final_lock_candidate(args.output, candidate)
    print("status", candidate["status"])
    print("implementation_qualified", int(candidate["implementation_qualification"]["implementation_qualified"]))
    print("planning_approved", int(candidate["planning_proposal"]["approved_by_collaborators"]))
    print("complete_pass_power_qualified", int(candidate["planning_proposal"]["complete_pass_power_qualified"]))
    print("freeze_authorized", int(candidate["freeze_authorized"]))
    print("confirmatory_namespace_used", int(candidate["confirmatory_namespace_used"]))
    print("candidate_digest", candidate["candidate_digest"])
    print("ABGP_FINAL_LOCK_CANDIDATE_REVIEW_PENDING")


if __name__ == "__main__":
    main()
