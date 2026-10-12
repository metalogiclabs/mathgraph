"""The producer rejects unpinned bytes and cannot promote source data to evidence."""
from copy import deepcopy
import hashlib
import importlib
import importlib.util
import json
import os
import shutil
import stat
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
    assert sha(api.contract.canonical_bytes(p)) == "3f5f60ffbcb64207f360f5ffdc982bd6e11f7709a0525c033e80729ad215f320"
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


def test_tracked_selected_source_symlink_is_still_rejected(api, inputs):
    root, policy, _ = inputs
    (root / "A.lean").unlink()
    (root / "A.lean").symlink_to("B.lean")
    git(root, "add", "A.lean")
    git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-qm", "selected source link")
    policy["source"]["commit"] = git(root, "rev-parse", "HEAD")
    policy["source"]["tree"] = git(root, "rev-parse", "HEAD^{tree}")
    policy["modules"][0]["sha256"] = sha((root / "B.lean").read_bytes())
    policy["modules"][0]["size_bytes"] = len((root / "B.lean").read_bytes())
    with pytest.raises(ValueError, match="symlink input is not admitted"):
        api.verify_source_checkout(policy, root)


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


def test_container_output_leaf_is_nonowner_writable_then_sealed_and_closed(api, tmp_path):
    parent = tmp_path / "private-parent"
    parent.mkdir(mode=0o700)
    leaf = parent / "plan"
    api._prepare_container_output(leaf)
    assert stat.S_IMODE(parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(leaf.stat().st_mode) == 0o733
    (leaf / "order.json").write_text('{"modules":[]}')
    assert [path.name for path in api._seal_container_output(
        leaf, {"order.json"}, {"order.json"})] == ["order.json"]
    assert stat.S_IMODE(leaf.stat().st_mode) == 0o700
    with pytest.raises(ValueError):
        api._prepare_container_output(leaf)


@pytest.mark.parametrize("unsafe", ["extra", "directory", "symlink"])
def test_container_output_leaf_rejects_any_unadmitted_output(api, tmp_path, unsafe):
    leaf = tmp_path / "output"
    api._prepare_container_output(leaf)
    (leaf / "extraction.json").write_bytes(b"{}")
    if unsafe == "extra":
        (leaf / "unexpected").write_bytes(b"extra")
    elif unsafe == "directory":
        (leaf / "unexpected").mkdir()
    else:
        (leaf / "unexpected").symlink_to("extraction.json")
    with pytest.raises(ValueError):
        api._seal_container_output(leaf, {"extraction.json"}, {"extraction.json"})
    assert stat.S_IMODE(leaf.stat().st_mode) == 0o700


@pytest.fixture
def environment(api, inputs, tmp_path):
    root, policy, _ = inputs
    dependencies = tmp_path / "dependencies"
    dependencies.mkdir()
    entries = []
    for path in ["build/lib/lean/A.olean", "build/lib/lean/A.olean.server", "build/lib/lean/A.olean.private", "build/lib/lean/A.ilean", "build/lib/lean/A.trace", "build/lib/lean/A.olean.hash", "build/ir/A.c", "build/ir/A.c.o", "build/lib/lean/Outside.olean"]:
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


@pytest.mark.parametrize("external_toolchain", [False, True])
def test_harness_rebuilds_selected_origins_and_denies_container_network(api, inputs, environment, git_dependency, monkeypatch, local_toolchain, external_toolchain):
    root, policy, _ = inputs
    dependencies, inventory, config = environment
    package_cache = dependencies / "packages/dep/.lake/build/lib/lean/A.olean"
    package_cache.parent.mkdir(parents=True, exist_ok=True)
    package_cache.write_bytes(b"pinned cache bytes")
    inventory["files"].append({"path": "packages/dep/.lake/build/lib/lean/A.olean", "sha256": sha(package_cache.read_bytes()), "size_bytes": 18, "mode": "100644"})
    inventory["files"].sort(key=lambda f: f["path"])
    package = inventory["packages"][0]
    (root / "lake-manifest.json").write_text(json.dumps({"packages": [{"name": package["name"], "rev": package["commit"], "url": package["repository"]}]}))
    git(root, "add", "lake-manifest.json")
    git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "lock dependency")
    for field, rev in [("commit", "HEAD"), ("tree", "HEAD^{tree}")]:
        policy["source"][field] = inventory["source_" + field] = git(root, "rev-parse", rev)
    policy["source"]["lake_manifest"]["sha256"] = sha((root / "lake-manifest.json").read_bytes())
    Path(config["inventory"]).write_bytes(api.contract.canonical_bytes(inventory))
    config["dependency_inventory_sha256"] = sha(Path(config["inventory"]).read_bytes())
    if external_toolchain:
        toolchain, receipt, profile = local_toolchain
        monkeypatch.setattr(api, "TOOLCHAIN_PROFILE", profile)
        config.update(image=api.BASE_IMAGE, toolchain={"root": str(toolchain), "inventory": str(receipt)})
    source = api.verify_source_checkout(policy, root)
    real_run = subprocess.run
    commands = []
    def docker_boundary(command, **kwargs):
        if command[0] != "docker": return real_run(command, **kwargs)
        if command[1:3] == ["image", "inspect"]:
            assert command[-1] == api.BASE_IMAGE
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"id": api.BASE_IMAGE_CONFIG, "os": "linux", "arch": "amd64"}).encode())
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
        writable = [mount for mount in mounts if not mount.endswith(",readonly")]
        assert len(writable) == 1
        writable_root = Path(writable[0].split("src=", 1)[1].split(",", 1)[0])
        assert writable[0].split("dst=", 1)[1] in {"/plan", "/module-output", "/output"}
        assert stat.S_IMODE(writable_root.stat().st_mode) == 0o733
        assert list(writable_root.iterdir()) == []
        if external_toolchain:
            assert any(m.endswith("dst=/opt/lean,readonly") for m in mounts)
            assert container_env["PATH"].startswith("/opt/lean/bin:")
            assert "LD_LIBRARY_PATH" not in container_env and "ELAN_HOME" not in container_env
            assert command[command.index("--platform") + 1] == "linux/amd64"
            assert "/opt/lean/bin/lean" in command[command.index("-c") + 1]
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
        assert any(m.endswith("dst=/work,readonly") for m in mounts)
        for source_tree in [snapshot / ".lake", mount_path("/verified-dependencies")]:
            selected = [p for p in source_tree.rglob("*") if p.is_file() and p.name.startswith("A.")]
            assert all(p.read_bytes() == b"fresh compiled output" for p in selected), "selected cached artifacts remain visible"
            if len(commands) == 1 or source_tree == mount_path("/verified-dependencies"): assert not selected
        assert (snapshot / ".lake/build/lib/lean/Outside.olean").read_bytes() == b"pinned cache bytes"
        assert (snapshot / "A.lean").read_bytes() == (root / "A.lean").read_bytes()
        assert (snapshot / ".lake/packages/dep/docs/README.md").is_symlink()
        assert os.readlink(snapshot / ".lake/packages/dep/docs/README.md") == "../README.md"
        assert (mount_path("/verified-dependencies") / "packages/dep/docs/README.md").is_symlink()
        if len(commands) == 1:
            assert "CompileOrder.lean" in command[-4]
            (mount_path("/plan") / "order.json").write_text('{"modules":["B","A"]}')
            assert not any("dst=/output" in m for m in mounts)
        elif len(commands) < 4:
            assert command[-1] == ("B.lean" if len(commands) == 2 else "A.lean")
            assert any(m.endswith("dst=/compiled,readonly") for m in mounts)
            assert "-DautoImplicit=false" in command[-3]
            (mount_path("/module-output") / "module.olean").write_bytes(b"fresh compiled output")
        else:
            assert (mount_path("/compiled") / "A.olean").read_bytes() == b"fresh compiled output"
            assert (mount_path("/compiled") / "B.olean").read_bytes() == b"fresh compiled output"
            (mount_path("/output") / "extraction.json").write_bytes(FIXTURE.read_bytes())
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(api.subprocess, "run", docker_boundary)
    assert api.run_offline_extraction(source, ROOT / "tools/mathlib_catalogue/Extract.lean", ["A", "B"], config) == FIXTURE.read_bytes()
    assert len(commands) == 4
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
    paths = ["mathgraph/source_catalogue_publisher_v1.py", "mathgraph_protocol/__init__.py",
             "mathgraph_protocol/discovery_ranking.py", "mathgraph_protocol/json_strict.py",
             "mathgraph_protocol/source_catalogue_v1.py", "scripts/catalogue_bootstrap_v1.py", "scripts/publish_mathlib_source_catalogue_v1.py",
             "scripts/run_mathlib_source_catalogue_offline_v1.py", "tools/mathlib_catalogue/CompileOrder.lean", "tools/mathlib_catalogue/Extract.lean"]
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
                           ".gitignore": ".lake\n", "README.md": "dependency documentation\n"}.items():
        (package / path).write_text(contents)
    (package / "docs").mkdir()
    (package / "docs/README.md").symlink_to("../README.md")
    git(package, "init", "-q")
    git(package, "add", ".")
    git(package, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "dependency")
    repository = "https://example.invalid/dep"
    git(package, "remote", "add", "origin", repository)
    record = {"name": "dep", "path": "packages/dep", "commit": git(package, "rev-parse", "HEAD"),
              "tree": git(package, "rev-parse", "HEAD^{tree}"), "repository": repository}
    record["git_metadata_sha256"] = api.git_metadata_digest(api.sanitized_git_files(package, record))
    inventory["packages"] = [record]
    for path in sorted(package.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if ".git" in path.relative_to(package).parts:
            continue
        if path.is_symlink():
            target = os.readlink(path)
            raw = target.encode()
            inventory["files"].append({"path": relative, "sha256": sha(raw),
                                       "size_bytes": len(raw), "mode": "120000", "target": target})
        elif path.is_file():
            inventory["files"].append({"path": relative, "sha256": sha(path.read_bytes()),
                                       "size_bytes": path.stat().st_size, "mode": "100644"})
    inventory["files"].sort(key=lambda f: f["path"])
    return package, root, inventory


@pytest.fixture
def git_dependency_with_tracked_symlink(tmp_path):
    package = tmp_path / "linked-dependency"
    package.mkdir()
    (package / "Target.lean").write_text("def linkedValue : Nat := 11\n")
    (package / "Alias.lean").symlink_to("Target.lean")
    git(package, "init", "-q")
    git(package, "add", ".")
    git(package, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-qm", "tracked relative link")
    repository = "https://example.invalid/linked-dependency"
    git(package, "remote", "add", "origin", repository)
    return package, {"name": "linked-dependency", "path": "packages/linked-dependency",
                     "commit": git(package, "rev-parse", "HEAD"),
                     "tree": git(package, "rev-parse", "HEAD^{tree}"), "repository": repository}


def test_tracked_dependency_symlink_is_preserved_in_sanitized_identity(
        api, git_dependency_with_tracked_symlink, tmp_path):
    package, record = git_dependency_with_tracked_symlink
    files = api.sanitized_git_files(package, record)
    rebuilt = tmp_path / "rebuilt"
    shutil.copytree(package, rebuilt, ignore=shutil.ignore_patterns(".git"), symlinks=True)
    for relative, raw in files:
        destination = rebuilt / ".git" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    (rebuilt / ".git/refs").mkdir(exist_ok=True)
    assert (rebuilt / "Alias.lean").is_symlink()
    assert os.readlink(rebuilt / "Alias.lean") == "Target.lean"
    assert git(rebuilt, "diff", "--exit-code", "HEAD") == ""


@pytest.mark.parametrize("mutation", ["absolute", "escape", "missing", "untracked", "chain", "git", "target_bytes", "link_blob"])
def test_dependency_symlink_declines_unsafe_or_unbound_targets_with_context(
        api, git_dependency_with_tracked_symlink, tmp_path, mutation):
    package, record = git_dependency_with_tracked_symlink
    link = package / "Alias.lean"
    link.unlink()
    if mutation == "absolute":
        outside = tmp_path / "absolute.lean"
        outside.write_text("def outside := 1\n")
        link.symlink_to(outside)
    elif mutation == "escape":
        outside = package.parent / "outside.lean"
        outside.write_text("def outside := 1\n")
        link.symlink_to("../outside.lean")
    elif mutation == "missing":
        link.symlink_to("Missing.lean")
    elif mutation == "untracked":
        (package / "Untracked.lean").write_text("def untracked := 1\n")
        link.symlink_to("Untracked.lean")
    elif mutation == "chain":
        (package / "Second.lean").symlink_to("Target.lean")
        link.symlink_to("Second.lean")
        git(package, "add", "Second.lean")
    elif mutation == "git":
        link.symlink_to(".git/config")
    elif mutation == "target_bytes":
        link.symlink_to("Target.lean")
        (package / "Target.lean").write_text("def changedTarget := 12\n")
    else:
        link.symlink_to("Target.lean")
    if mutation not in {"link_blob", "target_bytes"}:
        git(package, "add", "Alias.lean")
        git(package, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "mutated tracked link")
        record.update(commit=git(package, "rev-parse", "HEAD"), tree=git(package, "rev-parse", "HEAD^{tree}"))
    elif mutation == "link_blob":
        link.unlink()
        link.symlink_to("Missing.lean")
    with pytest.raises(ValueError, match=r"package=linked-dependency path=Alias\.lean mode=120000"):
        api.sanitized_git_files(package, record)


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


@pytest.mark.parametrize("mutation", ["target", "digest", "mode", "outside_package"])
def test_dependency_inventory_rejects_unbound_symlink_semantics(api, git_dependency, mutation):
    package, root, inventory = git_dependency
    link = next(entry for entry in inventory["files"] if entry["mode"] == "120000")
    if mutation == "target":
        link["target"] = "../Dep.lean"
        raw = link["target"].encode()
        link.update(sha256=sha(raw), size_bytes=len(raw))
    elif mutation == "digest":
        link["sha256"] = "0" * 64
    elif mutation == "mode":
        link.pop("target")
        link["mode"] = "100644"
    else:
        source = package / "docs/README.md"
        target = root / "outside-link"
        target.symlink_to(source)
        raw = os.readlink(target).encode()
        inventory["files"].append({"path": "outside-link", "sha256": sha(raw),
                                   "size_bytes": len(raw), "mode": "120000", "target": os.readlink(target)})
        inventory["files"].sort(key=lambda item: item["path"])
    with pytest.raises(ValueError):
        api.verify_dependency_inventory(root, inventory, sha(api.contract.canonical_bytes(inventory)))


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
    shutil.copytree(package, target, ignore=shutil.ignore_patterns(".git"), symlinks=True)
    for relative, raw in files:
        destination = target / ".git" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        destination.chmod(0o444)
    (target / ".git/refs").mkdir(exist_ok=True)
    assert git(target, "rev-parse", "HEAD") == record["commit"]
    assert not git(target, "diff", "--exit-code", "HEAD")
    assert (target / "docs/README.md").is_symlink()
    assert os.readlink(target / "docs/README.md") == "../README.md"
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


@pytest.fixture
def producer_checkout(api, inputs, tmp_path):
    _, _, identity = inputs
    root = tmp_path / "producer-checkout"
    paths = set(api.PRODUCER_FILES) | {"mathgraph_protocol/__init__.py", "mathgraph_protocol/discovery_ranking.py"}
    for relative in paths:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / relative).read_bytes())
    (root / ".gitignore").write_text("__pycache__/\n")
    (root / "unlisted.txt").write_text("tracked but not imported\n")
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "producer")
    identity["source_commit"] = git(root, "rev-parse", "HEAD")
    identity["sources"] = [{"path": p, "sha256": sha((root / p).read_bytes())} for p in api.PRODUCER_FILES]
    return root, identity


@pytest.mark.parametrize("cli", ["publish_mathlib_source_catalogue_v1.py", "run_mathlib_source_catalogue_offline_v1.py"])
@pytest.mark.parametrize("flag", ["--assume-unchanged", "--skip-worktree"])
def test_cli_declines_hidden_initializer_mutation_before_import(api, producer_checkout, inputs, environment, tmp_path, cli, flag):
    producer, identity = producer_checkout
    checkout, policy, _ = inputs
    _, _, config = environment
    marker = tmp_path / "initializer-ran"
    path = producer / "mathgraph_protocol/__init__.py"
    path.write_text(path.read_text() + f"\nfrom pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n")
    git(producer, "update-index", flag, "mathgraph_protocol/__init__.py")
    assert not git(producer, "status", "--porcelain")
    policy_path, identity_path, config_path = [tmp_path / name for name in ["policy.json", "identity.json", "config.json"]]
    for path, value in [(policy_path, policy), (identity_path, identity), (config_path, config)]: path.write_text(json.dumps(value))
    args = [sys.executable, str(producer / "scripts" / cli), "--checkout", str(checkout), "--source-policy", str(policy_path), "--extractor-identity", str(identity_path)]
    args += ["--output-dir", str(tmp_path / "out")] if cli.startswith("publish") else ["--environment", str(config_path), "--output", str(tmp_path / "out.json")]
    result = subprocess.run(args, env={**os.environ, "MATHGRAPH_CATALOGUE_ENVIRONMENT": str(config_path)}, capture_output=True, text=True)
    assert result.returncode != 0
    assert not marker.exists(), "unverified package initializer executed before producer verification"
    assert "producer" in result.stderr.lower()


@pytest.mark.parametrize("mode", ["publish", "extract", "remote", "hidden_unlisted", "poison_bytecode"])
def test_complete_cli_uses_verified_sources_without_acquisition(api, producer_checkout, inputs, environment, tmp_path, mode):
    producer, identity = producer_checkout
    checkout, policy, _ = inputs
    _, _, config = environment
    identity["environment"] = {"image": config["image"], "dependency_inventory_sha256": config["dependency_inventory_sha256"], "authority": "NONE"}
    marker = tmp_path / "poison-ran"
    if mode == "hidden_unlisted":
        (producer / "unlisted.txt").write_text("mutated")
        git(producer, "update-index", "--skip-worktree", "unlisted.txt")
        assert not git(producer, "status", "--porcelain")
    if mode == "poison_bytecode":
        import marshal
        import struct
        path = producer / "mathgraph_protocol/__init__.py"
        cache = Path(importlib.util.cache_from_source(str(path)))
        cache.parent.mkdir()
        payload = compile(f"from pathlib import Path; Path({str(marker)!r}).write_text('poison')", str(path), "exec")
        cache.write_bytes(importlib.util.MAGIC_NUMBER + struct.pack("<III", 0, int(path.stat().st_mtime), path.stat().st_size) + marshal.dumps(payload))
        assert not git(producer, "status", "--porcelain")
    policy_path, identity_path, config_path = [tmp_path / name for name in ["policy.json", "identity.json", "config.json"]]
    for path, value in [(policy_path, policy), (identity_path, identity), (config_path, config)]: path.write_text(json.dumps(value))
    binaries = tmp_path / "bin"
    binaries.mkdir()
    log = tmp_path / "commands.jsonl"
    common = "import json,os,sys\nfrom pathlib import Path\nwith open(os.environ['CATALOGUE_TEST_LOG'],'a') as f: f.write(json.dumps(sys.argv)+'\\n')\n"
    scripts = {
        "git": common + "assert not set(sys.argv[1:]) & {'clone','fetch','pull'}\nos.execv(" + repr(shutil.which("git")) + ", ['git',*sys.argv[1:]])\n",
        "docker": common + "args=sys.argv[1:]\nassert args[args.index('--network')+1]=='none' and args[args.index('--pull')+1]=='never'\nmounts=[dict(x.split('=',1) if '=' in x else (x,True) for x in args[i+1].split(',')) for i,a in enumerate(args) if a=='--mount']\npaths={m['dst']:Path(m['src']) for m in mounts}\nassert next(m for m in mounts if m['dst']=='/work')['readonly']\nif '/plan' in paths: (paths['/plan']/'order.json').write_text('{\"modules\":[\"B\",\"A\"]}')\nelif '/module-output' in paths: (paths['/module-output']/'module.olean').write_bytes(b'fixture')\nelse: (paths['/output']/'extraction.json').write_bytes(Path(os.environ['CATALOGUE_TEST_RAW']).read_bytes())\n",
        "curl": common + "raise SystemExit('acquisition forbidden')\n", "wget": common + "raise SystemExit('acquisition forbidden')\n"}
    for name, body in scripts.items():
        path = binaries / name
        path.write_text("#!" + sys.executable + "\n" + body)
        path.chmod(0o755)
    cli = "run_mathlib_source_catalogue_offline_v1.py" if mode == "extract" else "publish_mathlib_source_catalogue_v1.py"
    args = [sys.executable, str(producer / "scripts" / cli), "--checkout", "https://example.invalid/source" if mode == "remote" else str(checkout), "--source-policy", str(policy_path), "--extractor-identity", str(identity_path)]
    args += ["--environment", str(config_path), "--output", str(tmp_path / "extraction.json")] if mode == "extract" else ["--output-dir", str(tmp_path / "publication")]
    env = {**os.environ, "PATH": str(binaries) + os.pathsep + os.environ["PATH"], "MATHGRAPH_CATALOGUE_ENVIRONMENT": str(config_path), "CATALOGUE_TEST_LOG": str(log), "CATALOGUE_TEST_RAW": str(FIXTURE)}
    result = subprocess.run(args, env=env, capture_output=True, text=True)
    assert not marker.exists(), "unverified bytecode ran"
    commands = [json.loads(line) for line in log.read_text().splitlines()]
    assert all(not set(c[1:]) & {"clone", "fetch", "pull"} and Path(c[0]).name not in {"curl", "wget"} for c in commands)
    if mode in {"remote", "hidden_unlisted"}:
        assert result.returncode != 0
        assert not any(Path(c[0]).name == "docker" for c in commands)
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        assert len([c for c in commands if Path(c[0]).name == "docker"]) == 4
        if mode == "extract": assert (tmp_path / "extraction.json").read_bytes() == FIXTURE.read_bytes()
        else: api.contract.validate_manifest((tmp_path / "publication/manifest.json").read_bytes())


@pytest.fixture
def local_toolchain(api, tmp_path):
    root = tmp_path / "toolchain"
    (root / "bin").mkdir(parents=True)
    (root / "bin/lean").write_bytes(b"fixture lean")
    root.chmod(0o755)
    (root / "bin").chmod(0o755)
    (root / "bin/lean").chmod(0o755)
    (root / "lean-link").symlink_to("bin/lean")
    if hasattr(os, "lchmod"): os.lchmod(root / "lean-link", 0o777)
    entries = [{"kind": "directory", "mode": "0755", "path": "."}, {"kind": "directory", "mode": "0755", "path": "bin"},
               {"kind": "file", "mode": "0755", "path": "bin/lean", "sha256": sha(b"fixture lean"), "size_bytes": 12},
               {"kind": "symlink", "mode": "0777", "path": "lean-link", "target": "bin/lean"}]
    receipt = tmp_path / "toolchain-inventory.json"
    raw = api.contract.canonical_bytes({"schema": "mathgraph.toolchain-tree.v1", "entries": entries})
    receipt.write_bytes(raw)
    profile = dict(inventory_sha256=sha(raw), inventory_size_bytes=len(raw), entry_count=4, file_count=1, directory_count=2, symlink_count=1, regular_bytes=12,
                   lean_commit="5045d0056413266e57c625dcd7c365b10e377c52", authority="NONE")
    return root, receipt, profile


@pytest.mark.parametrize("mutation", [None, "bytes", "mode", "extra", "missing", "escape", "digest", "count", "root_symlink"])
def test_toolchain_tree_requires_exact_inventory(api, local_toolchain, tmp_path, mutation):
    assert hasattr(api, "verify_toolchain_tree"), "toolchain tree verifier missing"
    root, receipt, profile = local_toolchain
    if mutation == "bytes": (root / "bin/lean").write_bytes(b"altered lean")
    if mutation == "mode": (root / "bin/lean").chmod(0o644)
    if mutation == "extra": (root / "extra").write_text("extra")
    if mutation == "missing": (root / "bin/lean").unlink()
    if mutation == "escape":
        (root / "lean-link").unlink()
        (root / "lean-link").symlink_to("../toolchain-inventory.json")
    if mutation == "digest": profile["inventory_sha256"] = "0" * 64
    if mutation == "count": profile["file_count"] += 1
    if mutation == "root_symlink":
        link = tmp_path / "toolchain-link"
        link.symlink_to(root, target_is_directory=True)
        root = link
    if mutation is None: api.verify_toolchain_tree(root, receipt, profile)
    else:
        with pytest.raises((ValueError, OSError)): api.verify_toolchain_tree(root, receipt, profile)


@pytest.mark.parametrize("mutation", [None, "archive", "tree", "authority", "platform", "base", "missing"])
def test_external_toolchain_identity_is_exact_and_non_authoritative(api, inputs, mutation):
    identity = inputs[2]
    identity["environment"].update(image=api.BASE_IMAGE, toolchain=deepcopy(api.TOOLCHAIN_PROFILE))
    profile = identity["environment"]["toolchain"]
    assert profile["archive_sha256"] == "47bf4bbd78f70c2e9670598ab7124d92b6efb7330ff33e5fbb4030f6fd72e4e4"
    assert profile["inventory_sha256"] == "dce115ba9934df63c9c59f53297d90ffefa702b3736cab41eac4900351754c88"
    assert (profile["archive_size_bytes"], profile["inventory_size_bytes"], profile["entry_count"], profile["regular_bytes"]) == (580432872, 3206496, 18381, 3068313425)
    assert (profile["file_count"], profile["directory_count"], profile["symlink_count"]) == (17738, 631, 12)
    assert profile["base_image"] == "docker.io/library/buildpack-deps@sha256:17923645546d74acef88727bce62c23bbaed953fc7097c41a8b777bba3ca98de"
    assert profile["base_image_config"] == "sha256:12d2284be437af82eaf8ebf5d1965223b8f259d82c1a523fff8e46de50ed5b54"
    if mutation == "archive": profile["archive_sha256"] = "0" * 64
    if mutation == "tree": profile["inventory_sha256"] = "0" * 64
    if mutation == "authority": profile["authority"] = "VERIFIED"
    if mutation == "platform": profile["platform"] = "linux/arm64"
    if mutation == "base": identity["environment"]["image"] = "fixture@sha256:" + "b" * 64
    if mutation == "missing": del identity["environment"]["toolchain"]
    if mutation is None: assert api._environment(identity)["toolchain"]["authority"] == "NONE"
    else:
        with pytest.raises(ValueError): api._environment(identity)


@pytest.mark.parametrize("mutation", ["config", "architecture", "os", "missing_toolchain", "wrong_image"])
def test_external_toolchain_declines_before_build_for_wrong_base(api, inputs, environment, local_toolchain, monkeypatch, mutation):
    root, policy, _ = inputs
    config = environment[2]
    toolchain, receipt, profile = local_toolchain
    monkeypatch.setattr(api, "TOOLCHAIN_PROFILE", profile)
    config.update(image=api.BASE_IMAGE, toolchain={"root": str(toolchain), "inventory": str(receipt)})
    inspected = {"id": api.BASE_IMAGE_CONFIG, "os": "linux", "arch": "amd64"}
    if mutation == "config": inspected["id"] = "sha256:" + "0" * 64
    if mutation == "architecture": inspected["arch"] = "arm64"
    if mutation == "os": inspected["os"] = "windows"
    if mutation == "missing_toolchain": del config["toolchain"]
    if mutation == "wrong_image": config["image"] = "fixture@sha256:" + "b" * 64
    source = api.verify_source_checkout(policy, root)
    real_run = subprocess.run
    calls = []
    def boundary(command, **kwargs):
        if command[0] != "docker": return real_run(command, **kwargs)
        calls.append(command)
        assert command[1:3] == ["image", "inspect"], "build must not start"
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(inspected).encode())
    monkeypatch.setattr(api.subprocess, "run", boundary)
    with pytest.raises(ValueError): api.run_offline_extraction(source, ROOT / "tools/mathlib_catalogue/Extract.lean", ["A", "B"], config)
    assert len(calls) == (0 if mutation in {"missing_toolchain", "wrong_image"} else 1)
