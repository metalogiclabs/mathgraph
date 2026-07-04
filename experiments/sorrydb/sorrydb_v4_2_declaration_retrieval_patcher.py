#!/usr/bin/env python3
"""SorryDB v4.2 declaration-retrieval and exact-line replay harness."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any, Iterable

BANNER = "MATHGRAPH x SORRYDB v4.2 — DECLARATION-RETRIEVAL PATCHER"
ACCEPTED_EXACT_LINE = "ACCEPTED_EXACT_LINE"
ACCEPTED_BUT_ALIGNMENT_AMBIGUOUS = "ACCEPTED_BUT_ALIGNMENT_AMBIGUOUS"
OBSTRUCTED_NO_INPUT_RECORDS = "OBSTRUCTED_NO_INPUT_RECORDS"
OBSTRUCTED_NO_REPLAYABLE_TARGETS = "OBSTRUCTED_NO_REPLAYABLE_TARGETS"
LAWBOOK_ACCEPTED_PATCH_EXISTS = "LAWBOOK_ACCEPTED_PATCH_EXISTS"
OBSTRUCTED_NO_EXACT_LINE_PATCH = "OBSTRUCTED_NO_EXACT_LINE_PATCH"
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
    line_raw = first_value(record, ["line", "line_number", "target_line", "location.line"], 0)
    try:
        line = int(line_raw)
    except (TypeError, ValueError):
        line = 0
    return SorryTarget(
        repo=str(first_value(record, ["repo", "repository", "repo_name", "project"], "")),
        file_path=str(first_value(record, ["file", "file_path", "path", "location.file"], "")),
        line=line,
        statement=str(first_value(record, ["statement", "theorem", "declaration", "goal", "target"], "")),
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
            for key in ("records", "items", "targets"):
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


def run_command(command: list[str], cwd: Path, timeout: int) -> tuple[int | None, str, str, float, bool]:
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)
        return result.returncode, result.stdout, result.stderr, time.monotonic() - started, False
    except subprocess.TimeoutExpired as exc:
        return None, exc.stdout or "", exc.stderr or "", time.monotonic() - started, True
    except OSError as exc:
        return None, "", str(exc), time.monotonic() - started, False


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


def replay_patch(target: SorryTarget, patch: str, candidate_name: str, timeout: int) -> PatchAttempt:
    source, repo_root = resolve_paths(target)
    if source is None or not source.exists():
        return PatchAttempt(target.repo, target.file_path, target.line, patch, candidate_name, "OBSTRUCTED_MISSING_FILE", None, 0.0)
    if repo_root is None or not repo_root.exists():
        return PatchAttempt(target.repo, target.file_path, target.line, patch, candidate_name, "OBSTRUCTED_NO_BUILD_COMMAND", None, 0.0)
    original = source.read_text(encoding="utf-8")
    patched, aligned_line, aligned = replace_sorry_at_line(original, target.line, patch)
    if patched is None:
        return PatchAttempt(target.repo, target.file_path, target.line, patch, candidate_name, "ACCEPTED_BUT_ALIGNMENT_AMBIGUOUS", None, 0.0)
    before_count = len(FORBIDDEN_RE.findall(original))
    after_count = len(FORBIDDEN_RE.findall(patched))
    with tempfile.TemporaryDirectory(prefix="sorrydb_v42_") as tmp:
        copied_root = Path(tmp) / "repo"
        shutil.copytree(repo_root, copied_root, ignore=shutil.ignore_patterns(".git", ".lake", "build"))
        try:
            relative = source.relative_to(repo_root)
        except ValueError:
            return PatchAttempt(target.repo, target.file_path, target.line, patch, candidate_name, "OBSTRUCTED_MISSING_FILE", None, 0.0)
        copied_file = copied_root / relative
        command = choose_command(target, copied_root, copied_file)
        if command is None:
            return PatchAttempt(target.repo, target.file_path, target.line, patch, candidate_name, "OBSTRUCTED_NO_BUILD_COMMAND", None, 0.0, aligned_line)
        baseline_rc, baseline_out, baseline_err, baseline_elapsed, baseline_timeout = run_command(command, copied_root, timeout)
        if baseline_timeout or baseline_rc != 0:
            classification = "REJECTED_TIMEOUT" if baseline_timeout else "REJECTED_IMPORT_OR_BUILD_BOUNDARY"
            return PatchAttempt(target.repo, target.file_path, target.line, patch, candidate_name, classification, baseline_rc, baseline_elapsed, aligned_line, baseline_out[-4000:], baseline_err[-4000:])
        copied_file.write_text(patched, encoding="utf-8")
        rc, out, err, elapsed, timed_out = run_command(command, copied_root, timeout)
    classification = classify_result(rc, out, err, timed_out)
    if classification == ACCEPTED_EXACT_LINE:
        if not aligned or after_count != before_count - 1:
            classification = ACCEPTED_BUT_ALIGNMENT_AMBIGUOUS
    return PatchAttempt(target.repo, target.file_path, target.line, patch, candidate_name, classification, rc, elapsed, aligned_line, out[-4000:], err[-4000:])


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
        "# SorryDB v4.2 run\n\n"
        f"Verdict: `{summary.verdict}`\n\n"
        "Only `ACCEPTED_EXACT_LINE` attempts are Lawbook candidates.\n"
    )


def main() -> int:
    print(BANNER)
    work_root = Path(os.getenv("SORRYDB_V42_WORK_ROOT", "/tmp/mathgraph_sorrydb_v4_2"))
    records_path = Path(os.getenv("SORRYDB_V42_RECORDS_PATH", str(work_root / "sorrydb_records.jsonl")))
    max_records = int(os.getenv("SORRYDB_V42_MAX_RECORDS", "40"))
    focus = [x.strip() for x in os.getenv("SORRYDB_V42_FOCUS_REPOS", "LeanLangur,LeanLion,MetaExamples").split(",") if x.strip()]
    timeout = int(os.getenv("SORRYDB_V42_TIMEOUT_SECONDS", "90"))
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = work_root / "artifacts" / "runs" / "sorrydb_v4_2_declaration_retrieval_patcher" / timestamp
    records = load_records(records_path)
    summary = RunSummary(total_records_loaded=len(records))
    attempts: list[PatchAttempt] = []
    if not records:
        summary.verdict = OBSTRUCTED_NO_INPUT_RECORDS
        increment(summary.obstructions_by_reason, OBSTRUCTED_NO_INPUT_RECORDS)
        write_reports(output, summary, attempts)
        print(json.dumps(asdict(summary), indent=2))
        return 0
    targets = [defensive_target(record) for record in records]
    order = {repo: index for index, repo in enumerate(focus)}
    targets.sort(key=lambda target: (order.get(target.repo, len(order)), target.repo, target.file_path, target.line))
    targets = [target for target in targets if not focus or target.repo in focus][:max_records]
    summary.targets_selected = len(targets)
    for target in targets:
        increment(summary.focus_repo_counts, target.repo or "UNKNOWN")
        source, _ = resolve_paths(target)
        if source is None:
            increment(summary.obstructions_by_reason, "OBSTRUCTED_MISSING_FILE")
            continue
        text = source.read_text(encoding="utf-8")
        candidates = retrieve_declarations(target, text)
        summary.declaration_candidates_extracted += len(candidates)
        for candidate in candidates:
            for patch in generate_patch_templates(candidate, text):
                attempt = replay_patch(target, patch, candidate.name, timeout)
                attempts.append(attempt)
                summary.patch_attempts += 1
                if attempt.classification == ACCEPTED_EXACT_LINE:
                    summary.accepted_exact_line_patches += 1
                    summary.best_examples.append(asdict(attempt))
                    break
                if attempt.classification == ACCEPTED_BUT_ALIGNMENT_AMBIGUOUS:
                    summary.accepted_ambiguous_patches += 1
                elif attempt.classification.startswith("OBSTRUCTED_"):
                    increment(summary.obstructions_by_reason, attempt.classification)
                else:
                    increment(summary.rejected_counts_by_reason, attempt.classification)
            if summary.accepted_exact_line_patches:
                break
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
