#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GIB = 1024 ** 3
BANNER = "MATHGRAPH x SORRYDB v4.2.5 — CACHE/BUILD BOUNDARY INSPECTOR"

INSPECTED_CACHE_BUILD_BOUNDARY = "INSPECTED_CACHE_BUILD_BOUNDARY"
OBSTRUCTED_REPO_MISSING = "OBSTRUCTED_REPO_MISSING"
OBSTRUCTED_SOURCE_MISSING = "OBSTRUCTED_SOURCE_MISSING"
OBSTRUCTED_DISK_PRESSURE = "OBSTRUCTED_DISK_PRESSURE"

MATHLIB_OLEAN_REL = ".lake/packages/mathlib/.lake/build/lib/lean/Mathlib.olean"


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def nearest_existing(path: Path) -> Path:
    probe = path.expanduser()
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return probe


def free_gb(path: Path) -> float:
    return round(shutil.disk_usage(nearest_existing(path)).free / GIB, 3)


def read_text_tail(path: Path, limit: int = 12000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-limit:]


def exists(path: Path) -> bool:
    return path.exists()


def file_size(path: Path) -> int:
    if path.exists() and path.is_file():
        return path.stat().st_size
    return 0


def package_status(repo_root: Path, package: str) -> dict[str, Any]:
    root = repo_root / ".lake" / "packages" / package
    build_lib = root / ".lake" / "build" / "lib" / "lean"
    return {
        "package": package,
        "root": str(root),
        "root_exists": root.exists(),
        "build_lib": str(build_lib),
        "build_lib_exists": build_lib.exists(),
        "olean_count": len(list(build_lib.rglob("*.olean"))) if build_lib.exists() else 0,
    }


def classify(summary: dict[str, Any]) -> list[str]:
    findings: list[str] = []

    if not summary["repo_exists"]:
        return ["repo_missing"]

    if not summary["source_exists"]:
        return ["source_missing"]

    if not summary["lake_manifest_exists"]:
        findings.append("lake_manifest_missing")
    else:
        findings.append("lake_manifest_present")

    if summary["lean_toolchain"]:
        findings.append("lean_toolchain_present")
    else:
        findings.append("lean_toolchain_missing")

    if summary["mathlib_package_exists"]:
        findings.append("mathlib_package_present")
    else:
        findings.append("mathlib_package_missing")

    if summary["mathlib_olean_exists"]:
        findings.append("mathlib_olean_present")
    else:
        findings.append("mathlib_olean_missing")

    if summary["mathlib_package_exists"] and not summary["mathlib_olean_exists"]:
        findings.append("dependencies_cloned_but_mathlib_not_built_or_cached")

    if summary["lake_packages_count"] > 0 and not summary["mathlib_olean_exists"]:
        findings.append("lake_env_materialized_packages_without_olean_cache")

    return findings


def recommended_next(summary: dict[str, Any]) -> str:
    if not summary["repo_exists"]:
        return "hydrate_repo_first"
    if not summary["source_exists"]:
        return "resolve_source_path_first"
    if not summary["mathlib_package_exists"]:
        return "inspect_lake_manifest_or_dependency_fetch_boundary"
    if not summary["mathlib_olean_exists"]:
        return "next_safe_portal_is_cache_get_or_build_in_disposable_environment_not_local_proof_repair"
    return "baseline_replay_can_be_retried_without_dependency_materialization"


def main() -> int:
    print(BANNER)

    repo_root = Path(env("SORRYDB_V425_REPO_ROOT"))
    file_path = env("SORRYDB_V425_FILE_PATH")
    work_root = Path(env("SORRYDB_V425_WORK_ROOT", "/tmp/mathgraph_sorrydb_v425_cache_build_inspector"))
    required_gb = float(env("SORRYDB_V425_MIN_FREE_GB", "5"))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = work_root / "artifacts" / "runs" / "sorrydb_v4_2_5_cache_build_boundary_inspector" / timestamp
    out.mkdir(parents=True, exist_ok=True)

    source = repo_root / file_path if file_path else repo_root
    lake_manifest = repo_root / "lake-manifest.json"
    lakefile_lean = repo_root / "lakefile.lean"
    lakefile_toml = repo_root / "lakefile.toml"
    lean_toolchain = repo_root / "lean-toolchain"
    mathlib_pkg = repo_root / ".lake" / "packages" / "mathlib"
    mathlib_olean = repo_root / MATHLIB_OLEAN_REL
    packages_root = repo_root / ".lake" / "packages"

    summary: dict[str, Any] = {
        "repo_root": str(repo_root),
        "file_path": file_path,
        "source": str(source),
        "work_root": str(work_root),
        "required_gb": required_gb,
        "free_gb": {
            str(work_root): free_gb(work_root),
            str(repo_root): free_gb(repo_root),
            str(Path.home()): free_gb(Path.home()),
            str(Path.home() / ".cache"): free_gb(Path.home() / ".cache"),
        },
        "repo_exists": repo_root.exists(),
        "source_exists": source.exists(),
        "lake_manifest_exists": lake_manifest.exists(),
        "lake_manifest_size": file_size(lake_manifest),
        "lakefile_lean_exists": lakefile_lean.exists(),
        "lakefile_toml_exists": lakefile_toml.exists(),
        "lean_toolchain": read_text_tail(lean_toolchain, 1000).strip(),
        "mathlib_package_exists": mathlib_pkg.exists(),
        "mathlib_olean": str(mathlib_olean),
        "mathlib_olean_exists": mathlib_olean.exists(),
        "lake_packages_count": len([p for p in packages_root.iterdir() if p.is_dir()]) if packages_root.exists() else 0,
        "packages": [],
        "lake_manifest_tail": read_text_tail(lake_manifest, 12000),
        "lakefile_lean_tail": read_text_tail(lakefile_lean, 12000),
        "lakefile_toml_tail": read_text_tail(lakefile_toml, 12000),
        "findings": [],
        "recommended_next": "",
        "verdict": "",
    }

    if min(summary["free_gb"].values()) < required_gb:
        summary["verdict"] = OBSTRUCTED_DISK_PRESSURE
    elif not repo_root.exists():
        summary["verdict"] = OBSTRUCTED_REPO_MISSING
    elif not source.exists():
        summary["verdict"] = OBSTRUCTED_SOURCE_MISSING
    else:
        for pkg in [
            "mathlib",
            "batteries",
            "Qq",
            "aesop",
            "proofwidgets",
            "importGraph",
            "LeanSearchClient",
            "plausible",
            "leanaidecore",
            "Cli",
        ]:
            summary["packages"].append(package_status(repo_root, pkg))
        summary["findings"] = classify(summary)
        summary["recommended_next"] = recommended_next(summary)
        summary["verdict"] = INSPECTED_CACHE_BUILD_BOUNDARY

    (out / "cache_build_boundary_manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
