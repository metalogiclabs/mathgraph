"""The producer rejects unpinned bytes and cannot promote source data to evidence."""
from copy import deepcopy
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "catalogues/mathlib-v4.34.1-foundations-v1.source.json"
FIXTURE = ROOT / "tests/fixtures/source_catalogue_v1/extractor-output.json"


@pytest.fixture
def api():
    path = ROOT / "mathgraph/source_catalogue_publisher_v1.py"
    assert path.is_file(), "publisher missing"
    spec = importlib.util.spec_from_file_location("source_catalogue_publisher_v1", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_publisher_exists():
    assert (ROOT / "mathgraph/source_catalogue_publisher_v1.py").is_file(), "publisher missing"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def inputs(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()
    files = {"A.lean": "import B\n-- B.proof is only text\ndef α : B.T := B.mk\n",
             "B.lean": "inductive T where | mk\n", "LICENSE": "Apache-2.0\n",
             "CITATION.md": "Fixture\n", "lean-toolchain": "leanprover/lean4:v4.34.1\n",
             "lake-manifest.json": "{\"packages\":[]}\n", "Root.lean": "import A\n",
             "lakefile.toml": "name = \"fixture\"\n"}
    for name, text in files.items():
        (root / name).write_text(text)
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
    pin = {"repository": "https://example.invalid/fixture", "tag": "descriptive-only",
           "commit": git(root, "rev-parse", "HEAD"), "tree": git(root, "rev-parse", "HEAD^{tree}")}
    for key, path in [("license", "LICENSE"), ("citation", "CITATION.md"), ("lean_toolchain", "lean-toolchain"),
                      ("lake_manifest", "lake-manifest.json"), ("root_module", "Root.lean")]:
        pin[key] = {"path": path, "sha256": sha((root / path).read_bytes())}
    pin["lean_toolchain"]["value"] = "leanprover/lean4:v4.34.1"
    policy = {"schema": "mathgraph.source-catalogue-policy.v1", "catalogue_id": "fixture-v1", "source": pin,
              "modules": [{"module": name, "path": name + ".lean", "sha256": sha((root / (name + ".lean")).read_bytes()),
                           "size_bytes": len((root / (name + ".lean")).read_bytes())} for name in ["A", "B"]],
              "build_inputs": [{"path": "lakefile.toml", "sha256": sha((root / "lakefile.toml").read_bytes())}]}
    identity = {"source_commit": "f" * 40, "contract_version": 1,
                "sources": [{"path": "tools/mathlib_catalogue/Extract.lean", "sha256": "a" * 64}],
                "environment": {"image": "fixture@sha256:" + "b" * 64,
                                "dependency_inventory_sha256": "c" * 64, "authority": "NONE"}}
    return root, policy, identity


def test_policy_freezes_exact_source(api):
    p = api.load_source_policy(POLICY)
    assert p["source"]["repository"] == "https://github.com/leanprover-community/mathlib4"
    assert p["source"]["commit"] == "d13f23b723b8a846827a245b89c10fc7d3f11612"
    assert p["source"]["tree"] == "efa132418a56d0e38c56cc412a06df22178dac5c"
    assert p["source"]["tag"] == "v4.34.1"
    assert p["source"]["lean_toolchain"]["value"] == "leanprover/lean4:v4.34.1"
    assert {k: p["source"][k]["sha256"] for k in ["license", "citation", "lean_toolchain", "lake_manifest", "root_module"]} == {
        "license": "b40930bbcf80744c86c46a12bc9da056641d722716c378f5659b9e555ef833e1",
        "citation": "08a68d7e41823aa5bf55f19b65266e58802b76b7208109646fb5e94a056f518a",
        "lean_toolchain": "d5edba4e4b8faad9c1baeadb265716d20d03be4d1a2647dc5e35b0c0325bea7b",
        "lake_manifest": "8f67b2cf24143ac091cdb425e886c2164b2fc2d6fbccd6db9454b697f9541a67",
        "root_module": "61d699d8ace6240934a751f1b1951339090d6e380b505041632227dd7eb73a29"}
    assert {m["path"] for m in p["modules"]} == {"Mathlib/" + s + ".lean" for s in [
        "Data/Nat/Basic", "Data/Int/Basic", "Data/List/Basic", "Data/Finset/Basic", "Data/Set/Basic",
        "Logic/Function/Basic", "Algebra/Group/Basic", "Algebra/Ring/Basic", "Order/Basic", "Data/Nat/Prime/Basic",
        "Combinatorics/SimpleGraph/Basic", "Topology/Basic", "Analysis/SpecialFunctions/Pow/Real"]}


@pytest.mark.parametrize("mutation", ["dirty", "commit", "tree", "traversal", "symlink", "missing", "source_hash", "metadata_hash", "subdirectory"])
def test_checkout_rejects_unverified_inputs(api, inputs, mutation):
    root, policy, _ = inputs
    if mutation == "dirty": (root / "A.lean").write_text("changed")
    if mutation in {"commit", "tree"}: policy["source"][mutation] = "0" * 40
    if mutation == "traversal": policy["modules"][0]["path"] = "../A.lean"
    if mutation == "symlink":
        (root / "A.lean").unlink()
        (root / "A.lean").symlink_to(root.parent / "elsewhere")
    if mutation == "missing": (root / "B.lean").unlink()
    if mutation == "source_hash": policy["modules"][0]["sha256"] = "0" * 64
    if mutation == "metadata_hash": policy["source"]["license"]["sha256"] = "0" * 64
    if mutation == "subdirectory":
        (root / "nested").mkdir()
        root = root / "nested"
    with pytest.raises(ValueError): api.verify_source_checkout(policy, root)


def test_tag_is_only_descriptive_and_verified_source_is_immutable(api, inputs):
    root, policy, _ = inputs
    policy["source"]["tag"] = "no-such-tag"
    source = api.verify_source_checkout(policy, root)
    with pytest.raises((AttributeError, TypeError)): source.root = Path("/")
    policy["source"]["commit"] = "0" * 40
    assert json.loads(source.policy_bytes)["source"]["commit"] != "0" * 40


@pytest.mark.parametrize("target,accepted", [("LICENSE", True), ("../outside", False)])
def test_tracked_nonselected_symlink_must_remain_inside_verified_root(api, inputs, target, accepted):
    root, policy, _ = inputs
    (root.parent / "outside").write_text("external")
    (root / "helper-link").symlink_to(target)
    git(root, "add", "helper-link")
    git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "helper link")
    policy["source"]["commit"] = git(root, "rev-parse", "HEAD")
    policy["source"]["tree"] = git(root, "rev-parse", "HEAD^{tree}")
    if accepted:
        source = api.verify_source_checkout(policy, root)
        assert "helper-link" in source.tracked_paths
    else:
        with pytest.raises(ValueError): api.verify_source_checkout(policy, root)


def test_publication_is_deterministic_and_only_has_structural_edges(api, inputs, tmp_path):
    root, policy, identity = inputs
    source = api.verify_source_checkout(policy, root)
    one = api.build_publication(policy, source, identity, FIXTURE.read_bytes())
    two = api.build_publication(policy, source, identity, FIXTURE.read_bytes())
    assert one == two
    assert dict(one.files) == dict(two.files)
    docs = [json.loads(raw) for path, raw in one.files if path.startswith("shards/")]
    assert sum(len(d["objects"]) for d in docs) == 3
    assert {r["type"] for d in docs for r in d["relations"]} == {"DECLARES", "IMPORTS_MODULE", "TYPE_REFERENCES"}
    assert all(r["authority"] == "NONE" and not r["logical_implication"] and not r["semantic_equivalence"] for d in docs for r in d["relations"])
    assert sum(len(d["omissions"]["imports"]) for d in docs) == 1
    assert sum(len(d["omissions"]["type_references"]) for d in docs) == 1
    output = tmp_path / "publication"
    api.publish_catalogue(one, output)
    api.publish_catalogue(two, output, check=True)


@pytest.mark.parametrize("mutation", ["changed", "added", "missing"])
def test_check_detects_every_publication_byte_change(api, inputs, tmp_path, mutation):
    root, policy, identity = inputs
    pub = api.build_publication(policy, api.verify_source_checkout(policy, root), identity, FIXTURE.read_bytes())
    out = tmp_path / "out"
    api.publish_catalogue(pub, out)
    if mutation == "changed": (out / "search.json").write_bytes(b"[]")
    if mutation == "added": (out / "unexpected").write_bytes(b"extra")
    if mutation == "missing": (out / "search.json").unlink()
    with pytest.raises(ValueError): api.publish_catalogue(pub, out, check=True)


@pytest.mark.parametrize("mutation", ["range", "range_column", "range_first_line", "duplicate", "references", "kind", "authority", "module", "order", "omission", "overflow", "utf8"])
def test_extraction_rejects_ambiguity_and_forgery(api, inputs, mutation):
    root, policy, identity = inputs
    raw = json.loads(FIXTURE.read_bytes())
    decl = raw["modules"][0]["declarations"][0]
    if mutation == "range": decl["range"]["end"]["byte"] = 999
    if mutation == "range_column": decl["range"]["start"]["column"] = 1
    if mutation == "range_first_line": decl["range"]["start"]["line"] = 1
    if mutation == "duplicate": raw["modules"][0]["declarations"].append(deepcopy(decl))
    if mutation == "references": decl["type_references"].append("B.T")
    if mutation == "kind": decl["kind"] = "recursor"
    if mutation == "authority": decl["verification_status"] = "VERIFIED"
    if mutation == "module": raw["modules"][0]["module"] = "Outside"
    if mutation == "order": raw["modules"].reverse()
    if mutation == "omission": raw["modules"][0]["omissions"].append({"qualified_name": "A.α", "kind": "definition", "reason": "GENERATED"})
    if mutation == "overflow": decl["statement"] = "x" * 800000
    payload = b"\xff" if mutation == "utf8" else json.dumps(raw).encode()
    with pytest.raises(ValueError): api.build_publication(policy, api.verify_source_checkout(policy, root), identity, payload)


def test_offline_harness_rejects_mutable_image_and_arbitrary_cache(api, tmp_path):
    for image in ["lean:latest", "lean:v4.34.1", "sha256:abc"]:
        with pytest.raises(ValueError): api.validate_image_digest(image)
    cache = tmp_path / ".lake"
    cache.mkdir()
    (cache / "artifact.olean").write_bytes(b"arbitrary")
    with pytest.raises(ValueError): api.verify_dependency_inventory(cache, {"files": []}, "0" * 64)


def test_cli_rejects_remote_and_moving_revision_without_network(tmp_path):
    cli = ROOT / "scripts/publish_mathlib_source_catalogue_v1.py"
    assert cli.is_file(), "publisher CLI missing"
    import sys
    result = subprocess.run([sys.executable, str(cli), "--checkout", "https://github.com/leanprover-community/mathlib4", "--revision", "main"], capture_output=True)
    assert result.returncode != 0


@pytest.fixture
def environment(api, inputs, tmp_path):
    root, policy, _ = inputs
    dependencies = tmp_path / "dependencies"
    dependencies.mkdir()
    entries = []
    for path in ["build/lib/lean/A.olean", "build/lib/lean/A.olean.server", "build/ir/A.c", "build/lib/lean/Outside.olean"]:
        f = dependencies / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"pinned cache bytes")
        entries.append({"path": path, "size_bytes": len(f.read_bytes()), "sha256": sha(f.read_bytes()), "mode": "100644"})
    inventory = {"schema": "mathgraph.catalogue-environment-inventory.v1", "acquisition": "FRESH_EXACT_COMMIT_CACHE",
                 "source_commit": policy["source"]["commit"], "source_tree": policy["source"]["tree"],
                 "packages": [], "files": sorted(entries, key=lambda f: f["path"])}
    path = tmp_path / "inventory.json"
    path.write_bytes(api.contract.canonical_bytes(inventory))
    config = {"image": "fixture@sha256:" + "b" * 64, "dependency_root": str(dependencies), "inventory": str(path),
              "dependency_inventory_sha256": sha(path.read_bytes())}
    return dependencies, inventory, config


@pytest.mark.parametrize("mutation", ["changed", "extra", "missing", "symlink", "receipt", "order", "executable"])
def test_dependency_inventory_rejects_unbound_state(api, environment, mutation):
    root, inventory, config = environment
    first = root / inventory["files"][0]["path"]
    if mutation == "changed": first.write_bytes(b"tampered")
    if mutation == "extra": (root / "extra.olean").write_bytes(b"unbound")
    if mutation == "missing": first.unlink()
    if mutation == "symlink":
        first.unlink()
        first.symlink_to(root / "missing")
    if mutation == "receipt": inventory["acquisition"] = "ARBITRARY_EXISTING_BUILD"
    if mutation == "order": inventory["files"].reverse()
    if mutation == "executable": first.chmod(0o755)
    with pytest.raises(ValueError): api.verify_dependency_inventory(root, inventory, sha(api.contract.canonical_bytes(inventory)))


def test_harness_rebuilds_selected_origins_and_denies_container_network(api, inputs, environment, git_dependency, monkeypatch):
    root, policy, _ = inputs
    dependencies, inventory, config = environment
    package = inventory["packages"][0]
    (root / "lake-manifest.json").write_text(json.dumps({"packages": [{"name": package["name"], "rev": package["commit"], "url": package["repository"]}]}))
    git(root, "add", "lake-manifest.json")
    git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "lock dependency")
    for field, rev in [("commit", "HEAD"), ("tree", "HEAD^{tree}")]:
        policy["source"][field] = inventory["source_" + field] = git(root, "rev-parse", rev)
    policy["source"]["lake_manifest"]["sha256"] = sha((root / "lake-manifest.json").read_bytes())
    Path(config["inventory"]).write_bytes(api.contract.canonical_bytes(inventory))
    config["dependency_inventory_sha256"] = sha(Path(config["inventory"]).read_bytes())
    source = api.verify_source_checkout(policy, root)
    real_run = subprocess.run
    commands = []
    def docker_boundary(command, **kwargs):
        if command[0] != "docker": return real_run(command, **kwargs)
        commands.append(command)
        assert command[command.index("--network") + 1] == "none"
        assert command[command.index("--pull") + 1] == "never"
        assert "--read-only" in command
        container_env = dict(command[i + 1].split("=", 1) for i, arg in enumerate(command) if arg == "--env")
        assert container_env["GIT_CONFIG_COUNT"] == "2"
        assert container_env["GIT_CONFIG_KEY_0"] == "credential.helper"
        assert container_env["GIT_CONFIG_VALUE_0"] == ""
        assert container_env["GIT_CONFIG_KEY_1"] == "safe.directory"
        assert container_env["GIT_CONFIG_VALUE_1"] == "/work/.lake/packages/dep"
        assert container_env["GIT_CONFIG_GLOBAL"] == "/dev/null"
        assert container_env["GIT_CONFIG_NOSYSTEM"] == "1"
        mounts = [command[i + 1] for i, arg in enumerate(command) if arg == "--mount"]
        assert any("dst=/verified-source,readonly" in m for m in mounts)
        assert any("dst=/verified-dependencies,readonly" in m for m in mounts)
        def mount_path(target):
            mount = next(m for m in mounts if f"dst={target}" in m)
            return Path(mount.split("src=", 1)[1].split(",", 1)[0])
        snapshot = mount_path("/work")
        assert mount_path("/verified-source") != root
        assert mount_path("/verified-dependencies") != dependencies
        assert not (mount_path("/verified-source") / ".git").exists()
        assert not (mount_path("/verified-dependencies") / "packages/dep/.git").exists()
        assert any(m.endswith("dst=/work/.lake/packages/dep/.git,readonly") for m in mounts)
        assert snapshot != root
        assert not (snapshot / ".lake/build/lib/lean/A.olean").exists()
        assert not (snapshot / ".lake/build/lib/lean/A.olean.server").exists()
        assert not (snapshot / ".lake/build/ir/A.c").exists()
        assert (snapshot / ".lake/build/lib/lean/Outside.olean").read_bytes() == b"pinned cache bytes"
        assert (snapshot / "A.lean").read_bytes() == (root / "A.lean").read_bytes()
        if len(commands) == 1:
            assert any(m.endswith("dst=/work") for m in mounts)
            assert not any("dst=/output" in m for m in mounts)
        else:
            assert any(m.endswith("dst=/work,readonly") for m in mounts)
            (mount_path("/output") / "extraction.json").write_bytes(FIXTURE.read_bytes())
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(api.subprocess, "run", docker_boundary)
    assert api.run_offline_extraction(source, ROOT / "tools/mathlib_catalogue/Extract.lean", ["A", "B"], config) == FIXTURE.read_bytes()
    assert len(commands) == 2
    assert (dependencies / "build/lib/lean/A.olean").exists()


@pytest.mark.parametrize("coordinates", [
    {"start": {"line": 1, "column": 0, "byte": 0}, "end": {"line": 2, "column": 3, "byte": 7}},
    {"start": {"line": 1, "column": 1, "byte": 1}, "end": {"line": 2, "column": 4, "byte": 8}},
])
def test_range_validation_checks_real_utf8_and_newline_bytes(api, coordinates):
    # UTF-8 bytes: a(1), α(2), newline(1), β(2), b(1), newline(1).
    raw = "aα\nβb\n".encode()
    if coordinates["end"]["byte"] == 7:
        api._range_bytes(coordinates, raw)
    else:
        with pytest.raises(ValueError): api._range_bytes(coordinates, raw)


def test_range_cannot_split_utf8_character(api):
    with pytest.raises(ValueError):
        api._range_bytes({"start": {"line": 1, "column": 0, "byte": 0}, "end": {"line": 1, "column": 1, "byte": 1}}, "α".encode())


@pytest.mark.parametrize("mutation", [None, "dirty", "commit", "digest", "missing_file", "authority"])
def test_producer_identity_requires_clean_commit_and_all_source_bytes(api, inputs, tmp_path, mutation):
    _, _, identity = inputs
    producer = tmp_path / "producer"
    producer.mkdir()
    paths = ["mathgraph/source_catalogue_publisher_v1.py", "mathgraph_protocol/json_strict.py",
             "mathgraph_protocol/source_catalogue_v1.py", "scripts/publish_mathlib_source_catalogue_v1.py",
             "scripts/run_mathlib_source_catalogue_offline_v1.py", "tools/mathlib_catalogue/Extract.lean"]
    for path in paths:
        f = producer / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes((ROOT / path).read_bytes())
    git(producer, "init", "-q")
    git(producer, "add", ".")
    git(producer, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "producer")
    identity["source_commit"] = git(producer, "rev-parse", "HEAD")
    identity["sources"] = [{"path": p, "sha256": sha((producer / p).read_bytes())} for p in paths]
    if mutation == "dirty": (producer / "unrelated.txt").write_text("dirty")
    if mutation == "commit": identity["source_commit"] = "0" * 40
    if mutation == "digest": identity["sources"][0]["sha256"] = "0" * 64
    if mutation == "missing_file": identity["sources"].pop()
    if mutation == "authority": identity["environment"]["authority"] = "VERIFIED"
    if mutation is None:
        api.verify_extractor_identity(identity, producer)
    else:
        with pytest.raises(ValueError): api.verify_extractor_identity(identity, producer)


@pytest.fixture
def git_dependency(api, environment):
    root, inventory, config = environment
    package = root / "packages/dep"
    package.mkdir(parents=True)
    for path, contents in {"Dep.lean": "def depValue : Nat := 7\n", "lakefile.toml": 'name = "dep"\n[[lean_lib]]\nname = "Dep"\n',
                           ".gitignore": ".lake\n"}.items():
        (package / path).write_text(contents)
    git(package, "init", "-q")
    git(package, "add", ".")
    git(package, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "dependency")
    repository = "https://example.invalid/dep"
    git(package, "remote", "add", "origin", repository)
    record = {"name": "dep", "path": "packages/dep", "commit": git(package, "rev-parse", "HEAD"),
              "tree": git(package, "rev-parse", "HEAD^{tree}"), "repository": repository}
    record["git_metadata_sha256"] = api.git_metadata_digest(api.sanitized_git_files(package, record))
    inventory["packages"] = [record]
    for path in sorted(package.iterdir()):
        if path.is_file(): inventory["files"].append({"path": path.relative_to(root).as_posix(), "sha256": sha(path.read_bytes()),
                                                   "size_bytes": path.stat().st_size, "mode": "100644"})
    inventory["files"].sort(key=lambda f: f["path"])
    return package, root, inventory


@pytest.mark.parametrize("mutation", [None, "missing_git", "commit", "remote", "dirty", "git_escape", "extra_git", "metadata_digest"])
def test_dependency_git_identity_is_verified(api, git_dependency, tmp_path, mutation):
    package, root, inventory = git_dependency
    if mutation == "missing_git": (package / ".git").rename(tmp_path / "removed-git")
    if mutation == "commit": inventory["packages"][0]["commit"] = "0" * 40
    if mutation == "remote": git(package, "remote", "set-url", "origin", "https://example.invalid/wrong")
    if mutation == "dirty": (package / "Dep.lean").write_text("def changed := 1\n")
    if mutation == "git_escape":
        (package / ".git").rename(tmp_path / "external-git")
        (package / ".git").symlink_to(tmp_path / "external-git", target_is_directory=True)
    if mutation == "extra_git": (root / ".git").mkdir()
    if mutation == "metadata_digest": inventory["packages"][0]["git_metadata_sha256"] = "0" * 64
    digest = sha(api.contract.canonical_bytes(inventory))
    if mutation is None: api.verify_dependency_inventory(root, inventory, digest)
    else:
        with pytest.raises(ValueError): api.verify_dependency_inventory(root, inventory, digest)


def test_sanitized_dependency_git_supports_real_offline_lake_build(api, git_dependency, tmp_path):
    import shutil
    package, _, inventory = git_dependency
    record = inventory["packages"][0]
    git(package, "config", "credential.helper", "!secret-helper-must-never-be-copied")
    (package / ".git/hooks/private-token").write_text("secret")
    files = api.sanitized_git_files(package, record)
    assert api.git_metadata_digest(files) == record["git_metadata_sha256"]
    assert not any(b"secret" in raw for _, raw in files)
    project = tmp_path / "actual-lake"
    project.mkdir()
    (project / "lakefile.toml").write_text('name = "offline_fixture"\n[[lean_lib]]\nname = "Main"\n[[require]]\nname = "dep"\ngit = "https://example.invalid/dep"\nrev = "' + record["commit"] + '"\n')
    (project / "lean-toolchain").write_text("leanprover/lean4:v4.34.1\n")
    (project / "Main.lean").write_text("import Dep\nexample : depValue = 7 := rfl\n")
    (project / "lake-manifest.json").write_text(json.dumps({"version": "1.2.0", "name": "offline_fixture", "lakeDir": ".lake", "packagesDir": ".lake/packages", "packages": [{"name": "dep", "type": "git", "url": record["repository"], "rev": record["commit"], "inputRev": record["commit"], "scope": "", "subDir": None, "manifestFile": "lake-manifest.json", "configFile": "lakefile.toml", "inherited": False}]}))
    target = project / ".lake/packages/dep"
    shutil.copytree(package, target, ignore=shutil.ignore_patterns(".git"))
    for relative, raw in files:
        destination = target / ".git" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        destination.chmod(0o444)
    (target / ".git/refs").mkdir(exist_ok=True)
    assert git(target, "rev-parse", "HEAD") == record["commit"]
    assert not git(target, "diff", "--exit-code", "HEAD")
    lean = Path(os.environ["MATHGRAPH_CATALOGUE_LEAN"])
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "LEAN_", "LAKE_"))}
    env.update(api.git_runtime_environment(inventory["packages"], str(project / ".lake")))
    env.update(PATH=str(lean.parent) + os.pathsep + os.environ["PATH"], GIT_TEST_ASSUME_DIFFERENT_OWNER="1")
    result = subprocess.run([str(lean.with_name("lake")), "build", "Main"], cwd=project, env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / ".lake/build/lib/lean/Main.olean").is_file()


@pytest.mark.parametrize("name", ["*", "dep/*", "dep,readonly"])
def test_runtime_git_allowlist_rejects_nonliteral_package_roots(api, name):
    with pytest.raises(ValueError):
        api.git_runtime_environment([{"name": name, "path": "packages/" + name}])
