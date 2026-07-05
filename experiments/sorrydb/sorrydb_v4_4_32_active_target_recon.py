from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

VERSION = "v4.4.32"
OUT = Path("artifacts/sorrydb/active_target_recon_v4_4_32")
WORK = Path(".tmp_sorrydb_v4_4_32_active_target_recon")

INPUTS = {
    "filter_summary": Path("artifacts/sorrydb/commented_sorry_filter_v4_4_31/summary.json"),
    "filter_ledger": Path("artifacts/sorrydb/commented_sorry_filter_v4_4_31/commented_sorry_filter.json"),
}

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def run(cmd: list[str], cwd: Path | None = None, timeout: int = 120) -> dict[str, Any]:
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

def head(path: Path, n: int = 120) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:n])

def sorry_windows(text: str, radius: int = 5) -> list[dict[str, Any]]:
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        if "sorry" not in line:
            continue
        stripped = line.strip()
        comment_only = stripped.startswith("--") or stripped.startswith("/-")
        start = max(0, i - radius)
        end = min(len(lines), i + radius + 1)
        out.append({
            "line_number": i + 1,
            "line": line,
            "comment_only": comment_only,
            "snippet": "\n".join(f"{j+1}: {lines[j]}" for j in range(start, end)),
        })
    return out

def main() -> None:
    missing = [str(p) for p in INPUTS.values() if not p.exists()]
    if missing:
        raise SystemExit("missing inputs: " + json.dumps(missing, indent=2))

    OUT.mkdir(parents=True, exist_ok=True)

    filter_summary = load_json(INPUTS["filter_summary"])
    filter_ledger = load_json(INPUTS["filter_ledger"])
    selected = filter_ledger["selected_candidate"]

    repo = selected["repo"]
    target_path = selected["path"]
    html_url = selected["html_url"]
    commit = html_url.split("/blob/")[1].split("/")[0]
    clone_url = f"https://github.com/{repo}.git"

    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True, exist_ok=True)

    steps = []
    steps.append(run(["git", "clone", "--filter=blob:none", "--depth", "1", clone_url, "repo"], cwd=WORK, timeout=180))
    repo_dir = WORK / "repo"

    checkout_attempted = False
    if repo_dir.exists():
        checkout_attempted = True
        steps.append(run(["git", "fetch", "--depth", "1", "origin", commit], cwd=repo_dir, timeout=180))
        steps.append(run(["git", "checkout", commit], cwd=repo_dir, timeout=120))

    manifest_files = {}
    if repo_dir.exists():
        for name in ["lakefile.lean", "lakefile.toml", "lean-toolchain", "lake-manifest.json", "README.md"]:
            p = repo_dir / name
            manifest_files[name] = {
                "exists": p.exists(),
                "head": head(p, 80),
            }

    target_file = repo_dir / target_path
    target_exists = target_file.exists()
    target_text = target_file.read_text(encoding="utf-8", errors="replace") if target_exists else ""
    windows = sorry_windows(target_text)
    active_windows = [w for w in windows if not w["comment_only"]]

    lean_toolchain = manifest_files.get("lean-toolchain", {}).get("head", "").strip()
    lakefile_present = manifest_files.get("lakefile.lean", {}).get("exists") or manifest_files.get("lakefile.toml", {}).get("exists")
    lean4_likely = bool(lakefile_present and lean_toolchain)

    imports = [line for line in target_text.splitlines() if line.strip().startswith("import ")]
    local_imports = [x for x in imports if "equational_theories" in x or "EquationalTheories" in x]

    risk_reasons = []
    replay_risk = "UNKNOWN"

    if lean4_likely:
        risk_reasons.append("Lean4/lake repo detected")
    if target_exists:
        risk_reasons.append("target file exists at selected commit")
    if len(active_windows) == 1:
        risk_reasons.append("single active sorry remains in target file")
    if local_imports:
        risk_reasons.append("target depends on local equational_theories imports")
    if "Definability" in target_path:
        risk_reasons.append("definability theorem likely depends on project-specific infrastructure")
    if "decide +kernel" in target_text:
        risk_reasons.append("uses decide +kernel syntax nearby")
    if "by rfl" in target_text:
        risk_reasons.append("rfl witness nearby")

    if lean4_likely and target_exists and len(active_windows) == 1:
        replay_risk = "MEDIUM"
    if local_imports and "Definability" in target_path:
        replay_risk = "MEDIUM_HIGH_BUT_REAL_LEAN4_TARGET"
    if not target_exists:
        replay_risk = "BLOCKED_TARGET_FILE_MISSING"

    decision = "READY_FOR_BOUNDED_SOURCE_ONLY_PATCH_EXPERIMENT_NO_UPSTREAM_CONTACT"
    if replay_risk.startswith("BLOCKED"):
        decision = "PARK_TARGET_MISSING"
    elif not lean4_likely:
        decision = "PARK_UNTIL_LEAN4_ENV_CONFIRMED"

    recon = {
        "version": VERSION,
        "recon_type": "ACTIVE_TARGET_RECON_BEFORE_REPLAY",
        "input_version": filter_summary.get("version"),
        "repo": repo,
        "clone_url": clone_url,
        "commit": commit,
        "target_path": target_path,
        "clone_attempted": True,
        "checkout_attempted": checkout_attempted,
        "target_exists": target_exists,
        "target_line_count": len(target_text.splitlines()),
        "sorry_count": len(windows),
        "active_sorry_count": len(active_windows),
        "commented_sorry_count": len(windows) - len(active_windows),
        "active_sorry_windows": active_windows,
        "imports": imports,
        "local_imports": local_imports,
        "manifest_files": manifest_files,
        "lean_toolchain": lean_toolchain,
        "lean4_likely": lean4_likely,
        "replay_risk": replay_risk,
        "risk_reasons": risk_reasons,
        "steps": steps,
        "build_attempted": False,
        "replay_attempted": False,
        "patch_attempted": False,
        "upstream_contact_performed": False,
        "decision": decision,
    }

    summary = {
        "version": VERSION,
        "status": "ACTIVE_TARGET_RECON_LEDGERED",
        "input_version": filter_summary.get("version"),
        "repo": repo,
        "commit": commit,
        "target_path": target_path,
        "target_exists": target_exists,
        "lean_toolchain": lean_toolchain,
        "lean4_likely": lean4_likely,
        "active_sorry_count": len(active_windows),
        "replay_risk": replay_risk,
        "clone_attempted": True,
        "checkout_attempted": checkout_attempted,
        "build_attempted": False,
        "replay_attempted": False,
        "patch_attempted": False,
        "upstream_contact_performed": False,
        "decision": decision,
        "bounded_claim": [
            "v4.4.32 clones the selected active-sorry target into a bounded temporary directory for reconnaissance",
            "it records manifest files, Lean toolchain, target exactness, imports, and active-sorry count",
            "it does not build, replay Lean, patch the target, modify upstream, or contact maintainers",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "candidate repairability",
            "that the repo builds locally",
            "that a patch exists",
            "upstream acceptance",
            "automated external contact",
        ],
        "next_frontier": "v4.4.33 run a bounded source-only patch experiment on the exact target file, then replay only if the patch is syntactically plausible",
    }

    first_window = active_windows[0]["snippet"] if active_windows else "(none)"
    report = f"""# SorryDB v4.4.32 — Active Target Recon

## Result

- repo: {repo}
- commit: {commit}
- target path: {target_path}
- target exists: {target_exists}
- Lean toolchain: {lean_toolchain}
- Lean4 likely: {lean4_likely}
- active sorry count: {len(active_windows)}
- replay risk: {replay_risk}
- build attempted: false
- replay attempted: false
- patch attempted: false
- decision: {decision}

## Risk reasons

{chr(10).join("- " + r for r in risk_reasons)}

## Imports

{chr(10).join(imports) if imports else "(none)"}

## First active sorry window

{first_window}

## Boundary

Repo was cloned only into `.tmp_sorrydb_v4_4_32_active_target_recon`. No Lean build, Lean replay, patch, upstream modification, or maintainer contact was performed.

## Next frontier

Run a bounded source-only patch experiment on the exact target file, then replay only if the patch is syntactically plausible.
"""

    write_json(OUT / "summary.json", summary)
    write_json(OUT / "active_target_recon.json", recon)
    (OUT / "report.md").write_text(report, encoding="utf-8")

    shutil.rmtree(WORK, ignore_errors=True)

    print(json.dumps(summary, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
