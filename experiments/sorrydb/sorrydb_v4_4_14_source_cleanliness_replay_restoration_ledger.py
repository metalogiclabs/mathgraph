from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

VERSION = "v4.4.14"
SOURCE_ROOT = Path(".mathgraph_source_cache/siddhartha-gadgil__MetaExamples__edbb75e784db")
OUT = Path("artifacts/sorrydb/source_cleanliness_v4_4_14")
EXPECTED_COMMIT = "edbb75e784db19846a1c19841e182b797afc18bb"
TARGET_FILE = "MetaExamples/Fiddle.lean"


def run(cmd: list[str], cwd: Path | None = None) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "cmd": cmd,
        "cwd": str(cwd) if cwd else None,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "stdout_tail": proc.stdout[-8000:],
        "stderr_tail": proc.stderr[-8000:],
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    if not SOURCE_ROOT.exists():
        raise SystemExit(f"missing source root: {SOURCE_ROOT}")

    commit_probe = run(["git", "rev-parse", "HEAD"], cwd=SOURCE_ROOT)
    status_probe = run(["git", "status", "--short"], cwd=SOURCE_ROOT)
    diff_probe = run(["git", "diff", "--", TARGET_FILE], cwd=SOURCE_ROOT)
    diff_name_probe = run(["git", "diff", "--name-only"], cwd=SOURCE_ROOT)
    target_exists = (SOURCE_ROOT / TARGET_FILE).exists()

    actual_commit = commit_probe["stdout"].strip()
    git_status_short = status_probe["stdout"].strip()
    untracked_paths = [
        line[3:] for line in git_status_short.splitlines()
        if line.startswith("?? ")
    ]
    tracked_dirty_paths = [
        line for line in git_status_short.splitlines()
        if line and not line.startswith("?? ")
    ]
    source_status_clean = status_probe["returncode"] == 0 and git_status_short == ""
    source_has_untracked_paths = bool(untracked_paths)
    source_tracked_changes_clean = status_probe["returncode"] == 0 and not tracked_dirty_paths
    target_diff_clean = diff_probe["returncode"] == 0 and diff_probe["stdout"].strip() == ""
    full_diff_clean = diff_name_probe["returncode"] == 0 and diff_name_probe["stdout"].strip() == ""
    commit_matches = actual_commit == EXPECTED_COMMIT

    summary = {
        "version": VERSION,
        "status": "SOURCE_CLEANLINESS_REPLAY_RESTORATION_LEDGERED",
        "source_root": str(SOURCE_ROOT.resolve()),
        "target_file": TARGET_FILE,
        "expected_commit": EXPECTED_COMMIT,
        "actual_commit": actual_commit,
        "commit_matches": commit_matches,
        "target_exists": target_exists,
        "git_status_clean": source_status_clean,
        "source_has_untracked_paths": source_has_untracked_paths,
        "source_untracked_path_count": len(untracked_paths),
        "source_untracked_paths": untracked_paths,
        "source_tracked_changes_clean": source_tracked_changes_clean,
        "source_tracked_dirty_paths": tracked_dirty_paths,
        "target_diff_clean": target_diff_clean,
        "full_diff_clean": full_diff_clean,
        "restoration_invariant_passed": commit_matches and target_exists and source_tracked_changes_clean and target_diff_clean and full_diff_clean,
        "bounded_claim": [
            "after v4.4.11 replay and v4.4.13 seed packaging, the hydrated source checkout remains at the expected pinned commit",
            "the target source file has no git diff",
            "the source checkout has no tracked file modifications",
            "untracked cache/build artifacts may remain after cache hydration and are recorded rather than hidden",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "new accepted patches",
            "general SorryDB mining",
            "arbitrary proof repair",
            "upstream submission",
            "that source cleanliness proves semantic portability",
        ],
        "next_frontier": "v4.4.15 package the minimal end-to-end SorryDB microflywheel report",
    }

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "commit_probe.json", commit_probe)
    write_json(OUT / "git_status_probe.json", status_probe)
    write_json(OUT / "target_diff_probe.json", diff_probe)
    write_json(OUT / "diff_name_probe.json", diff_name_probe)

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
