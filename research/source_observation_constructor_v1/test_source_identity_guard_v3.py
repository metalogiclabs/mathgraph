#!/usr/bin/env python3
"""Adversarial synthetic source fixture. Never reads protected held-out sources."""
from __future__ import annotations
from pathlib import Path
import importlib.util
import json
import os
import random
import stat
import subprocess
import tempfile

name = Path(__file__).with_name("source_identity_guard_v3.py")
spec = importlib.util.spec_from_file_location("guard_v3", name)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def git(root: Path, *args):
    p = subprocess.run(["git", "-C", str(root), *args], text=True,
                       capture_output=True, check=True)
    return p.stdout.strip()


def source(root: Path):
    git(root, "init", "-q")
    (root / "test").mkdir()
    (root / "test" / "README.md").write_text(
        "To run the full test suite:\npython test.py -- -knownfailure\n")
    (root / "test" / "test.py").write_text("print('trusted')\n")
    (root / "test" / "helper.py").write_text("VALUE = 1\n")
    git(root, "add", "test")
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture",
                    "-c", "user.email=fixture@example.invalid", "commit",
                    "-qm", "synthetic fixture"], check=True)
    return git(root, "rev-parse", "HEAD")


def independent_driver_oracle(root, rev):
    """Different code path: raw stat + independent Git object content."""
    expected = subprocess.check_output(
        ["git", "-C", str(root), "show", rev + ":test/test.py"])
    actual = (root / "test" / "test.py").read_bytes()
    mode = os.lstat(root / "test" / "test.py").st_mode
    return stat.S_ISREG(mode) and expected == actual


def rejected(root, revision, proposal, expected=None):
    try:
        guard.verify_driver(root, revision, proposal)
    except guard.SourceIdentityObstruction as exc:
        if expected:
            assert str(exc) == expected, (str(exc), expected)
        return str(exc)
    raise AssertionError("unsafe source accepted")


def main():
    cases = {}
    with tempfile.TemporaryDirectory(prefix="mg-f1-v3-") as directory:
        root = Path(directory) / "checkout"
        root.mkdir()
        revision = source(root)
        proposal = {
            "kind": "AUTHOR_DRIVER",
            "argv": ["python", "test.py", "--", "-knownfailure"],
            "cwd": "test",
        }
        approved = guard.verify_driver(root, revision, proposal)
        assert approved["status"] == "CHECKED_PINNED_NATIVE_DRIVER"
        assert approved["git_blob"] == git(root, "rev-parse", "HEAD:test/test.py")
        assert independent_driver_oracle(root, revision)
        cases["original_tracked_driver_passes"] = True
        cases["incorrect_revision_refused"] = bool(
            rejected(root, "0" * 40, proposal, "SOURCE_REVISION_MISMATCH"))
        # Core regression: Git SHA and README unchanged, executable bytes mutated.
        script = root / "test" / "test.py"
        script.write_text("print('unauthorized')\n")
        assert git(root, "rev-parse", "HEAD") == revision
        assert not independent_driver_oracle(root, revision)
        cases["modified_script_refused"] = bool(
            rejected(root, revision, proposal, "SOURCE_WORKTREE_NOT_CLEAN"))
        git(root, "reset", "--hard", "-q", revision)
        script.write_text("print('staged unauthorized')\n")
        git(root, "add", "test/test.py")
        cases["staged_script_refused"] = bool(
            rejected(root, revision, proposal, "SOURCE_WORKTREE_NOT_CLEAN"))
        git(root, "reset", "--hard", "-q", revision)
        (root / "test" / "helper.py").write_text("VALUE = 999\n")
        cases["changed_import_refused"] = bool(
            rejected(root, revision, proposal, "SOURCE_WORKTREE_NOT_CLEAN"))
        git(root, "reset", "--hard", "-q", revision)
        (root / "test" / "untracked.py").write_text("VALUE = 999\n")
        cases["untracked_import_refused"] = bool(
            rejected(root, revision, proposal, "SOURCE_WORKTREE_NOT_CLEAN"))
        (root / "test" / "untracked.py").unlink()
        (root / ".gitignore").write_text("test/ignored.py\n")
        git(root, "add", ".gitignore")
        subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture",
                        "-c", "user.email=fixture@example.invalid", "commit",
                        "-qm", "ignore fixture"], check=True)
        revision = git(root, "rev-parse", "HEAD")
        (root / "test" / "ignored.py").write_text("VALUE = 123\n")
        cases["ignored_import_refused"] = bool(rejected(
            root, revision, proposal, "SOURCE_IGNORED_UNTRACKED_FILES_PRESENT"))
        (root / "test" / "ignored.py").unlink()
        script.unlink()
        script.symlink_to(root / "test" / "helper.py")
        cases["inside_alias_refused"] = bool(rejected(
            root, revision, proposal, "SOURCE_WORKTREE_NOT_CLEAN"))
        script.unlink()
        # Refuse unsupported operation even when exact source is clean.
        git(root, "reset", "--hard", "-q", revision)
        pytest_proposal = dict(proposal, kind="AUTHOR_PYTEST", argv=[
            "python", "-m", "pytest", "-q"])
        cases["pytest_scope_unknown"] = bool(rejected(
            root, revision, pytest_proposal,
            "UNKNOWN_NON_DRIVER_EXECUTION_IDENTITY"))
        cases["forbidden_help_flag"] = bool(rejected(
            root, revision, dict(proposal, argv=["python", "test.py", "--help"]),
            "LIST_ONLY_DRIVER_NOT_ADMITTED"))
        cases["forbidden_path_flag"] = bool(rejected(
            root, revision, dict(proposal, argv=["python", "test.py", "../escape"]),
            "UNSUPPORTED_DRIVER_ARGUMENT"))
        cases["forbidden_cwd_traversal"] = bool(rejected(
            root, revision, dict(proposal, cwd="../outside"), "UNSAFE_CWD"))
        assert guard.verify_driver(root, revision, proposal)["git_blob"] == git(
            root, "rev-parse", "HEAD:test/test.py")
        cases["clean_restore_passes"] = True
        randomizer = random.Random(20261026)
        count = 0
        for i in range(128):
            # Deterministic changes in executable bytes; the pinned commit is unchanged.
            value = randomizer.randrange(1, 1_000_000)
            script.write_text("print(%d)\n" % value)
            assert not independent_driver_oracle(root, revision)
            assert rejected(root, revision, proposal,
                            "SOURCE_WORKTREE_NOT_CLEAN")
            git(root, "reset", "--hard", "-q", revision)
            assert guard.verify_driver(root, revision, proposal)["status"] == \
                "CHECKED_PINNED_NATIVE_DRIVER"
            count += 1
    assert all(cases.values()), cases
    print(json.dumps({
        "status": "PASS_F1_V3_SOURCE_IDENTITY_PREQUALIFICATION",
        "named_cases": len(cases),
        "randomized_executable_mutations": count,
        "actual_heldout_source_access": "NONE",
        "scope": "exact clean Git checkout + pinned AUTHOR_DRIVER bytes",
        "not_verified": [
            "imports/transitive dependencies beyond source tree",
            "hermetic execution or time-of-check/time-of-use",
            "author-declared suite completeness",
            "autonomous sensor grammar invention",
        ],
        "cases": cases,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
