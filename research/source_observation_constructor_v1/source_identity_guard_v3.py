#!/usr/bin/env python3
"""Source-identity admission gate for a future F1 observer evaluator.

Bounded pre-execution assurance only: it establishes clean exact Git checkout
and pinned native test.py bytes. It does NOT establish hermetic execution,
transitive dependency completeness, external truth, or absence of TOCTOU.
Never use this module to qualify a protected source without the separately
precommitted source lock, authority, and baseline.
"""
from __future__ import annotations
from pathlib import Path
import os
import re
import stat
import subprocess


class SourceIdentityObstruction(RuntimeError):
    pass


def git(root: Path, *arguments: str, binary: bool = False):
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True, timeout=12, check=False,
    )
    if result.returncode:
        raise SourceIdentityObstruction("SOURCE_GIT_QUERY_FAILED")
    return result.stdout if binary else result.stdout.decode("utf-8").strip()


def verify_source(root: Path, pinned_sha: str) -> dict:
    """Refuse modifications including staged, untracked and ignored files."""
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise SourceIdentityObstruction("SOURCE_ROOT_NOT_DIRECTORY")
    if not re.fullmatch(r"[0-9a-f]{40}", pinned_sha):
        raise SourceIdentityObstruction("BAD_SOURCE_COMMIT")
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise SourceIdentityObstruction("SOURCE_ROOT_NOT_GIT_TOPLEVEL")
    if git(root, "rev-parse", "HEAD") != pinned_sha:
        raise SourceIdentityObstruction("SOURCE_REVISION_MISMATCH")
    if git(root, "status", "--porcelain=v1", "--untracked-files=all",
           "--ignore-submodules=none"):
        raise SourceIdentityObstruction("SOURCE_WORKTREE_NOT_CLEAN")
    # Ignored Python modules can be imported: they must not escape admission.
    if git(root, "ls-files", "--others", "--ignored",
           "--exclude-standard", "-z", binary=True):
        raise SourceIdentityObstruction("SOURCE_IGNORED_UNTRACKED_FILES_PRESENT")
    return {
        "status": "CHECKED_EXACT_GIT_WORKTREE",
        "commit": pinned_sha,
        "boundary": "tracked/staged/untracked/ignored at check time only",
    }


def no_symlinks_below(root: Path, relative: Path) -> bool:
    parent = root
    for segment in relative.parts:
        parent = parent / segment
        try:
            if stat.S_ISLNK(os.lstat(parent).st_mode):
                return False
        except OSError:
            return False
    return True


def verify_driver(root: Path, pinned_sha: str, proposal: dict) -> dict:
    """Fail closed on any other operation family or unsafe path."""
    source = verify_source(root, pinned_sha)
    root = Path(root).resolve()
    if proposal.get("kind") != "AUTHOR_DRIVER":
        raise SourceIdentityObstruction("UNKNOWN_NON_DRIVER_EXECUTION_IDENTITY")
    args = proposal.get("argv")
    if (not isinstance(args, list) or len(args) < 2 or len(args) > 9
        or not all(isinstance(x, str) for x in args)
        or args[:2] != ["python", "test.py"]):
        raise SourceIdentityObstruction("UNSUPPORTED_DRIVER_COMMAND")
    if any(arg in ("-l", "--help") for arg in args[2:]):
        raise SourceIdentityObstruction("LIST_ONLY_DRIVER_NOT_ADMITTED")
    if any(not re.fullmatch(r"-[a-z][a-z0-9_-]*|--", arg)
           for arg in args[2:]):
        raise SourceIdentityObstruction("UNSUPPORTED_DRIVER_ARGUMENT")
    cwd = proposal.get("cwd")
    if not isinstance(cwd, str):
        raise SourceIdentityObstruction("BAD_CWD")
    rel = Path(cwd)
    if rel.is_absolute() or ".." in rel.parts:
        raise SourceIdentityObstruction("UNSAFE_CWD")
    script_rel = rel / "test.py"
    if not no_symlinks_below(root, script_rel):
        raise SourceIdentityObstruction("SCRIPT_OR_PARENT_IS_SYMLINK")
    target = root / script_rel
    try:
        if not stat.S_ISREG(os.lstat(target).st_mode):
            raise SourceIdentityObstruction("DRIVER_NOT_REGULAR_FILE")
    except OSError:
        raise SourceIdentityObstruction("DRIVER_NOT_REGULAR_FILE") from None
    relative_name = script_rel.as_posix()
    try:
        git(root, "ls-files", "--error-unmatch", "--", relative_name)
        expected = git(root, "rev-parse", "HEAD:" + relative_name)
        actual = git(root, "hash-object", "--", relative_name)
    except SourceIdentityObstruction:
        raise SourceIdentityObstruction("UNTRACKED_OR_UNQUALIFIED_DRIVER") from None
    if not re.fullmatch(r"[0-9a-f]{40}", expected) or actual != expected:
        raise SourceIdentityObstruction("EXECUTABLE_BYTES_DIFFER_FROM_PINNED_COMMIT")
    return {
        **source, "status": "CHECKED_PINNED_NATIVE_DRIVER",
        "executable": relative_name, "git_blob": expected,
        "limitations": [
            "Only directly executed native script bytes; imports and interpreter not fully bound",
            "Source admission check and execution are not atomic",
            "Not an assertion of full source-author test scope or source-side-effect safety",
        ],
    }
