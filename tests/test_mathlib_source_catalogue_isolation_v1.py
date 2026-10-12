"""Native process qualification of the emitted read-only mount policy.

Docker is unavailable in this task environment. At its process boundary this
test translates the actual emitted read-only roots into enforced Seatbelt
rules and runs a real write-attempt process. Run separately from an outer
Seatbelt sandbox: macOS prohibits nesting. The child also denies networking.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from test_mathlib_source_catalogue_publisher_v1 import ROOT, api, inputs, environment, git_dependency, git, sha

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or shutil.which("sandbox-exec") is None,
    reason="macOS Seatbelt qualification unavailable; Task 3 requires actual Docker isolation qualification",
)


@pytest.mark.parametrize("relative", ["A.lean", ".lake/packages/dep/Dep.lean", ".lake/build/lib/lean/Outside.olean"])
def test_build_process_cannot_mutate_compiled_inputs(api, inputs, environment, git_dependency, monkeypatch, relative):
    root, policy, _ = inputs
    _, inventory, config = environment
    package = inventory["packages"][0]
    (root / "lake-manifest.json").write_text(json.dumps({"packages": [{"name": package["name"], "rev": package["commit"], "url": package["repository"]}]}))
    git(root, "add", "lake-manifest.json")
    git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "lock")
    for field, rev in [("commit", "HEAD"), ("tree", "HEAD^{tree}")]: policy["source"][field] = inventory["source_" + field] = git(root, "rev-parse", rev)
    policy["source"]["lake_manifest"]["sha256"] = sha((root / "lake-manifest.json").read_bytes())
    Path(config["inventory"]).write_bytes(api.contract.canonical_bytes(inventory))
    config["dependency_inventory_sha256"] = sha(Path(config["inventory"]).read_bytes())
    real_run = subprocess.run
    attempted = []
    def boundary(command, **kwargs):
        if command[0] != "docker": return real_run(command, **kwargs)
        mounts = [dict(part.split("=", 1) if "=" in part else (part, True) for part in command[i + 1].split(",")) for i, arg in enumerate(command) if arg == "--mount"]
        work = Path(next(m["src"] for m in mounts if m["dst"] == "/work"))
        target = work / relative
        before = target.read_bytes()
        profile = '(version 1)(allow default)(deny network*)' + ''.join('(deny file-write* (subpath ' + json.dumps(str(Path(m["src"]).resolve())) + '))' for m in mounts if m.get("readonly"))
        result = real_run(["sandbox-exec", "-p", profile, sys.executable, "-I", "-S", "-B", "-c", "from pathlib import Path; import sys; Path(sys.argv[1]).write_bytes(b'changed input')", str(target)], capture_output=True, text=True)
        assert result.returncode != 0, "build process was able to mutate its verified input"
        assert "PermissionError" in result.stderr and "Operation not permitted" in result.stderr, result.stderr
        assert target.read_bytes() == before
        attempted.append(relative)
        raise subprocess.CalledProcessError(result.returncode, command)
    monkeypatch.setattr(api.subprocess, "run", boundary)
    with pytest.raises(subprocess.CalledProcessError):
        api.run_offline_extraction(api.verify_source_checkout(policy, root), ROOT / "tools/mathlib_catalogue/Extract.lean", ["A", "B"], config)
    assert attempted == [relative]


def test_real_selected_compile_and_extract_with_readonly_inputs(api, inputs, environment, monkeypatch, tmp_path):
    root, policy, identity = inputs
    dependencies, inventory, config = environment
    (root / "B.lean").write_text("namespace B\ninductive T where | mk\nend B\n")
    (root / "A.lean").write_text("import B\nnamespace A\ndef stale : B.T := B.T.mk\nend A\n")
    lean = Path(os.environ["MATHGRAPH_CATALOGUE_LEAN"])
    cache = dependencies / "build/lib/lean"
    env = {**os.environ, "LEAN_PATH": str(cache), "PATH": str(lean.parent) + os.pathsep + os.environ["PATH"]}
    for name in ["B", "A"]:
        subprocess.run([str(lean), "-o", str(cache / (name + ".olean")), name + ".lean"], cwd=root, env=env, check=True)
    # Stale selected cache must never win over newly compiled source outputs.
    (root / "A.lean").write_text("import B\nnamespace A\ndef α : B.T := B.T.mk\nend A\n")
    git(root, "add", ".")
    git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "real sources")
    for field, rev in [("commit", "HEAD"), ("tree", "HEAD^{tree}")]: policy["source"][field] = inventory["source_" + field] = git(root, "rev-parse", rev)
    for module in policy["modules"]:
        raw = (root / module["path"]).read_bytes()
        module.update(sha256=sha(raw), size_bytes=len(raw))
    inventory["files"] = [{"path": p.relative_to(dependencies).as_posix(), "sha256": sha(p.read_bytes()), "size_bytes": p.stat().st_size, "mode": "100644"} for p in sorted(dependencies.rglob("*")) if p.is_file()]
    Path(config["inventory"]).write_bytes(api.contract.canonical_bytes(inventory))
    config["dependency_inventory_sha256"] = sha(Path(config["inventory"]).read_bytes())
    source = api.verify_source_checkout(policy, root)
    real_run = subprocess.run
    commands = []
    def boundary(command, **kwargs):
        if command[0] != "docker": return real_run(command, **kwargs)
        mounts = [dict(part.split("=", 1) if "=" in part else (part, True) for part in command[i + 1].split(",")) for i, arg in enumerate(command) if arg == "--mount"]
        assert next(m for m in mounts if m["dst"] == "/work")["readonly"]
        assert next(m for m in mounts if m["dst"] == "/compiled")["readonly"]
        def translate(value):
            for m in sorted(mounts, key=lambda m: -len(m["dst"])):
                value = value.replace(m["dst"], m["src"])
            return value
        child_env = {**env, **{command[i + 1].split("=", 1)[0]: translate(command[i + 1].split("=", 1)[1]) for i, arg in enumerate(command) if arg == "--env"}}
        profile = '(version 1)(allow default)(deny network*)' + ''.join('(deny file-write* (subpath ' + json.dumps(str(Path(m["src"]).resolve())) + '))' for m in mounts if m.get("readonly"))
        args = [translate(a) for a in command[command.index(config["image"]) + 1:]]
        commands.append(args)
        result = real_run(["sandbox-exec", "-p", profile, "/bin/sh", *args], cwd=translate("/work"), env=child_env, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        return result
    monkeypatch.setattr(api.subprocess, "run", boundary)
    raw = api.run_offline_extraction(source, ROOT / "tools/mathlib_catalogue/Extract.lean", ["A", "B"], config)
    assert [c[-1] for c in commands[1:3]] == ["B.lean", "A.lean"]
    assert len(commands) == 4
    doc = json.loads(raw)
    assert any(d["qualified_name"] == "A.α" for d in doc["modules"][0]["declarations"])
    assert not any(d["qualified_name"] == "A.stale" for d in doc["modules"][0]["declarations"])
    publication = api.build_publication(policy, source, identity, raw)
    api.validate_publication(publication)
