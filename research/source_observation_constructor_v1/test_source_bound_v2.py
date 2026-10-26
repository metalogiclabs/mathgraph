#!/usr/bin/env python3
"""Exposed-only F1 executable-identity regression. No protected source access.

This verifies the *specific* native-driver path binding. It is not a
general-purpose process sandbox or autonomous sensor grammar test.
"""
import importlib.util
import json
import os
import pathlib
import random
import stat
import tempfile
import sys

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE / "construct.py"
spec = importlib.util.spec_from_file_location("candidate_observer_constructor_v2", SOURCE)
candidate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = candidate
spec.loader.exec_module(candidate)


def independent_oracle(root, cwd):
    """Independent lstat/realpath condition, not candidate's Path methods."""
    root = os.path.realpath(root)
    cwd = os.fspath(cwd)
    path = os.path.join(cwd, "test.py")
    try:
        d = os.lstat(cwd).st_mode
        f = os.lstat(path).st_mode
        return (
            stat.S_ISDIR(d) and not stat.S_ISLNK(d)
            and stat.S_ISREG(f) and not stat.S_ISLNK(f)
            and os.path.commonpath((root, os.path.realpath(path))) == root
        )
    except (OSError, ValueError):
        return False


def check():
    cases = []
    with tempfile.TemporaryDirectory(prefix="mathgraph-f1-v2-") as td:
        td = pathlib.Path(td)
        root = td / "source"
        native = root / "test"
        foreign = td / "foreign"
        native.mkdir(parents=True)
        foreign.mkdir()
        (foreign / "test.py").write_text("print('FOREIGN')\n")
        driver = native / "test.py"
        driver.write_text("print('IN_SOURCE')\n")
        (root / "safe.py").write_text("pass\n")

        def case(name, allowed, working_dir=None):
            cwd = working_dir if working_dir is not None else native
            actual = candidate.argv_from_fragment(
                "python test.py -- -knownfailure", cwd, root
            ) is not None
            independent = independent_oracle(root, cwd)
            assert actual == allowed == independent, (name, actual, allowed, independent)
            cases.append({"name": name, "accepted": actual})

        case("regular source driver", True)
        driver.unlink()
        driver.symlink_to(foreign / "test.py")
        case("outside symbolic link", False)
        driver.unlink()
        driver.symlink_to(root / "safe.py")
        case("inside symbolic link", False)
        driver.unlink()
        driver.write_text("pass\n")
        (root / "aliased-test").symlink_to(native, target_is_directory=True)
        case("aliased directory", False, root / "aliased-test")
        (root / "missing").mkdir()
        case("missing test driver", False, root / "missing")
        driver.unlink()
        driver.mkdir()
        case("directory instead of driver", False)
        driver.rmdir()
        driver.write_text("pass\n")
        case("restored regular driver", True)

        assert candidate.argv_from_fragment("python test.py -l", native, root) is None
        assert candidate.argv_from_fragment("python test.py --help", native, root) is None
        assert candidate.argv_from_fragment("pytest ../outside", native, root) is None
        assert candidate.argv_from_fragment("python test.py -- -knownfailure", native, root)
        cases.append({"name": "unsafe flags and traversal refused", "accepted": False})

        rng = random.Random(2601026)
        for index in range(256):
            if driver.exists() or driver.is_symlink():
                driver.unlink()
            variant = rng.randrange(4)
            if variant == 0:
                driver.write_text("pass\n")
            elif variant == 1:
                driver.symlink_to(root / "safe.py")
            elif variant == 2:
                driver.symlink_to(foreign / "test.py")
            else:
                driver.symlink_to(root / "absent.py")
            got = candidate.argv_from_fragment("python test.py", native, root) is not None
            expected = independent_oracle(root, native)
            assert got == expected, (index, variant, got, expected)

        old_exposed = candidate.synthetic()
        assert old_exposed["synthetic"] == "PASS"

    return {
        "status": "PASS_EXPOSED_SOURCE_BOUND_PREFLIGHT",
        "adversarial_cases": cases,
        "independent_filesystem_oracle_cases": 256,
        "frozen_prior_f0": "NOT_MODIFIED",
        "heldout_sources_opened": False,
        "not_established": [
            "general process sandbox security",
            "native held-out source identity",
            "observer grammar invention",
            "prospective source-native advantage"
        ],
    }


if __name__ == "__main__":
    result = check()
    if len(sys.argv) == 3 and sys.argv[1] == "--out":
        out = pathlib.Path(sys.argv[2])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
