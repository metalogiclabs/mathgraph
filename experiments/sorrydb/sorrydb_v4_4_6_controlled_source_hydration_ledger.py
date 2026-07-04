#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Iterable


VERSION = "v4.4.6"
STATUS = "CONTROLLED_SOURCE_HYDRATION_LEDGERED"

SOURCE_HYDRATED_VERIFIED = "SOURCE_HYDRATED_VERIFIED"
SOURCE_HYDRATED_FILE_MISSING = "SOURCE_HYDRATED_FILE_MISSING"
SOURCE_HYDRATED_SNIPPET_NOT_FOUND = "SOURCE_HYDRATED_SNIPPET_NOT_FOUND"
SOURCE_HYDRATED_SNIPPET_AMBIGUOUS = "SOURCE_HYDRATED_SNIPPET_AMBIGUOUS"
SOURCE_HYDRATED_SNIPPET_HASH_MISMATCH = "SOURCE_HYDRATED_SNIPPET_HASH_MISMATCH"
SOURCE_HYDRATED_COMMIT_MISMATCH = "SOURCE_HYDRATED_COMMIT_MISMATCH"
SOURCE_HYDRATION_BLOCKED_REPO_IDENTITY = "SOURCE_HYDRATION_BLOCKED_REPO_IDENTITY"
SOURCE_HYDRATION_FAILED = "SOURCE_HYDRATION_FAILED"
SOURCE_HYDRATION_UNCLASSIFIED = "SOURCE_HYDRATION_UNCLASSIFIED"

CATEGORIES = (
    SOURCE_HYDRATED_VERIFIED,
    SOURCE_HYDRATED_FILE_MISSING,
    SOURCE_HYDRATED_SNIPPET_NOT_FOUND,
    SOURCE_HYDRATED_SNIPPET_AMBIGUOUS,
    SOURCE_HYDRATED_SNIPPET_HASH_MISMATCH,
    SOURCE_HYDRATED_COMMIT_MISMATCH,
    SOURCE_HYDRATION_BLOCKED_REPO_IDENTITY,
    SOURCE_HYDRATION_FAILED,
    SOURCE_HYDRATION_UNCLASSIFIED,
)

PINNED_REPO_URL = "https://github.com/siddhartha-gadgil/MetaExamples"
PINNED_COMMIT = "edbb75e784db19846a1c19841e182b797afc18bb"

DEFAULT_PLAN = Path("artifacts/sorrydb/source_registration_v4_4_5/registration_plan.json")
DEFAULT_PLAN_SUMMARY = Path("artifacts/sorrydb/source_registration_v4_4_5/summary.json")
DEFAULT_FIXTURE_PLAN = Path("artifacts/sorrydb/source_registration_v4_4_5/fixture_plan.json")
DEFAULT_SNIPPET_DIR = Path("artifacts/sorrydb/source_inputs_v4_4_4/source_snippets")
DEFAULT_CACHE_ROOT = Path(".mathgraph_source_cache")
DEFAULT_OUTPUT_DIR = Path("artifacts/sorrydb/source_hydration_v4_4_6")


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value is not an object")
    return value


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cache_name(repo_url: str, commit: str) -> str:
    repo = repo_url.rstrip("/").removesuffix(".git")
    parts = repo.split("/")
    owner = parts[-2] if len(parts) >= 2 else "repo"
    name = parts[-1] if parts else "source"
    return f"{owner}__{name}__{commit[:12]}"


def run_git(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


@dataclass
class HydrationResult:
    success: bool
    actual_commit: str = ""
    commands: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""


def hydrate_repository(
    repo_url: str,
    commit: str,
    cache_path: Path,
    *,
    allowed_pairs: set[tuple[str, str]],
) -> HydrationResult:
    if (repo_url, commit) not in allowed_pairs:
        return HydrationResult(False, error="repo URL/commit pair is not allowlisted")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    commands: list[dict[str, Any]] = []

    def execute(args: list[str], cwd: Path | None = None) -> bool:
        rc, stdout, stderr = run_git(args, cwd)
        commands.append({
            "command": ["git", *args],
            "cwd": str(cwd or Path.cwd()),
            "returncode": rc,
            "stdout_tail": stdout[-1000:],
            "stderr_tail": stderr[-1000:],
        })
        return rc == 0

    if not (cache_path / ".git").is_dir():
        cache_path.mkdir(parents=True, exist_ok=True)
        if not execute(["init"], cache_path):
            return HydrationResult(False, commands=commands, error="git init failed")
        if not execute(["remote", "add", "origin", repo_url], cache_path):
            return HydrationResult(False, commands=commands, error="git remote add failed")
    else:
        rc, existing_url, _ = run_git(["remote", "get-url", "origin"], cache_path)
        if rc != 0 or existing_url.strip().rstrip("/").removesuffix(".git") != repo_url.rstrip("/").removesuffix(".git"):
            return HydrationResult(False, commands=commands, error="existing cache origin does not match pinned repo")

    if not execute(["fetch", "--depth", "1", "origin", commit], cache_path):
        return HydrationResult(False, commands=commands, error="exact pinned commit fetch failed")
    if not execute(["checkout", "--detach", commit], cache_path):
        return HydrationResult(False, commands=commands, error="exact pinned commit checkout failed")
    rc, actual, stderr = run_git(["rev-parse", "HEAD"], cache_path)
    commands.append({
        "command": ["git", "rev-parse", "HEAD"],
        "cwd": str(cache_path),
        "returncode": rc,
        "stdout_tail": actual[-1000:],
        "stderr_tail": stderr[-1000:],
    })
    if rc != 0:
        return HydrationResult(False, commands=commands, error="unable to read hydrated commit")
    actual_commit = actual.strip()
    return HydrationResult(
        actual_commit == commit,
        actual_commit=actual_commit,
        commands=commands,
        error="" if actual_commit == commit else "hydrated commit does not match expected commit",
    )


def load_snippets(snippet_dir: Path) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    snippets: dict[str, dict[str, Any]] = {}
    scanned: list[str] = []
    notes: list[str] = []
    if not snippet_dir.is_dir():
        notes.append(f"missing snippet directory: {snippet_dir}")
        return snippets, scanned, notes
    for path in sorted(snippet_dir.glob("*.json")):
        scanned.append(str(path))
        try:
            value = load_object(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            notes.append(f"ignored malformed snippet record {path}: {exc}")
            continue
        row_id = str(value.get("row_id", ""))
        if row_id:
            value["_path"] = str(path)
            snippets[row_id] = value
    return snippets, scanned, notes


def verify_rows(
    rows: list[dict[str, Any]],
    snippets: dict[str, dict[str, Any]],
    cache_path: Path,
    expected_commit: str,
    actual_commit: str,
    *,
    hydration_error: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    ledger_rows: list[dict[str, Any]] = []
    file_rows: dict[str, dict[str, Any]] = {}
    verified_snippets: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()

    for source_row in rows:
        row_id = str(source_row.get("row_id", ""))
        file_path = str(source_row.get("file_path", ""))
        snippet = snippets.get(row_id)
        status = SOURCE_HYDRATION_UNCLASSIFIED
        reason = ""
        occurrence_count = 0
        line_start: int | None = None
        line_end: int | None = None
        cached_file = cache_path / file_path

        if hydration_error:
            status = SOURCE_HYDRATION_FAILED
            reason = hydration_error
        elif actual_commit != expected_commit:
            status = SOURCE_HYDRATED_COMMIT_MISMATCH
            reason = f"expected {expected_commit}, found {actual_commit}"
        elif not cached_file.is_file():
            status = SOURCE_HYDRATED_FILE_MISSING
            reason = "expected source file is missing from hydrated checkout"
        elif snippet is None:
            status = SOURCE_HYDRATION_FAILED
            reason = "checked-in snippet record is missing"
        else:
            source_snippet = str(snippet.get("source_snippet", ""))
            patch_snippet = str(snippet.get("patch_snippet", ""))
            expected_source_hash = str(source_row.get("source_snippet_sha256", ""))
            expected_patch_hash = str(source_row.get("patch_snippet_sha256", ""))
            if (
                sha256_text(source_snippet) != expected_source_hash
                or str(snippet.get("source_snippet_sha256", "")) != expected_source_hash
                or (patch_snippet and sha256_text(patch_snippet) != expected_patch_hash)
                or (patch_snippet and str(snippet.get("patch_snippet_sha256", "")) != expected_patch_hash)
            ):
                status = SOURCE_HYDRATED_SNIPPET_HASH_MISMATCH
                reason = "source or patch snippet hash differs from checked-in registration evidence"
            else:
                source_text = cached_file.read_text(encoding="utf-8")
                occurrence_count = source_text.count(source_snippet)
                if occurrence_count == 0:
                    status = SOURCE_HYDRATED_SNIPPET_NOT_FOUND
                    reason = "expected source snippet was not found"
                elif occurrence_count > 1:
                    status = SOURCE_HYDRATED_SNIPPET_AMBIGUOUS
                    reason = "expected source snippet occurs more than once"
                else:
                    offset = source_text.index(source_snippet)
                    line_start = source_text.count("\n", 0, offset) + 1
                    line_end = line_start + source_snippet.count("\n")
                    status = SOURCE_HYDRATED_VERIFIED
                    reason = "pinned file and exact source/patch snippet hashes verified"

        counts[status] += 1
        ledger_rows.append({
            "row_id": row_id,
            "file_path": file_path,
            "status": status,
            "reason": reason,
            "expected_commit": expected_commit,
            "actual_commit": actual_commit,
            "absolute_cached_file_path": str(cached_file.resolve()),
        })
        verified_snippets.append({
            "row_id": row_id,
            "file_path": file_path,
            "source_snippet_sha256": str(source_row.get("source_snippet_sha256", "")),
            "patch_snippet_sha256": str(source_row.get("patch_snippet_sha256", "")),
            "source_snippet_occurrence_count": occurrence_count,
            "source_snippet_line_start": line_start,
            "source_snippet_line_end": line_end,
            "status": status,
        })
        if cached_file.is_file():
            key = str(cached_file.resolve())
            if key not in file_rows:
                file_rows[key] = {
                    "file_path": file_path,
                    "absolute_cached_file_path": key,
                    "sha256": sha256_file(cached_file),
                    "size_bytes": cached_file.stat().st_size,
                    "row_ids": [],
                }
            file_rows[key]["row_ids"].append(row_id)

    ledger_rows.sort(key=lambda row: row["row_id"])
    verified_snippets.sort(key=lambda row: row["row_id"])
    files = sorted(file_rows.values(), key=lambda row: row["file_path"])
    stable_counts = {category: counts.get(category, 0) for category in CATEGORIES}
    return ledger_rows, files, verified_snippets, stable_counts


def empty_outputs(
    plan_path: Path,
    note: str,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    counts = {category: 0 for category in CATEGORIES}
    summary = make_summary("", "", "", [], counts)
    ledger = {
        "version": VERSION,
        "rows": [],
        "category_counts": counts,
        "repo_url": "",
        "commit": "",
        "actual_commit": "",
        "controlled_cache_path": "",
        "hydration_command_summary": [],
        "scanned_paths": [str(plan_path)],
        "notes": [note],
    }
    return summary, ledger, [], []


def make_summary(
    repo_url: str,
    commit: str,
    cache_path: str,
    row_ids: list[str],
    category_counts: dict[str, int],
) -> dict[str, Any]:
    verified = category_counts.get(SOURCE_HYDRATED_VERIFIED, 0)
    return {
        "version": VERSION,
        "status": STATUS,
        "repo_url": repo_url,
        "commit": commit,
        "controlled_cache_path": cache_path,
        "hydrated_row_count": len(row_ids),
        "source_hydrated_verified_count": verified,
        "blocked_count": len(row_ids) - verified,
        "category_counts": category_counts,
        "row_ids": sorted(row_ids),
        "bounded_claim": "the pinned source checkout was hydrated and the expected source snippets were verified against checked-in hashes",
        "does_not_claim": [
            "Lean replay success",
            "dependency hydration",
            "proof checking",
            "new proof discovery",
            "general SorryDB mining",
            "arbitrary proof repair",
            "upstream submission",
        ],
        "next_frontier": "v4.4.7 rerun missing-manifest backfill planning against the controlled hydrated source cache",
    }


def execute_hydration(
    plan_path: Path,
    *,
    plan_summary_path: Path | None,
    fixture_plan_path: Path | None,
    snippet_dir: Path,
    cache_root: Path,
    allowed_pairs: set[tuple[str, str]],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    if not plan_path.exists():
        return empty_outputs(plan_path, f"missing registration plan: {plan_path}")
    try:
        plan = load_object(plan_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return empty_outputs(plan_path, f"malformed registration plan: {exc}")

    rows = [
        row for row in plan.get("rows", [])
        if isinstance(row, dict) and row.get("registration_status") == "REGISTRATION_NEEDS_NETWORK_HYDRATION"
    ]
    pairs = {(str(row.get("repo_url", "")), str(row.get("commit", ""))) for row in rows}
    scanned_paths = [str(plan_path)]
    if plan_summary_path is not None:
        scanned_paths.append(str(plan_summary_path))
    if fixture_plan_path is not None:
        scanned_paths.append(str(fixture_plan_path))
    snippets, snippet_paths, notes = load_snippets(snippet_dir)
    scanned_paths.extend(snippet_paths)

    if len(pairs) != 1:
        counts = {category: 0 for category in CATEGORIES}
        counts[SOURCE_HYDRATION_BLOCKED_REPO_IDENTITY] = len(rows)
        summary = make_summary("", "", "", [str(row.get("row_id", "")) for row in rows], counts)
        ledger_rows = [{
            "row_id": str(row.get("row_id", "")),
            "file_path": str(row.get("file_path", "")),
            "status": SOURCE_HYDRATION_BLOCKED_REPO_IDENTITY,
            "reason": "registration plan must contain exactly one repo URL/commit pair",
            "expected_commit": str(row.get("commit", "")),
            "actual_commit": "",
            "absolute_cached_file_path": "",
        } for row in rows]
        ledger = {
            "version": VERSION,
            "rows": ledger_rows,
            "category_counts": counts,
            "repo_url": "",
            "commit": "",
            "actual_commit": "",
            "controlled_cache_path": "",
            "hydration_command_summary": [],
            "scanned_paths": sorted(dict.fromkeys(scanned_paths)),
            "notes": notes + ["hydration refused because repo identity was not singular"],
        }
        return summary, ledger, [], []

    repo_url, commit = next(iter(pairs))
    cache_path = cache_root / cache_name(repo_url, commit)
    hydration = hydrate_repository(repo_url, commit, cache_path, allowed_pairs=allowed_pairs)
    ledger_rows, files, verified, counts = verify_rows(
        rows,
        snippets,
        cache_path,
        commit,
        hydration.actual_commit,
        hydration_error=hydration.error if not hydration.success and not hydration.actual_commit else "",
    )
    summary = make_summary(
        repo_url,
        commit,
        str(cache_path.resolve()),
        [str(row.get("row_id", "")) for row in rows],
        counts,
    )
    ledger = {
        "version": VERSION,
        "rows": ledger_rows,
        "category_counts": counts,
        "repo_url": repo_url,
        "commit": commit,
        "actual_commit": hydration.actual_commit,
        "controlled_cache_path": str(cache_path.resolve()),
        "hydration_command_summary": hydration.commands,
        "scanned_paths": sorted(dict.fromkeys(scanned_paths)),
        "notes": notes + [
            "only the exact allowlisted repo URL and commit were fetched",
            "no Lean, Lake, build, dependency hydration, replay, or proof checking was run",
            "the full source checkout remains ignored and is not committed",
        ],
    }
    return summary, ledger, files, verified


def write_outputs(
    output_dir: Path,
    summary: dict[str, Any],
    ledger: dict[str, Any],
    files: list[dict[str, Any]],
    verified: list[dict[str, Any]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads: tuple[tuple[str, Any], ...] = (
        ("summary.json", summary),
        ("source_hydration_ledger.json", ledger),
        ("file_hashes.json", files),
        ("verified_snippets.json", verified),
    )
    for name, payload in payloads:
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def main() -> int:
    summary, ledger, files, verified = execute_hydration(
        DEFAULT_PLAN,
        plan_summary_path=DEFAULT_PLAN_SUMMARY,
        fixture_plan_path=DEFAULT_FIXTURE_PLAN,
        snippet_dir=DEFAULT_SNIPPET_DIR,
        cache_root=DEFAULT_CACHE_ROOT,
        allowed_pairs={(PINNED_REPO_URL, PINNED_COMMIT)},
    )
    write_outputs(DEFAULT_OUTPUT_DIR, summary, ledger, files, verified)
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
