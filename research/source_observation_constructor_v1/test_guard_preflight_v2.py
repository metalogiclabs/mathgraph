#!/usr/bin/env python3
"""Exposed-only constructor guard tests. No protected sources or native execution."""
import importlib.util
import json
import os
from pathlib import Path
import random
import stat
from tempfile import TemporaryDirectory

spec = importlib.util.spec_from_file_location("observer_f1_guard_v2", Path(__file__).with_name("construct.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def independent_oracle(root, cwd):
    """Inode and canonical path oracle, separate from candidate implementation."""
    root, cwd = os.path.realpath(root), os.fspath(cwd)
    script = os.path.join(cwd, "test.py")
    try:
        a, b = os.lstat(cwd).st_mode, os.lstat(script).st_mode
        return (stat.S_ISDIR(a) and not stat.S_ISLNK(a)
                and stat.S_ISREG(b) and not stat.S_ISLNK(b)
                and os.path.commonpath([root, os.path.realpath(script)]) == root)
    except (OSError, ValueError):
        return False

def test():
    labels = []
    with TemporaryDirectory(prefix="mg-observer-f1-") as tmp:
        base = Path(tmp)
        root = base / "checkout"
        cwd = root / "test"
        outside = base / "outside"
        cwd.mkdir(parents=True)
        outside.mkdir()
        (outside / "test.py").write_text("print('OUTSIDE')\n")
        script = cwd / "test.py"
        script.write_text("print('INSIDE')\n")
        def check(label, expected, target=cwd):
            observed = mod.argv_from_fragment("python test.py -- -knownfailure", target, root) is not None
            assert observed == expected, (label, expected, observed)
            assert independent_oracle(root, target) == expected, (label, "oracle")
            labels.append(label)
        check("ordinary-driver", True)
        script.unlink()
        script.symlink_to(outside / "test.py")
        check("outside-symlink-driver", False)
        script.unlink()
        (root / "safe.py").write_text("pass\n")
        script.symlink_to(root / "safe.py")
        check("inside-symlink-driver", False)
        script.unlink()
        script.write_text("pass\n")
        (root / "alias").symlink_to(cwd, target_is_directory=True)
        check("aliased-working-directory", False, root / "alias")
        (root / "missing").mkdir()
        check("missing-driver", False, root / "missing")
        script.unlink()
        script.mkdir()
        check("directory-driver", False)
        script.rmdir()
        script.write_text("pass\n")
        assert mod.argv_from_fragment("python test.py -l", cwd, root) is None
        assert mod.argv_from_fragment("python test.py --help", cwd, root) is None
        assert mod.argv_from_fragment("python -m pytest ../../outside", cwd, root) is None
        assert mod.argv_from_fragment("python test.py -- -knownfailure", cwd, root) is not None
        randomizer = random.Random(2601026)
        for i in range(256):
            if script.exists() or script.is_symlink():
                script.unlink()
            kind = randomizer.randrange(4)
            if kind == 0:
                script.write_text("pass\n")
            elif kind == 1:
                script.symlink_to(root / "safe.py")
            elif kind == 2:
                script.symlink_to(outside / "test.py")
            else:
                script.symlink_to(root / "not-present.py")
            observed = mod.argv_from_fragment("python test.py", cwd, root) is not None
            assert observed == independent_oracle(root, cwd), (i, kind)
    assert mod.synthetic()["synthetic"] == "PASS"
    report = {"status": "PASS_EXPOSED_GUARD_V2",
              "targeted_path_cases": len(labels), "negative_argv_checks": 3,
              "independent_path_oracle_cases": 256,
              "prior_exposed_synthetic": "PASS",
              "protected_heldout_source_access": "NONE",
              "not_a_sandbox_proof": True}
    print(json.dumps(report, sort_keys=True, indent=2))
    return report

if __name__ == "__main__":
    test()
