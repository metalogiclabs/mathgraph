from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

VERSION = "v4.4.9"
OUT_DIR = Path("artifacts/sorrydb/cache_hydration_plan_v4_4_9")
V448_SUMMARY = Path("artifacts/sorrydb/hydrated_backfill_reality_v4_4_8/summary.json")
V447_QUEUE = Path("artifacts/sorrydb/hydrated_backfill_queue_v4_4_7/backfill_queue.json")
V446_SUMMARY = Path("artifacts/sorrydb/source_hydration_v4_4_6/summary.json")

REQUIRED_GB = 8.0

STATUS_READY = "CACHE_HYDRATION_READY"
STATUS_REPO_ROOT_MISSING = "CACHE_HYDRATION_BLOCKED_REPO_ROOT_MISSING"
STATUS_TOOLCHAIN_MISSING = "CACHE_HYDRATION_BLOCKED_TOOLCHAIN_MISSING"
STATUS_LAKEFILE_MISSING = "CACHE_HYDRATION_BLOCKED_LAKEFILE_MISSING"
STATUS_MANIFEST_MISSING = "CACHE_HYDRATION_BLOCKED_MANIFEST_MISSING"
STATUS_MATHLIB_SOURCE_MISSING = "CACHE_HYDRATION_BLOCKED_MATHLIB_SOURCE_MISSING"
STATUS_DISK_LOW = "CACHE_HYDRATION_BLOCKED_DISK_LOW"
STATUS_ALREADY = "CACHE_HYDRATION_ALREADY_SATISFIED"
STATUS_UNCLASSIFIED = "CACHE_HYDRATION_UNCLASSIFIED"


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def run_readonly(cmd: list[str], cwd: Path | None = None) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
            check=False,
        )
        return {
            "cmd": cmd,
            "cwd": str(cwd) if cwd else None,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as exc:
        return {
            "cmd": cmd,
            "cwd": str(cwd) if cwd else None,
            "returncode": None,
            "stdout": "",
            "stderr": repr(exc),
        }


def free_gb(path: Path) -> float:
    probe = path if path.exists() else Path.cwd()
    usage = shutil.disk_usage(str(probe))
    return round(usage.free / (1024 ** 3), 3)


def dir_size(path: Path) -> str | None:
    if not path.exists():
        return None
    result = run_readonly(["du", "-sh", str(path)])
    if result["returncode"] != 0:
        return None
    return result["stdout"].split()[0] if result["stdout"] else None


def first_repo_root_from_queue(queue: dict[str, Any]) -> str | None:
    candidates = queue.get("candidates") or []
    for c in candidates:
        if c.get("repo_root"):
            return c["repo_root"]
    return None


def classify_cache_hydration(repo_root: Path, expected_commit: str | None, required_gb: float = REQUIRED_GB, free_gb_override: float | None = None) -> dict[str, Any]:
    toolchain = repo_root / "lean-toolchain"
    lakefile_lean = repo_root / "lakefile.lean"
    lakefile_toml = repo_root / "lakefile.toml"
    lakefile = lakefile_lean if lakefile_lean.exists() else lakefile_toml
    lake_manifest = repo_root / "lake-manifest.json"
    mathlib_package = repo_root / ".lake/packages/mathlib"
    mathlib_olean = mathlib_package / ".lake/build/lib/lean/Mathlib.olean"

    actual_commit = None
    if repo_root.exists():
        result = run_readonly(["git", "-C", str(repo_root), "rev-parse", "HEAD"])
        if result["returncode"] == 0:
            actual_commit = result["stdout"].strip()

    fg = free_gb_override if free_gb_override is not None else free_gb(repo_root)

    if not repo_root.exists():
        status = STATUS_REPO_ROOT_MISSING
    elif expected_commit and actual_commit and actual_commit != expected_commit:
        status = STATUS_UNCLASSIFIED
    elif not toolchain.exists():
        status = STATUS_TOOLCHAIN_MISSING
    elif not lakefile.exists():
        status = STATUS_LAKEFILE_MISSING
    elif not lake_manifest.exists():
        status = STATUS_MANIFEST_MISSING
    elif not mathlib_package.exists():
        status = STATUS_MATHLIB_SOURCE_MISSING
    elif mathlib_olean.exists():
        status = STATUS_ALREADY
    elif fg < required_gb:
        status = STATUS_DISK_LOW
    else:
        status = STATUS_READY

    return {
        "repo_root": str(repo_root),
        "expected_commit": expected_commit,
        "actual_commit": actual_commit,
        "toolchain_file": str(toolchain),
        "toolchain_exists": toolchain.exists(),
        "lakefile": str(lakefile),
        "lakefile_lean_exists": lakefile_lean.exists(),
        "lakefile_toml_exists": lakefile_toml.exists(),
        "lakefile_exists": lakefile.exists(),
        "lake_manifest": str(lake_manifest),
        "lake_manifest_exists": lake_manifest.exists(),
        "mathlib_package": str(mathlib_package),
        "mathlib_package_exists": mathlib_package.exists(),
        "mathlib_olean_path": str(mathlib_olean),
        "mathlib_olean_exists": mathlib_olean.exists(),
        "free_gb": fg,
        "required_gb": required_gb,
        "status": status,
    }


def build_plan() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    v448 = read_json(V448_SUMMARY, {})
    v447_queue = read_json(V447_QUEUE, {})
    v446 = read_json(V446_SUMMARY, {})

    repo_root_str = (
        first_repo_root_from_queue(v447_queue)
        or v446.get("controlled_cache_path")
        or v446.get("repo_root")
        or ""
    )
    expected_commit = v446.get("commit") or v446.get("expected_commit") or v446.get("repo_commit")

    repo_root = Path(repo_root_str) if repo_root_str else Path("__missing_repo_root__")
    probe = classify_cache_hydration(repo_root, expected_commit)

    recommended_commands = []
    if probe["status"] == STATUS_READY:
        recommended_commands.append(f"cd {repo_root}")
        recommended_commands.append("lake exe cache get")

    optional_followup = f"cd {repo_root} && lake env lean MetaExamples/Fiddle.lean"

    environment_probe = {
        "version": VERSION,
        "lean_version": run_readonly(["lean", "--version"]),
        "lake_version": run_readonly(["lake", "--version"]),
        "elan_lean_path": run_readonly(["elan", "which", "lean"]),
        "repo_git_status": run_readonly(["git", "-C", str(repo_root), "status", "--short"]) if repo_root.exists() else None,
        "repo_git_commit": run_readonly(["git", "-C", str(repo_root), "rev-parse", "HEAD"]) if repo_root.exists() else None,
        "disk_probe": {
            "repo_root_free_gb": probe["free_gb"],
            "required_gb": REQUIRED_GB,
        },
        "path_probe": {
            "repo_root_exists": repo_root.exists(),
            "lean_toolchain_exists": probe["toolchain_exists"],
            "lakefile": probe["lakefile"],
            "lakefile_lean_exists": probe.get("lakefile_lean_exists"),
            "lakefile_toml_exists": probe.get("lakefile_toml_exists"),
            "lakefile_exists": probe["lakefile_exists"],
            "lake_manifest_exists": probe["lake_manifest_exists"],
            "mathlib_package_exists": probe["mathlib_package_exists"],
            "mathlib_olean_exists": probe["mathlib_olean_exists"],
            "mathlib_package_size": dir_size(repo_root / ".lake/packages/mathlib"),
            "lake_build_size": dir_size(repo_root / ".lake/build"),
        },
        "command_probe_results": {
            "forbidden_commands_executed": [],
            "readonly_only": True,
        },
    }

    plan = {
        "version": VERSION,
        "repo_root": probe["repo_root"],
        "expected_commit": probe["expected_commit"],
        "actual_commit": probe["actual_commit"],
        "toolchain_file": probe["toolchain_file"],
        "toolchain_exists": probe["toolchain_exists"],
        "lakefile": probe["lakefile"],
        "lakefile_lean_exists": probe["lakefile_lean_exists"],
        "lakefile_toml_exists": probe["lakefile_toml_exists"],
        "lakefile": probe["lakefile"],
            "lakefile_lean_exists": probe.get("lakefile_lean_exists"),
            "lakefile_toml_exists": probe.get("lakefile_toml_exists"),
            "lakefile_exists": probe["lakefile_exists"],
        "lake_manifest_exists": probe["lake_manifest_exists"],
        "mathlib_package_exists": probe["mathlib_package_exists"],
        "mathlib_olean_path": probe["mathlib_olean_path"],
        "mathlib_olean_exists": probe["mathlib_olean_exists"],
        "free_gb": probe["free_gb"],
        "required_gb": probe["required_gb"],
        "status": probe["status"],
        "recommended_commands": recommended_commands,
        "optional_followup_baseline_command_not_part_of_v4_4_9": optional_followup,
        "forbidden_commands_in_this_step": [
            "lake exe cache get",
            "lake build",
            "lake update",
            "lake env lean MetaExamples/Fiddle.lean",
            "lean MetaExamples/Fiddle.lean",
            "git fetch",
            "git pull",
            "network dependency download commands",
        ],
        "expected_postconditions": [
            "Mathlib.olean exists in the hydrated source cache search path",
            "baseline Lean contact can be retried under controlled replay",
        ],
        "source_obstruction_from_v4_4_8": {
            "queue_verdict": v448.get("queue_verdict"),
            "primary_obstruction": v448.get("primary_obstruction"),
            "primary_obstruction_detail": v448.get("primary_obstruction_detail"),
            "candidate_count": v448.get("candidate_count"),
            "failed_count": v448.get("failed_count"),
        },
        "notes": [
            "This planner does not hydrate cache.",
            "This planner does not run Lean, Lake build, replay, proof checking, or network downloads.",
        ],
    }

    summary = {
        "version": VERSION,
        "status": "CACHE_DEPENDENCY_HYDRATION_PLANNED",
        "cache_hydration_status": probe["status"],
        "repo_root": probe["repo_root"],
        "repo_commit": probe["actual_commit"],
        "expected_commit": probe["expected_commit"],
        "mathlib_olean_exists": probe["mathlib_olean_exists"],
        "free_gb": probe["free_gb"],
        "recommended_command": " && ".join(recommended_commands) if recommended_commands else "",
        "postcondition": "Mathlib.olean exists and baseline Lean contact can be retried",
        "bounded_claim": [
            "identifies whether the pinned hydrated source checkout is ready for controlled cache hydration",
            "records the exact next command and expected postcondition when ready",
        ],
        "does_not_claim": [
            "cache hydration performed",
            "Lean replay success",
            "proof checking",
            "new proof discovery",
            "general SorryDB mining",
            "arbitrary proof repair",
            "upstream submission",
        ],
        "next_frontier": "v4.4.10 authorized controlled cache hydration reality, then rerun baseline contact",
    }

    return summary, plan, environment_probe


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary, plan, environment_probe = build_plan()
    write_json(OUT_DIR / "summary.json", summary)
    write_json(OUT_DIR / "cache_hydration_plan.json", plan)
    write_json(OUT_DIR / "environment_probe.json", environment_probe)
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
