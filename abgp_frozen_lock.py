from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

from mathgraph.abgp.frozen_lock import build_frozen_lock, write_frozen_lock

def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()

def main() -> None:
    parser = argparse.ArgumentParser(description="Verify and emit the frozen ABGP lock")
    parser.add_argument("--output", type=Path, default=Path("abgp-frozen-lock.json"))
    args = parser.parse_args()
    lock = build_frozen_lock(
        repository_tree_hash=_git("rev-parse", "HEAD^{tree}"),
        repository_commit=_git("rev-parse", "HEAD"),
    )
    write_frozen_lock(args.output, lock)
    print("status", lock["status"])
    print("freeze_authorized", int(lock["freeze_authorized"]))
    print("planning_status", lock["planning_status"])
    print("implementation_status", lock["qualification_status"])
    print("confirmatory_execution_enabled", int(lock["confirmatory_execution_enabled"]))
    print("confirmatory_namespace_used", int(lock["confirmatory_namespace_used"]))
    print("repository_tree_hash", lock["repository_tree_hash"])
    print("lock_digest", lock["lock_digest"])
    print("ABGP_FROZEN_LOCK_VERIFIED_CONFIRMATION_DISABLED")

if __name__ == "__main__":
    main()
