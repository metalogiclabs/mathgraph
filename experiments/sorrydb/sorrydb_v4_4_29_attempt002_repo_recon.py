from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

VERSION = "v4.4.29"
OUT = Path("artifacts/sorrydb/attempt002_repo_recon_v4_4_29")
WORK = Path(".tmp_sorrydb_attempt002_recon")

INPUTS = {
    "snippet_summary": Path("artifacts/sorrydb/attempt002_snippet_inspection_v4_4_28/summary.json"),
    "snippet_inspection": Path("artifacts/sorrydb/attempt002_snippet_inspection_v4_4_28/snippet_inspection.json"),
}

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def run(cmd: list[str], cwd: Path | None = None, timeout: int = 60) -> dict[str, Any]:
    p = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    return {
        "cmd": cmd,
        "cwd": str(cwd) if cwd else None,
        "returncode": p.returncode,
        "stdout": p.stdout[-5000:],
        "stderr": p.stderr[-5000:],
        "ok": p.returncode == 0,
    }

def file_head(path: Path, limit: int = 120) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:limit])

def main() -> None:
    missing = [str(path) for path in INPUTS.values() if not path.exists()]
    if missing:
        raise SystemExit("missing inputs: " + json.dumps(missing, indent=2))

    OUT.mkdir(parents=True, exist_ok=True)

    snippet_summary = load_json(INPUTS["snippet_summary"])
    inspection = load_json(INPUTS["snippet_inspection"])
    selected = inspection.get("selected_candidate")
    if not selected:
        raise SystemExit("no selected candidate in v4.4.28")

    repo = selected["repo"]
    commit = selected["html_url"].split("/blob/")[1].split("/")[0]
    target_path = selected["path"]
    clone_url = f"https://github.com/{repo}.git"

    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True, exist_ok=True)

    steps: list[dict[str, Any]] = []
    steps.append(run(["git", "clone", "--filter=blob:none", "--depth", "1", clone_url, "repo"], cwd=WORK, timeout=120))
    repo_dir = WORK / "repo"

    checkout_attempted = False
    if repo_dir.exists():
        checkout_attempted = True
        steps.append(run(["git", "fetch", "--depth", "1", "origin", commit], cwd=repo_dir, timeout=120))
        steps.append(run(["git", "checkout", commit], cwd=repo_dir, timeout=60))

    manifest_files = {}
    if repo_dir.exists():
        for name in ["leanpkg.toml", "lean-toolchain", "lakefile.lean", "lakefile.toml", "lake-manifest.json", "README.md"]:
            manifest_files[name] = {
                "exists": (repo_dir / name).exists(),
                "head": file_head(repo_dir / name, 80),
            }

    target_file = repo_dir / target_path
    target_exists = target_file.exists()
    target_text = target_file.read_text(encoding="utf-8", errors="replace") if target_exists else ""
    target_lines = target_text.splitlines()
    sorry_lines = [
        {
            "line_number": i + 1,
            "line": line,
        }
        for i, line in enumerate(target_lines)
        if "sorry" in line
    ]

    lean_version_guess = "UNKNOWN"
    if manifest_files.get("leanpkg.toml", {}).get("exists"):
        lean_version_guess = "LEAN3_LEANPKG"
    if manifest_files.get("lakefile.lean", {}).get("exists") or manifest_files.get("lakefile.toml", {}).get("exists"):
        lean_version_guess = "LEAN4_LAKE"
    if manifest_files.get("lean-toolchain", {}).get("exists"):
        lean_version_guess += "_TOOLCHAIN_PRESENT"

    replay_risk = "HIGH"
    risk_reasons = []
    if "LEAN3" in lean_version_guess:
        risk_reasons.append("repo appears Lean 3 / leanpkg")
    if "equate" in target_text:
        risk_reasons.append("target depends on custom equate tactic")
    if "†" in target_text or "adj" in target_text.lower():
        risk_reasons.append("target uses adjoint/custom notation")
    if len(sorry_lines) == 1:
        risk_reasons.append("single sorry target")
    if target_exists and len(target_lines) <= 120:
        risk_reasons.append("small target file")

    if "LEAN3" in lean_version_guess and "target depends on custom equate tactic" in risk_reasons:
        replay_risk = "MEDIUM_HIGH"
    if not target_exists:
        replay_risk = "BLOCKED_TARGET_FILE_MISSING"

    exact_source_window = ""
    if target_exists and sorry_lines:
        line_no = sorry_lines[0]["line_number"]
        start = max(1, line_no - 5)
        end = min(len(target_lines), line_no + 5)
        exact_source_window = "\n".join(f"{i}: {target_lines[i-1]}" for i in range(start, end + 1))

    recon = {
        "version": VERSION,
        "recon_type": "ATTEMPT002_REPO_RECON_BEFORE_REPLAY",
        "input_version": snippet_summary.get("version"),
        "repo": repo,
        "clone_url": clone_url,
        "commit": commit,
        "target_path": target_path,
        "clone_attempted": True,
        "checkout_attempted": checkout_attempted,
        "target_exists": target_exists,
        "target_line_count": len(target_lines),
        "sorry_count": len(sorry_lines),
        "sorry_lines": sorry_lines,
        "exact_source_window": exact_source_window,
        "manifest_files": manifest_files,
        "lean_version_guess": lean_version_guess,
        "replay_risk": replay_risk,
        "risk_reasons": risk_reasons,
        "steps": steps,
        "replay_attempted": False,
        "build_attempted": False,
        "upstream_contact_performed": False,
        "decision": "DO_NOT_REPLAY_YET_REQUIRES_LEAN3_ENV_AND_EQUATE_CONTEXT",
    }

    summary = {
        "version": VERSION,
        "status": "ATTEMPT002_REPO_RECON_LEDGERED",
        "input_version": snippet_summary.get("version"),
        "repo": repo,
        "commit": commit,
        "target_path": target_path,
        "target_exists": target_exists,
        "sorry_count": len(sorry_lines),
        "lean_version_guess": lean_version_guess,
        "replay_risk": replay_risk,
        "clone_attempted": True,
        "checkout_attempted": checkout_attempted,
        "build_attempted": False,
        "replay_attempted": False,
        "upstream_contact_performed": False,
        "decision": recon["decision"],
        "bounded_claim": [
            "v4.4.29 clones the selected attempt002 repo into a bounded temporary directory for reconnaissance",
            "it records manifest files, target-file presence, sorry count, and Lean-version risk before replay",
            "it does not run Lean, build the repo, modify upstream, or contact maintainers",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "candidate repairability",
            "that the repo builds locally",
            "that the selected sorry has a repair",
            "upstream acceptance",
            "automated external contact",
        ],
        "next_frontier": "v4.4.30 either install/locate a safe Lean3 replay path for this candidate or park it and choose a lower-risk Lean4/Nat/simp target",
    }

    report = f"""# SorryDB v4.4.29 — Attempt 002 Repo Recon

## Result

- repo: {repo}
- commit: {commit}
- target path: {target_path}
- target exists: {target_exists}
- sorry count: {len(sorry_lines)}
- lean version guess: {lean_version_guess}
- replay risk: {replay_risk}
- build attempted: false
- replay attempted: false
- decision: {recon["decision"]}

## Risk reasons

{chr(10).join("- " + r for r in risk_reasons)}

## Exact source window

{exact_source_window}

## Boundary

Repo was cloned only into `.tmp_sorrydb_attempt002_recon`. No Lean build, Lean replay, upstream modification, or maintainer contact was performed.

## Next frontier

Either install/locate a safe Lean3 replay path for this candidate or park it and choose a lower-risk Lean4/Nat/simp target.
"""

    write_json(OUT / "summary.json", summary)
    write_json(OUT / "repo_recon.json", recon)
    (OUT / "report.md").write_text(report, encoding="utf-8")

    shutil.rmtree(WORK, ignore_errors=True)

    print(json.dumps(summary, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
