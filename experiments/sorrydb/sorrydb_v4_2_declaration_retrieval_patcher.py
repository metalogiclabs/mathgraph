#!/usr/bin/env python3
"""SorryDB v4.2.1 cache-safe declaration-retrieval replay harness."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import tempfile
import time
from typing import Any, Iterable

BANNER = "MATHGRAPH x SORRYDB v4.2.1 — CACHE-SAFE DECLARATION-RETRIEVAL PATCHER"
ACCEPTED_EXACT_LINE = "ACCEPTED_EXACT_LINE"
ACCEPTED_BUT_ALIGNMENT_AMBIGUOUS = "ACCEPTED_BUT_ALIGNMENT_AMBIGUOUS"
OBSTRUCTED_NO_INPUT_RECORDS = "OBSTRUCTED_NO_INPUT_RECORDS"
OBSTRUCTED_NO_REPLAYABLE_TARGETS = "OBSTRUCTED_NO_REPLAYABLE_TARGETS"
OBSTRUCTED_DISK_PRESSURE = "OBSTRUCTED_DISK_PRESSURE"
OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY = "OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY"
OBSTRUCTED_BASELINE_TIMEOUT = "OBSTRUCTED_BASELINE_TIMEOUT"
OBSTRUCTED_BASELINE_COMPILE_FAILURE = "OBSTRUCTED_BASELINE_COMPILE_FAILURE"
OBSTRUCTED_UNSAFE_REPLAY_COMMAND = "OBSTRUCTED_UNSAFE_REPLAY_COMMAND"
OBSTRUCTED_REPO_NOT_CACHED = "OBSTRUCTED_REPO_NOT_CACHED"
REPLAY_MANIFEST_WRITTEN = "REPLAY_MANIFEST_WRITTEN"
INTERRUPTED_PARTIAL_RUN = "INTERRUPTED_PARTIAL_RUN"
LAWBOOK_ACCEPTED_PATCH_EXISTS = "LAWBOOK_ACCEPTED_PATCH_EXISTS"
OBSTRUCTED_NO_EXACT_LINE_PATCH = "OBSTRUCTED_NO_EXACT_LINE_PATCH"
GIB = 1024**3
FORBIDDEN_RE = re.compile(r"\b(sorry|admit|axiom|unsafe)\b")
DECL_RE = re.compile(
    r"^\s*(theorem|lemma|def|abbrev|example|structure|inductive)\s+"
    r"([A-Za-z_][A-Za-z0-9_'.]*)?"
)
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*|[∀∃→↔=<>≤≥+*/^-]+")


# dataclass SorryTarget
@dataclass
class SorryTarget:
    repo: str
    file_path: str
    line: int
    commit: str = ""
    lean_version: str = ""
    statement: str = ""
    context: str = ""
    source_path: str = ""
    local_repo_path: str = ""
    build_command: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


# dataclass DeclarationCandidate
@dataclass
class DeclarationCandidate:
    name: str
    kind: str
    line: int
    signature: str
    namespace: str = ""
    score: float = 0.0


# dataclass PatchAttempt
@dataclass
class PatchAttempt:
    repo: str
    file_path: str
    line: int
    patch: str
    candidate_name: str
    classification: str
    return_code: int | None
    elapsed_seconds: float
    aligned_line: int | None = None
    stdout: str = ""
    stderr: str = ""
    timeout_reason: str = ""


@dataclass
class ProcessResult:
    return_code: int | None
    stdout: str
    stderr: str
    elapsed_seconds: float
    timed_out: bool = False
    timeout_reason: str = ""


@dataclass
class BaselineResult:
    classification: str
    process: ProcessResult
    command: list[str] = field(default_factory=list)


# dataclass RunSummary
@dataclass
class RunSummary:
    total_records_loaded: int = 0
    targets_selected: int = 0
    focus_repo_counts: dict[str, int] = field(default_factory=dict)
    declaration_candidates_extracted: int = 0
    patch_attempts: int = 0
    accepted_exact_line_patches: int = 0
    accepted_ambiguous_patches: int = 0
    rejected_counts_by_reason: dict[str, int] = field(default_factory=dict)
    obstructions_by_reason: dict[str, int] = field(default_factory=dict)
    best_examples: list[dict[str, Any]] = field(default_factory=list)
    free_gb: dict[str, float] = field(default_factory=dict)
    required_gb: float = 15.0
    checked_paths: list[str] = field(default_factory=list)
    completed_targets: int = 0
    completed_attempts: int = 0
    repo_copy_strategy: str = "one_copy_per_replayable_target_after_preflight_and_baseline"
    cache_get_allowed: bool = False
    replay_manifest_rows: int = 0
    repo_cache_root: str = ""
    dry_run_manifest_enabled: bool = False
    repo_cache_hits: int = 0
    repo_cache_misses: int = 0
    source_hits: int = 0
    source_misses: int = 0
    verdict: str = OBSTRUCTED_NO_INPUT_RECORDS


def first_value(record: dict[str, Any], keys: Iterable[str], default: Any = "") -> Any:
    for key in keys:
        value: Any = record
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                value = None
                break
            value = value[part]
        if value not in (None, ""):
            return value
    return default


def defensive_target(record: dict[str, Any]) -> SorryTarget:
    line_raw = first_value(
        record,
        ["line", "line_number", "target_line", "location.start_line", "location.line"],
        0,
    )
    try:
        line = int(line_raw)
    except (TypeError, ValueError):
        line = 0
    return SorryTarget(
        repo=str(
            first_value(
                record,
                ["repo.remote", "repository.remote", "repo_url", "repository", "repo_name", "project", "repo"],
                "",
            )
        ),
        file_path=str(first_value(record, ["file", "file_path", "path", "location.path", "location.file"], "")),
        line=line,
        commit=str(first_value(record, ["repo.commit", "repository.commit", "commit", "revision"], "")),
        lean_version=str(first_value(record, ["repo.lean_version", "repository.lean_version", "lean_version"], "")),
        statement=str(
            first_value(
                record,
                ["statement", "theorem", "declaration", "goal", "debug_info.goal", "target"],
                "",
            )
        ),
        context=str(first_value(record, ["context", "local_context", "prefix", "source_context"], "")),
        source_path=str(first_value(record, ["source_path", "absolute_path", "local_file"], "")),
        local_repo_path=str(first_value(record, ["local_repo_path", "repo_path", "checkout", "root"], "")),
        build_command=str(first_value(record, ["build_command", "lean_command", "command"], "")),
        raw=record,
    )


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    try:
        value = json.loads(text)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
        if isinstance(value, dict):
            for key in ("sorries", "records", "items", "targets"):
                if isinstance(value.get(key), list):
                    return [x for x in value[key] if isinstance(x, dict)]
            return [value]
    except json.JSONDecodeError:
        records = []
        for line in text.splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                records.append(value)
        return records
    return []


def repo_focus_matches(repo: str, focus_value: str) -> bool:
    repo_folded = repo.strip().rstrip("/").removesuffix(".git").casefold()
    focus_folded = focus_value.strip().rstrip("/").removesuffix(".git").casefold()
    if not focus_folded:
        return True
    repo_name = repo_folded.rsplit("/", 1)[-1]
    focus_name = focus_folded.rsplit("/", 1)[-1]
    return (
        focus_folded in repo_folded
        or repo_folded in focus_folded
        or focus_name == repo_name
    )


def target_matches_focus(target: SorryTarget, focus: list[str]) -> bool:
    return not focus or any(repo_focus_matches(target.repo, value) for value in focus)


def focus_rank(target: SorryTarget, focus: list[str]) -> int:
    for index, value in enumerate(focus):
        if repo_focus_matches(target.repo, value):
            return index
    return len(focus)


def nearest_existing_path(path: Path) -> Path:
    candidate = path.expanduser()
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def disk_preflight(paths: Iterable[Path], required_gb: float) -> tuple[bool, dict[str, float], list[str]]:
    free_gb: dict[str, float] = {}
    checked_paths: list[str] = []
    safe = True
    for raw_path in paths:
        display = str(raw_path.expanduser())
        checked_paths.append(display)
        check_path = nearest_existing_path(raw_path)
        try:
            free = shutil.disk_usage(check_path).free / GIB
        except OSError:
            free = 0.0
        free_gb[display] = round(free, 3)
        if free < required_gb:
            safe = False
    return safe, free_gb, checked_paths


def safe_repo_cache_key(repo: str, commit: str) -> str:
    cleaned = repo.strip().rstrip("/").removesuffix(".git")
    parts = cleaned.split("/")
    if len(parts) >= 2:
        owner_repo = "__".join(parts[-2:])
    else:
        owner_repo = cleaned or "unknown_repo"
    owner_repo = re.sub(r"[^A-Za-z0-9_.-]+", "_", owner_repo)
    commit_part = re.sub(r"[^A-Za-z0-9_.-]+", "_", (commit or "unknown_commit"))[:12]
    return f"{owner_repo}__{commit_part}"


def expected_repo_cache_path(repo_cache_root: Path, target: SorryTarget) -> Path:
    return repo_cache_root.expanduser() / safe_repo_cache_key(target.repo, target.commit)


def build_manifest_row(target: SorryTarget, repo_cache_root: Path) -> dict[str, Any]:
    repo_path = expected_repo_cache_path(repo_cache_root, target)
    source_path = repo_path / target.file_path if target.file_path else repo_path
    repo_cached = repo_path.exists()
    source_exists = source_path.exists()
    if not repo_cached:
        obstruction = OBSTRUCTED_REPO_NOT_CACHED
    elif not source_exists:
        obstruction = "OBSTRUCTED_MISSING_FILE"
    else:
        obstruction = "NONE"
    return {
        "repo": target.repo,
        "commit": target.commit,
        "lean_version": target.lean_version,
        "file_path": target.file_path,
        "line": target.line,
        "statement": target.statement,
        "expected_repo_cache_path": str(repo_path),
        "expected_source_path": str(source_path),
        "repo_cached": repo_cached,
        "source_exists": source_exists,
        "obstruction": obstruction,
    }


def write_replay_manifest(output: Path, rows: list[dict[str, Any]]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with (output / "replay_manifest.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def symbolic_tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text) if len(token) > 1}


def extract_declarations(text: str) -> list[DeclarationCandidate]:
    lines = text.splitlines()
    namespace_stack: list[str] = []
    candidates: list[DeclarationCandidate] = []
    for index, line in enumerate(lines):
        ns = re.match(r"^\s*namespace\s+([A-Za-z_][A-Za-z0-9_.']*)", line)
        if ns:
            namespace_stack.append(ns.group(1))
            continue
        if re.match(r"^\s*end(?:\s|$)", line) and namespace_stack:
            namespace_stack.pop()
            continue
        match = DECL_RE.match(line)
        if not match:
            continue
        kind = match.group(1)
        name = match.group(2) or f"example_at_{index + 1}"
        snippet = [line.strip()]
        for follow in lines[index + 1 : min(len(lines), index + 8)]:
            if DECL_RE.match(follow):
                break
            snippet.append(follow.strip())
            if ":=" in follow or re.search(r"\bwhere\b|:=\s*by|:\s*.*:=", follow):
                break
        candidates.append(
            DeclarationCandidate(
                name=name,
                kind=kind,
                line=index + 1,
                signature=" ".join(part for part in snippet if part),
                namespace=".".join(namespace_stack),
            )
        )
    return candidates


def score_declaration(target: SorryTarget, candidate: DeclarationCandidate) -> float:
    target_tokens = symbolic_tokens(target.statement + " " + target.context)
    candidate_tokens = symbolic_tokens(candidate.name + " " + candidate.signature)
    overlap = len(target_tokens & candidate_tokens)
    union = max(1, len(target_tokens | candidate_tokens))
    score = 10.0 * overlap / union
    if target.line and candidate.line:
        score += 3.0 / (1.0 + abs(target.line - candidate.line) / 20.0)
    if candidate.namespace:
        score += 0.5
    if candidate.kind in {"theorem", "lemma"}:
        score += 1.0
    return score


def retrieve_declarations(target: SorryTarget, text: str, top_k: int = 8) -> list[DeclarationCandidate]:
    candidates = extract_declarations(text)
    for candidate in candidates:
        candidate.score = score_declaration(target, candidate)
    return sorted(candidates, key=lambda item: (-item.score, abs(item.line - target.line)))[:top_k]


def generate_patch_templates(candidate: DeclarationCandidate, text: str) -> list[str]:
    names = [candidate.name]
    if candidate.namespace and candidate.name != f"{candidate.namespace}.{candidate.name}":
        names.append(f"{candidate.namespace}.{candidate.name}")
    patches: list[str] = []
    for name in names:
        patches.extend([
            f"by\n  exact {name}",
            f"by\n  simpa using {name}",
            f"by\n  exact by simpa using {name}",
            f"by\n  apply {name}",
        ])
    patches.extend(["by\n  constructor <;> assumption", "by\n  trivial", "by\n  simp"])
    if "aesop" in text.lower():
        patches.append("by\n  aesop")
    if "omega" in text.lower():
        patches.append("by\n  omega")
    if "norm_num" in text.lower():
        patches.append("by\n  norm_num")
    return list(dict.fromkeys(patches))


def resolve_paths(target: SorryTarget) -> tuple[Path | None, Path | None]:
    source = Path(target.source_path).expanduser() if target.source_path else None
    repo = Path(target.local_repo_path).expanduser() if target.local_repo_path else None
    if source and source.exists():
        if repo is None:
            repo = source.parent
        return source, repo
    if repo and target.file_path:
        candidate = repo / target.file_path
        if candidate.exists():
            return candidate, repo
    path = Path(target.file_path).expanduser() if target.file_path else None
    if path and path.is_absolute() and path.exists():
        return path, repo or path.parent
    return None, repo


def find_sorry_line(lines: list[str], recorded_line: int) -> tuple[int | None, bool]:
    center = max(0, recorded_line - 1)
    nearby = [i for i in range(max(0, center - 3), min(len(lines), center + 4)) if re.search(r"\bsorry\b", lines[i])]
    if not nearby:
        return None, False
    exact = center in nearby
    if exact:
        return center, len(nearby) == 1
    return min(nearby, key=lambda i: abs(i - center)), len(nearby) == 1


def replace_sorry_at_line(text: str, recorded_line: int, patch: str) -> tuple[str | None, int | None, bool]:
    lines = text.splitlines(keepends=True)
    index, unambiguous = find_sorry_line([line.rstrip("\n") for line in lines], recorded_line)
    if index is None:
        return None, None, False
    original = lines[index]
    match = re.search(r"\bsorry\b", original)
    if not match:
        return None, None, False
    indent = original[: len(original) - len(original.lstrip())]
    replacement = patch.replace("\n", "\n" + indent)
    lines[index] = original[: match.start()] + replacement + original[match.end() :]
    return "".join(lines), index + 1, unambiguous and index + 1 == recorded_line


def choose_command(target: SorryTarget, repo_root: Path, file_path: Path) -> list[str] | None:
    if target.build_command:
        return ["sh", "-lc", target.build_command]
    relative = file_path.relative_to(repo_root) if file_path.is_relative_to(repo_root) else file_path
    if (repo_root / "lakefile.lean").exists() or (repo_root / "lakefile.toml").exists():
        return ["lake", "env", "lean", str(relative)]
    return None


def command_safety_obstruction(command: list[str], allow_cache_get: bool) -> str | None:
    rendered = " ".join(command).casefold()
    if re.search(r"\blake\s+update\b", rendered):
        return OBSTRUCTED_UNSAFE_REPLAY_COMMAND
    if re.search(r"\blake\s+exe\s+cache\s+get\b", rendered) and not allow_cache_get:
        return OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY
    return None


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def kill_process_group(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        process.kill()


def run_command(command: list[str], cwd: Path, timeout: int) -> ProcessResult:
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return ProcessResult(
                process.returncode,
                _text(stdout),
                _text(stderr),
                time.monotonic() - started,
            )
        except subprocess.TimeoutExpired as exc:
            kill_process_group(process)
            stdout, stderr = process.communicate()
            return ProcessResult(
                None,
                _text(exc.stdout) + _text(stdout),
                _text(exc.stderr) + _text(stderr),
                time.monotonic() - started,
                True,
                f"process group exceeded {timeout}s and was killed",
            )
        except KeyboardInterrupt:
            kill_process_group(process)
            process.communicate()
            raise
    except subprocess.TimeoutExpired as exc:
        return ProcessResult(
            None,
            _text(exc.stdout),
            _text(exc.stderr),
            time.monotonic() - started,
            True,
            f"process group exceeded {timeout}s and was killed",
        )
    except OSError as exc:
        return ProcessResult(None, "", str(exc), time.monotonic() - started)


def classify_result(return_code: int | None, stdout: str, stderr: str, timed_out: bool = False) -> str:
    if timed_out:
        return "REJECTED_TIMEOUT"
    if return_code == 0:
        return ACCEPTED_EXACT_LINE
    text = (stdout + "\n" + stderr).lower()
    if "unknown identifier" in text or "unknown constant" in text or "invalid field" in text:
        return "REJECTED_UNKNOWN_IDENTIFIER_OR_SCOPE"
    if "unsolved goals" in text or "no goals to be solved" in text:
        return "REJECTED_UNSOLVED_GOALS"
    if "type mismatch" in text or "application type mismatch" in text:
        return "REJECTED_TYPE_MISMATCH"
    if "unknown module" in text or "build failed" in text or "could not resolve import" in text:
        return "REJECTED_IMPORT_OR_BUILD_BOUNDARY"
    return "REJECTED_OTHER"


def check_baseline(
    target: SorryTarget,
    source: Path,
    repo_root: Path,
    timeout: int,
    allow_cache_get: bool,
) -> BaselineResult:
    command = choose_command(target, repo_root, source)
    if command is None:
        return BaselineResult(
            "OBSTRUCTED_NO_BUILD_COMMAND",
            ProcessResult(None, "", "No safe baseline build command was resolved.", 0.0),
        )
    safety = command_safety_obstruction(command, allow_cache_get)
    if safety:
        return BaselineResult(
            safety,
            ProcessResult(None, "", "Replay command rejected by v4.2.1 safety policy.", 0.0),
            command,
        )
    process = run_command(command, repo_root, timeout)
    if process.timed_out:
        classification = OBSTRUCTED_BASELINE_TIMEOUT
    elif process.return_code != 0 and not allow_cache_get:
        classification = OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY
    elif process.return_code != 0:
        classification = OBSTRUCTED_BASELINE_COMPILE_FAILURE
    else:
        classification = "BASELINE_PASSED"
    return BaselineResult(classification, process, command)


def replay_patch_in_workspace(
    target: SorryTarget,
    original: str,
    copied_root: Path,
    copied_file: Path,
    command: list[str],
    patch: str,
    candidate_name: str,
    timeout: int,
) -> PatchAttempt:
    patched, aligned_line, aligned = replace_sorry_at_line(original, target.line, patch)
    if patched is None:
        return PatchAttempt(target.repo, target.file_path, target.line, patch, candidate_name, "ACCEPTED_BUT_ALIGNMENT_AMBIGUOUS", None, 0.0)
    before_count = len(FORBIDDEN_RE.findall(original))
    after_count = len(FORBIDDEN_RE.findall(patched))
    try:
        copied_file.write_text(patched, encoding="utf-8")
        result = run_command(command, copied_root, timeout)
    finally:
        copied_file.write_text(original, encoding="utf-8")
    classification = classify_result(
        result.return_code,
        result.stdout,
        result.stderr,
        result.timed_out,
    )
    if classification == ACCEPTED_EXACT_LINE:
        if not aligned or after_count != before_count - 1:
            classification = ACCEPTED_BUT_ALIGNMENT_AMBIGUOUS
    return PatchAttempt(
        target.repo,
        target.file_path,
        target.line,
        patch,
        candidate_name,
        classification,
        result.return_code,
        result.elapsed_seconds,
        aligned_line,
        result.stdout[-4000:],
        result.stderr[-4000:],
        result.timeout_reason,
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def increment(mapping: dict[str, int], key: str) -> None:
    mapping[key] = mapping.get(key, 0) + 1


def write_reports(output: Path, summary: RunSummary, attempts: list[PatchAttempt]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    accepted = [asdict(a) for a in attempts if a.classification == ACCEPTED_EXACT_LINE]
    obstructions = {k: v for k, v in summary.obstructions_by_reason.items()}
    (output / "run_summary.json").write_text(json.dumps(asdict(summary), indent=2) + "\n")
    write_jsonl(output / "accepted_patches.jsonl", accepted)
    write_jsonl(output / "attempts.jsonl", (asdict(a) for a in attempts))
    (output / "obstruction_summary.json").write_text(json.dumps(obstructions, indent=2) + "\n")
    write_jsonl(output / "lawbook_candidates.jsonl", accepted)
    (output / "README.md").write_text(
        "# SorryDB v4.2.1 cache-safe replay run\n\n"
        f"Verdict: `{summary.verdict}`\n\n"
        "Only `ACCEPTED_EXACT_LINE` attempts are Lawbook candidates. Historical replay "
        "must preserve the recorded commit, manifest, and Lean toolchain. `lake update` "
        "is forbidden because it changes the replay environment.\n"
    )


def finalize_interrupted_run(
    output: Path,
    summary: RunSummary,
    attempts: list[PatchAttempt],
) -> None:
    summary.verdict = INTERRUPTED_PARTIAL_RUN
    summary.completed_attempts = summary.patch_attempts
    increment(summary.obstructions_by_reason, INTERRUPTED_PARTIAL_RUN)
    write_reports(output, summary, attempts)


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def main() -> int:
    print(BANNER)
    work_root = Path(
        os.getenv(
            "SORRYDB_V421_WORK_ROOT",
            os.getenv("SORRYDB_V42_WORK_ROOT", "/tmp/mathgraph_sorrydb_v4_2_1"),
        )
    )
    records_path = Path(
        os.getenv(
            "SORRYDB_V421_RECORDS_PATH",
            os.getenv("SORRYDB_V42_RECORDS_PATH", str(work_root / "sorrydb_records.jsonl")),
        )
    )
    max_records = int(
        os.getenv("SORRYDB_V421_MAX_RECORDS", os.getenv("SORRYDB_V42_MAX_RECORDS", "40"))
    )
    focus = [
        x.strip()
        for x in os.getenv(
            "SORRYDB_V421_FOCUS_REPOS",
            os.getenv("SORRYDB_V42_FOCUS_REPOS", "LeanLangur,LeanLion,MetaExamples"),
        ).split(",")
        if x.strip()
    ]
    timeout = int(
        os.getenv(
            "SORRYDB_V421_TIMEOUT_SECONDS",
            os.getenv("SORRYDB_V42_TIMEOUT_SECONDS", "90"),
        )
    )
    required_gb = float(os.getenv("SORRYDB_V421_MIN_FREE_GB", "15"))
    allow_cache_get = env_flag("SORRYDB_V421_ALLOW_CACHE_GET")
    dry_run_manifest = env_flag("SORRYDB_V422_DRY_RUN_MANIFEST")
    repo_cache_root = Path(os.getenv("SORRYDB_V422_REPO_CACHE_ROOT", str(work_root / "repo_cache")))
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = (
        work_root
        / "artifacts"
        / "runs"
        / "sorrydb_v4_2_1_cache_safe_replay_preflight"
        / timestamp
    )
    records = load_records(records_path)
    summary = RunSummary(
        total_records_loaded=len(records),
        required_gb=required_gb,
        cache_get_allowed=allow_cache_get,
        dry_run_manifest_enabled=dry_run_manifest,
        repo_cache_root=str(repo_cache_root),
    )
    attempts: list[PatchAttempt] = []
    if not records:
        summary.verdict = OBSTRUCTED_NO_INPUT_RECORDS
        increment(summary.obstructions_by_reason, OBSTRUCTED_NO_INPUT_RECORDS)
        write_reports(output, summary, attempts)
        print(json.dumps(asdict(summary), indent=2))
        return 0

    cache_path = Path(os.getenv("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    safe_disk, free_gb, checked_paths = disk_preflight(
        [work_root, Path.home(), cache_path],
        required_gb,
    )
    summary.free_gb = free_gb
    summary.checked_paths = checked_paths
    if not safe_disk:
        summary.verdict = OBSTRUCTED_DISK_PRESSURE
        increment(summary.obstructions_by_reason, OBSTRUCTED_DISK_PRESSURE)
        write_reports(output, summary, attempts)
        print(json.dumps(asdict(summary), indent=2))
        return 0

    targets = [defensive_target(record) for record in records]
    targets.sort(
        key=lambda target: (
            focus_rank(target, focus),
            target.repo,
            target.file_path,
            target.line,
        )
    )
    targets = [target for target in targets if target_matches_focus(target, focus)][:max_records]
    summary.targets_selected = len(targets)
    if not targets:
        summary.verdict = OBSTRUCTED_NO_REPLAYABLE_TARGETS
        write_reports(output, summary, attempts)
        print(json.dumps(asdict(summary), indent=2))
        return 0

    if dry_run_manifest:
        manifest_rows = []
        for target in targets:
            increment(summary.focus_repo_counts, target.repo or "UNKNOWN")
            row = build_manifest_row(target, repo_cache_root)
            manifest_rows.append(row)
            if row["repo_cached"]:
                summary.repo_cache_hits += 1
            else:
                summary.repo_cache_misses += 1
            if row["source_exists"]:
                summary.source_hits += 1
            else:
                summary.source_misses += 1
            if row["obstruction"] != "NONE":
                increment(summary.obstructions_by_reason, row["obstruction"])
            summary.completed_targets += 1
        summary.replay_manifest_rows = len(manifest_rows)
        summary.verdict = REPLAY_MANIFEST_WRITTEN if manifest_rows else OBSTRUCTED_NO_REPLAYABLE_TARGETS
        write_replay_manifest(output, manifest_rows)
        write_reports(output, summary, attempts)
        print(json.dumps(asdict(summary), indent=2))
        return 0

    baseline_cache: dict[tuple[str, str, str], BaselineResult] = {}
    try:
        for target in targets:
            increment(summary.focus_repo_counts, target.repo or "UNKNOWN")
            source, repo_root = resolve_paths(target)
            if source is None or not source.exists():
                increment(summary.obstructions_by_reason, "OBSTRUCTED_MISSING_FILE")
                summary.completed_targets += 1
                continue
            if repo_root is None or not repo_root.exists():
                increment(summary.obstructions_by_reason, "OBSTRUCTED_NO_BUILD_COMMAND")
                summary.completed_targets += 1
                continue

            cache_key = (
                str(repo_root.resolve()),
                str(source.resolve()),
                target.build_command,
            )
            baseline = baseline_cache.get(cache_key)
            if baseline is None:
                baseline = check_baseline(
                    target,
                    source,
                    repo_root,
                    timeout,
                    allow_cache_get,
                )
                baseline_cache[cache_key] = baseline
            if baseline.classification != "BASELINE_PASSED":
                increment(summary.obstructions_by_reason, baseline.classification)
                summary.completed_targets += 1
                continue

            text = source.read_text(encoding="utf-8")
            candidates = retrieve_declarations(target, text)
            summary.declaration_candidates_extracted += len(candidates)
            try:
                relative = source.relative_to(repo_root)
            except ValueError:
                increment(summary.obstructions_by_reason, "OBSTRUCTED_MISSING_FILE")
                summary.completed_targets += 1
                continue

            accepted_for_target = False
            with tempfile.TemporaryDirectory(prefix="sorrydb_v421_") as tmp:
                copied_root = Path(tmp) / "repo"
                shutil.copytree(
                    repo_root,
                    copied_root,
                    ignore=shutil.ignore_patterns(".git", ".lake", "build"),
                )
                copied_file = copied_root / relative
                copied_command = choose_command(target, copied_root, copied_file)
                if copied_command is None:
                    increment(summary.obstructions_by_reason, "OBSTRUCTED_NO_BUILD_COMMAND")
                    summary.completed_targets += 1
                    continue
                safety = command_safety_obstruction(copied_command, allow_cache_get)
                if safety:
                    increment(summary.obstructions_by_reason, safety)
                    summary.completed_targets += 1
                    continue

                for candidate in candidates:
                    for patch in generate_patch_templates(candidate, text):
                        attempt = replay_patch_in_workspace(
                            target,
                            text,
                            copied_root,
                            copied_file,
                            copied_command,
                            patch,
                            candidate.name,
                            timeout,
                        )
                        attempts.append(attempt)
                        summary.patch_attempts += 1
                        summary.completed_attempts = summary.patch_attempts
                        if attempt.classification == ACCEPTED_EXACT_LINE:
                            summary.accepted_exact_line_patches += 1
                            summary.best_examples.append(asdict(attempt))
                            accepted_for_target = True
                            break
                        if attempt.classification == ACCEPTED_BUT_ALIGNMENT_AMBIGUOUS:
                            summary.accepted_ambiguous_patches += 1
                        elif attempt.classification.startswith("OBSTRUCTED_"):
                            increment(summary.obstructions_by_reason, attempt.classification)
                        else:
                            increment(summary.rejected_counts_by_reason, attempt.classification)
                    if accepted_for_target:
                        break
            summary.completed_targets += 1
    except KeyboardInterrupt:
        finalize_interrupted_run(output, summary, attempts)
        print(json.dumps(asdict(summary), indent=2))
        return 130

    if summary.accepted_exact_line_patches:
        summary.verdict = LAWBOOK_ACCEPTED_PATCH_EXISTS
    elif summary.patch_attempts:
        summary.verdict = OBSTRUCTED_NO_EXACT_LINE_PATCH
    else:
        summary.verdict = OBSTRUCTED_NO_REPLAYABLE_TARGETS
    write_reports(output, summary, attempts)
    print(json.dumps(asdict(summary), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
