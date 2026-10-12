#!/usr/bin/env python3
"""Acquire, generate, and prequalify the bounded Mathlib source catalogue.

Acquisition is deliberately separate from the Task 2 producer.  This wrapper
starts from new roots, pins every source/runtime input, enters the producer's
network-denied/read-only Docker boundary twice, and emits only the compact
publication plus small qualification reports.  The separate independent
consumer workflow is still required before publication is qualified.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
PRODUCER_COMMIT = "d98f217d7e43cf74bfdb180dd953e98a29388f48"
MATHLIB_REPOSITORY = "https://github.com/leanprover-community/mathlib4"
SOURCE_POLICY_PATH = "catalogues/mathlib-v4.34.1-foundations-v1.source.json"
PRODUCER_FILES = (
    "mathgraph/source_catalogue_publisher_v1.py",
    "mathgraph_protocol/__init__.py",
    "mathgraph_protocol/discovery_ranking.py",
    "mathgraph_protocol/json_strict.py",
    "mathgraph_protocol/source_catalogue_v1.py",
    "scripts/catalogue_bootstrap_v1.py",
    "scripts/publish_mathlib_source_catalogue_v1.py",
    "scripts/run_mathlib_source_catalogue_offline_v1.py",
    "tools/mathlib_catalogue/CompileOrder.lean",
    "tools/mathlib_catalogue/Extract.lean",
)
QUALIFICATION_WRAPPER_FILES = (
    ".github/workflows/mathgraph-source-catalogue-v1.yml",
    "conformance/source_catalogue_v1/consumer.py",
    "conformance/source_catalogue_v1/run_isolated.py",
    "conformance/source_catalogue_v1/stdlib_conformance.py",
    "conformance/source_catalogue_v1/test_consumer.py",
    "scripts/qualify_mathlib_source_catalogue_v1.py",
    "tests/test_mathlib_source_catalogue_qualification_v1.py",
)
BASE_IMAGE = "docker.io/library/buildpack-deps@sha256:17923645546d74acef88727bce62c23bbaed953fc7097c41a8b777bba3ca98de"
BASE_PARENT_INDEX = "sha256:8ea58fbc817960cd62d512044956ff00cb94865e549eeec32c12139413262004"
BASE_IMAGE_CONFIG = "sha256:12d2284be437af82eaf8ebf5d1965223b8f259d82c1a523fff8e46de50ed5b54"
RESULT = {
    "source_status": "SOURCE_INDEXED",
    "independent_verification": "NOT_CHECKED",
    "current_applicability": "NOT_CHECKED",
    "freshness": "PINNED_HISTORICAL_SOURCE",
    "authorization": "NONE",
    "authority": "NONE",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _clean_environment() -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_NO_REPLACE_OBJECTS="1",
        GIT_OPTIONAL_LOCKS="0",
        GIT_TERMINAL_PROMPT="0",
        LC_ALL="C.UTF-8",
        TZ="UTC",
        PYTHONHASHSEED="0",
        SOURCE_DATE_EPOCH="0",
    )
    return environment


def run(command: list[str], *, cwd: Path | None = None,
        capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=cwd,
        env=_clean_environment(),
        capture_output=capture,
        check=True,
    )


def git(root: Path, *arguments: str) -> str:
    completed = run(
        ["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-C", str(root), *arguments],
        capture=True,
    )
    return completed.stdout.decode("utf-8").strip()


def require_new_work_root(root: Path) -> None:
    """Reject reuse, including an existing empty directory or a symlink."""
    require(not root.is_symlink(), "qualification work root must not be a symlink")
    require(not root.exists(), "qualification work root must not already exist")


def verify_parent_index(raw: bytes) -> None:
    def unique_object(pairs):
        value = {}
        for key, member in pairs:
            require(key not in value, "duplicate OCI index field")
            value[key] = member
        return value

    try:
        value = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid OCI parent index") from error
    require(type(value) is dict and type(value.get("manifests")) is list, "OCI parent index is missing manifests")
    expected = BASE_IMAGE.rsplit("@", 1)[1]
    matches = [entry for entry in value["manifests"]
               if type(entry) is dict and entry.get("digest") == expected
               and entry.get("platform") == {"os": "linux", "architecture": "amd64"}]
    require(len(matches) == 1, "parent index does not bind the exact linux/amd64 child")


def load_producer_module(root: Path):
    """Load the publisher source from an explicitly selected checkout."""
    path = root / "mathgraph/source_catalogue_publisher_v1.py"
    require(path.is_file() and not path.is_symlink(), "producer module is missing or unsafe")
    before = list(sys.path)
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "mathgraph"))
    try:
        spec = importlib.util.spec_from_file_location("task3_source_catalogue_publisher_v1", path)
        require(spec is not None and spec.loader is not None, "producer module cannot be loaded")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(spec.name, None)
            raise
        return module
    finally:
        sys.path[:] = before


def _file_digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def _utf16(value: str) -> bytes:
    return value.encode("utf-16-be")


def _manifest_packages(mathlib_root: Path, publisher) -> list[dict]:
    lock = publisher.contract._load((mathlib_root / "lake-manifest.json").read_bytes(), 16 * 1024 * 1024)
    require(type(lock) is dict and type(lock.get("packages")) is list, "invalid lake manifest")
    packages = []
    names: set[str] = set()
    for locked in lock["packages"]:
        require(type(locked) is dict and set(locked) >= {"name", "url", "rev"}, "unsupported lake package entry")
        name, repository, commit = locked["name"], locked["url"], locked["rev"]
        require(type(name) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", name) is not None,
                "invalid lake package name")
        require(name not in names, "duplicate lake package")
        names.add(name)
        require(type(repository) is str and repository.startswith("https://"), "public HTTPS package required")
        require(type(commit) is str and re.fullmatch(r"[0-9a-f]{40}", commit) is not None,
                "exact package commit required")
        package_root = mathlib_root / ".lake/packages" / name
        require(package_root.is_dir() and not package_root.is_symlink(), "package checkout is missing or unsafe")
        require(git(package_root, "rev-parse", "HEAD") == commit, "package commit differs from lake manifest")
        require(not git(package_root, "status", "--porcelain=v1", "--untracked-files=all"), "dirty dependency package")
        tree = git(package_root, "rev-parse", "HEAD^{tree}")
        package = {"name": name, "path": "packages/" + name, "commit": commit, "tree": tree,
                   "repository": repository}
        metadata = publisher.sanitized_git_files(package_root, {**package, "git_metadata_sha256": "0" * 64})
        package["git_metadata_sha256"] = publisher.git_metadata_digest(metadata)
        packages.append(package)
    packages.sort(key=lambda item: _utf16(item["name"]))
    return packages


def build_dependency_inventory(mathlib_root: Path, policy: dict, publisher) -> tuple[dict, bytes]:
    """Inventory every admitted cache byte and separately pin package Git trees."""
    dependency_root = mathlib_root / ".lake"
    require(dependency_root.is_dir() and not dependency_root.is_symlink(), "fresh .lake dependency root required")
    packages = _manifest_packages(mathlib_root, publisher)
    files = []
    for path in dependency_root.rglob("*"):
        relative = path.relative_to(dependency_root)
        if ".git" in relative.parts:
            require(not path.is_symlink(), "symlink in package Git administration")
            continue
        if path.is_symlink():
            matches = [package for package in packages
                       if relative.as_posix().startswith(package["path"] + "/")]
            require(len(matches) == 1, "dependency symlink is not inside one pinned package tree")
            package = matches[0]
            package_relative = relative.as_posix()[len(package["path"]) + 1:]
            target = publisher.dependency_symlink_target(dependency_root / package["path"], package,
                                                         package_relative)
            raw = target.encode("utf-8", errors="strict")
            files.append({"path": relative.as_posix(), "sha256": sha256(raw), "size_bytes": len(raw),
                          "mode": "120000", "target": target})
            continue
        if path.is_dir():
            continue
        require(path.is_file() and stat.S_ISREG(path.stat().st_mode), "unsupported dependency entry")
        digest, size = _file_digest(path)
        files.append({"path": relative.as_posix(), "sha256": digest, "size_bytes": size,
                      "mode": "100755" if path.stat().st_mode & 0o111 else "100644"})
    files.sort(key=lambda item: _utf16(item["path"]))
    inventory = {
        "schema": "mathgraph.catalogue-environment-inventory.v1",
        "acquisition": "FRESH_EXACT_COMMIT_CACHE",
        "source_commit": policy["source"]["commit"],
        "source_tree": policy["source"]["tree"],
        "packages": packages,
        "files": files,
    }
    raw = publisher.contract.canonical_bytes(inventory)
    publisher.verify_dependency_inventory(dependency_root, inventory, sha256(raw))
    return inventory, raw


def _identity(root: Path, commit: str, sources: Iterable[str], *, contract_version: bool) -> dict:
    require(git(root, "rev-parse", "HEAD") == commit, "identity checkout at wrong commit")
    require(not git(root, "status", "--porcelain=v1", "--untracked-files=all"), "identity checkout must be clean")
    result = []
    for relative in sources:
        path = root / relative
        require(path.is_file() and not path.is_symlink(), "identity source missing or unsafe")
        raw = path.read_bytes()
        require(run(["git", "-C", str(root), "show", f"{commit}:{relative}"], capture=True).stdout == raw,
                "identity source differs from commit")
        result.append({"path": relative, "sha256": sha256(raw)})
    value = {"source_commit": commit, "sources": result}
    if contract_version:
        value["contract_version"] = 1
    return value


def producer_identity(producer_root: Path, publisher, dependency_sha256: str) -> dict:
    identity = _identity(producer_root, PRODUCER_COMMIT, PRODUCER_FILES, contract_version=True)
    identity["environment"] = {
        "image": BASE_IMAGE,
        "dependency_inventory_sha256": dependency_sha256,
        "toolchain": publisher.TOOLCHAIN_PROFILE,
        "authority": "NONE",
    }
    return identity


def wrapper_identity(repository_root: Path) -> dict:
    commit = git(repository_root, "rev-parse", "HEAD")
    require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "exact wrapper commit required")
    return _identity(repository_root, commit, QUALIFICATION_WRAPPER_FILES, contract_version=False)


def build_trust_policy(publication_root: Path, source_policy: dict, source_policy_raw: bytes,
                       producer: dict, wrapper: dict) -> dict:
    manifest_raw = (publication_root / "manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    require(manifest.get("catalogue_id") == source_policy["catalogue_id"],
            "publication and source-policy catalogue identities differ")
    source = source_policy["source"]
    modules = [{key: module[key] for key in ("module", "path", "sha256", "size_bytes")}
               for module in source_policy["modules"]]
    return {
        "schema": "mathgraph.source-catalogue-trust-policy.v1",
        "policy_version": 1,
        "catalogue_id": source_policy["catalogue_id"],
        "manifest": {"path": "manifest.json", "sha256": sha256(manifest_raw), "size_bytes": len(manifest_raw)},
        "source_policy": {"path": SOURCE_POLICY_PATH, "sha256": sha256(source_policy_raw)},
        "source": {
            "repository": source["repository"],
            "commit": source["commit"],
            "tree": source["tree"],
            "lean_toolchain": {key: source["lean_toolchain"][key] for key in ("value", "sha256")},
            "modules": modules,
        },
        "producer": producer,
        "qualification_wrapper": wrapper,
        "admitted_relations": ["DECLARES", "IMPORTS_MODULE", "TYPE_REFERENCES"],
        "result": RESULT,
        "extensions": [],
    }


def _clone_producer(repository_root: Path, destination: Path) -> None:
    run(["git", "clone", "--no-hardlinks", "--no-checkout", str(repository_root), str(destination)])
    run(["git", "-C", str(destination), "checkout", "--detach", PRODUCER_COMMIT])
    require(git(destination, "rev-parse", "HEAD") == PRODUCER_COMMIT, "producer checkout pin failed")
    require(not git(destination, "status", "--porcelain=v1", "--untracked-files=all"), "producer checkout is dirty")


def _acquire_mathlib(destination: Path, policy: dict) -> dict:
    destination.mkdir()
    run(["git", "init", "-q", str(destination)])
    run(["git", "-C", str(destination), "remote", "add", "origin", policy["source"]["repository"]])
    run(["git", "-C", str(destination), "fetch", "--depth", "1", "--no-tags", "origin", policy["source"]["commit"]])
    run(["git", "-C", str(destination), "checkout", "--detach", "FETCH_HEAD"])
    require(git(destination, "rev-parse", "HEAD") == policy["source"]["commit"], "Mathlib commit pin failed")
    require(git(destination, "rev-parse", "HEAD^{tree}") == policy["source"]["tree"], "Mathlib tree pin failed")
    require(not git(destination, "status", "--porcelain=v1", "--untracked-files=all"), "Mathlib checkout is dirty")
    tag = policy["source"].get("tag")
    observation = {"label": tag, "authority": "NONE", "observed": False, "target": None}
    if tag:
        queried = run(["git", "ls-remote", "--tags", policy["source"]["repository"],
                       "refs/tags/" + tag, "refs/tags/" + tag + "^{}"], capture=True).stdout.decode()
        targets = [line.split()[0] for line in queried.splitlines() if line.strip()]
        if targets:
            target = targets[-1]
            require(target == policy["source"]["commit"], "descriptive tag currently targets another commit")
            observation.update(observed=True, target=target)
    return observation


def _prepare_container_runtime(evidence_root: Path) -> dict:
    parent_reference = "docker.io/library/buildpack-deps@" + BASE_PARENT_INDEX
    parent_raw = run(["docker", "buildx", "imagetools", "inspect", "--raw", parent_reference], capture=True).stdout
    verify_parent_index(parent_raw)
    run(["docker", "pull", "--platform", "linux/amd64", BASE_IMAGE])
    inspected_raw = run(["docker", "image", "inspect", "--format",
                         '{"id":"{{.Id}}","os":"{{.Os}}","arch":"{{.Architecture}}"}', BASE_IMAGE],
                        capture=True).stdout
    inspected = json.loads(inspected_raw)
    require(inspected == {"id": BASE_IMAGE_CONFIG, "os": "linux", "arch": "amd64"},
            "base image config/platform mismatch")
    run(["docker", "run", "--rm", "--pull", "never", "--network", "none", "--read-only",
         "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--platform", "linux/amd64",
         "--entrypoint", "/bin/sh", BASE_IMAGE, "-eu", "-c", "test ! -e /var/run/docker.sock"])
    missing = subprocess.run(
        ["docker", "run", "--rm", "--pull", "never", "--network", "none",
         "docker.io/library/buildpack-deps@sha256:" + "0" * 64, "true"],
        env=_clean_environment(), capture_output=True,
    )
    require(missing.returncode != 0, "missing immutable image unexpectedly ran")
    (evidence_root / "base-parent-index.json").write_bytes(parent_raw)
    return {"parent_index": BASE_PARENT_INDEX, "child_manifest": BASE_IMAGE.rsplit("@", 1)[1],
            "config": BASE_IMAGE_CONFIG, "platform": "linux/amd64", "cached_run_succeeded": True,
            "missing_image_failed": True}


def _acquire_toolchain(work: Path, publisher) -> tuple[Path, Path, dict]:
    profile = publisher.TOOLCHAIN_PROFILE
    archive = work / "lean.tar.zst"
    run(["curl", "--fail", "--location", "--silent", "--show-error", "--retry", "3",
         "--output", str(archive), profile["archive_url"]])
    digest, size = _file_digest(archive)
    require(digest == profile["archive_sha256"] and size == profile["archive_size_bytes"],
            "Lean archive pin mismatch")
    parent = work / "toolchain"
    parent.mkdir()
    run(["tar", "--zstd", "-xf", str(archive), "-C", str(parent)])
    archive.unlink()
    root = parent / profile["archive_root"]
    require(root.is_dir() and not root.is_symlink(), "Lean archive root mismatch")
    inventory = publisher.toolchain_inventory(root)
    raw = publisher.contract.canonical_bytes(inventory)
    require(len(raw) == profile["inventory_size_bytes"] and sha256(raw) == profile["inventory_sha256"],
            "Lean toolchain inventory pin mismatch")
    receipt = work / "toolchain-inventory.json"
    receipt.write_bytes(raw)
    publisher.verify_toolchain_tree(root, receipt, profile)
    return root, receipt, {"sha256": sha256(raw), "size_bytes": len(raw),
                           "entry_count": len(inventory["entries"]), "authority": "NONE"}


def _prune_selected_outputs(mathlib_root: Path, policy: dict) -> list[str]:
    """Remove cached outputs for selected origins before inventorying closure."""
    build = mathlib_root / ".lake/build"
    if not build.exists():
        return []
    selected = [module["module"].replace(".", "/") + "." for module in policy["modules"]]
    removed = []
    for path in list(build.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(build).as_posix()
        if any(("/" + prefix) in ("/" + relative) for prefix in selected):
            removed.append(relative)
            path.unlink()
    return sorted(removed, key=_utf16)


def _publication_inventory(root: Path) -> list[dict]:
    files = []
    for path in root.rglob("*"):
        require(not path.is_symlink(), "symlink in compact publication")
        if path.is_file():
            digest, size = _file_digest(path)
            files.append({"path": path.relative_to(root).as_posix(), "sha256": digest, "size_bytes": size})
    return sorted(files, key=lambda item: _utf16(item["path"]))


def _write_canonical(path: Path, value: object, publisher) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(publisher.contract.canonical_bytes(value))


def write_artifact_checksum_manifest(output_root: Path) -> list[dict]:
    """Close the complete generated artifact inventory with relative digests."""
    checksum_path = output_root / "evidence/artifact-checksums.txt"
    require(not checksum_path.exists() and not checksum_path.is_symlink(),
            "artifact checksum manifest must be written once")
    entries = _publication_inventory(output_root)
    for entry in entries:
        require("\n" not in entry["path"] and "\r" not in entry["path"], "unsafe artifact path")
    checksum_path.write_text(
        "".join(f"{entry['sha256']}  {entry['path']}\n" for entry in entries),
        encoding="utf-8",
    )
    return entries


def host_runtime_identity() -> dict:
    executable = Path(sys.executable).resolve()
    executable_sha256, _ = _file_digest(executable)
    return {
        "implementation": sys.implementation.name,
        "version": sys.version,
        "cache_tag": sys.implementation.cache_tag,
        "executable": str(executable),
        "executable_sha256": executable_sha256,
        "runner_os": os.environ.get("RUNNER_OS"),
        "runner_arch": os.environ.get("RUNNER_ARCH"),
        "runner_image_os": os.environ.get("ImageOS"),
        "runner_image_version": os.environ.get("ImageVersion"),
    }


def qualify(arguments) -> dict:
    repository_root = arguments.repository_root.resolve()
    work_root, output_root = arguments.work_root.absolute(), arguments.output_root.absolute()
    require_new_work_root(work_root)
    require(not output_root.exists() and not output_root.is_symlink(), "output root must be new")
    usage = shutil.disk_usage(work_root.parent)
    require(usage.free >= arguments.minimum_free_gib * 1024 ** 3, "insufficient free disk for exact acquisition")
    work_root.mkdir()
    output_root.mkdir()
    evidence = output_root / "evidence"
    evidence.mkdir()

    producer_root = work_root / "producer"
    _clone_producer(repository_root, producer_root)
    publisher = load_producer_module(producer_root)
    require(tuple(publisher.PRODUCER_FILES) == PRODUCER_FILES, "Task 2 producer closure changed")
    require(publisher.BASE_IMAGE == BASE_IMAGE and publisher.BASE_IMAGE_CONFIG == BASE_IMAGE_CONFIG,
            "Task 2 runtime profile changed")
    policy_path = producer_root / SOURCE_POLICY_PATH
    source_policy_raw = policy_path.read_bytes()
    policy = publisher.load_source_policy(policy_path)
    require(policy["source"]["repository"] == MATHLIB_REPOSITORY, "unexpected source repository")

    container_receipt = _prepare_container_runtime(evidence)
    mathlib_root = work_root / "mathlib"
    tag_observation = _acquire_mathlib(mathlib_root, policy)
    source = publisher.verify_source_checkout(policy, mathlib_root)
    toolchain_root, toolchain_receipt, toolchain_summary = _acquire_toolchain(work_root, publisher)

    lake = toolchain_root / "bin/lake"
    require(lake.is_file() and os.access(lake, os.X_OK), "pinned lake executable missing")
    environment = _clean_environment()
    environment["PATH"] = str(toolchain_root / "bin") + os.pathsep + environment.get("PATH", "/usr/bin:/bin")
    subprocess.run([str(lake), "exe", "cache", "get"], cwd=mathlib_root, env=environment, check=True)
    removed_outputs = _prune_selected_outputs(mathlib_root, policy)
    inventory, inventory_raw = build_dependency_inventory(mathlib_root, policy, publisher)
    inventory_path = work_root / "dependency-inventory.json"
    inventory_path.write_bytes(inventory_raw)
    dependency_sha256 = sha256(inventory_raw)

    identity = producer_identity(producer_root, publisher, dependency_sha256)
    identity_path = work_root / "extractor-identity.json"
    _write_canonical(identity_path, identity, publisher)
    local_environment = {
        "image": BASE_IMAGE,
        "dependency_root": str(mathlib_root / ".lake"),
        "inventory": str(inventory_path),
        "dependency_inventory_sha256": dependency_sha256,
        "toolchain": {"root": str(toolchain_root), "inventory": str(toolchain_receipt)},
    }
    environment_path = work_root / "offline-environment.json"
    _write_canonical(environment_path, local_environment, publisher)
    extraction_paths = [work_root / "extraction-1.json", work_root / "extraction-2.json"]
    command = [
        sys.executable, "-I", "-S", "-B",
        str(producer_root / "scripts/run_mathlib_source_catalogue_offline_v1.py"),
        "--checkout", str(mathlib_root), "--source-policy", str(policy_path),
        "--extractor-identity", str(identity_path), "--environment", str(environment_path),
    ]
    for extraction in extraction_paths:
        run([*command, "--output", str(extraction)])
    raw_first, raw_second = extraction_paths[0].read_bytes(), extraction_paths[1].read_bytes()
    require(raw_first == raw_second, "two offline extraction passes differ")

    publication = publisher.build_publication(policy, source, identity, raw_first)
    catalogue_root = output_root / "catalogue"
    publisher.publish_catalogue(publication, catalogue_root)
    publisher.validate_publication(publication)
    if arguments.expected_publication is not None:
        expected = arguments.expected_publication.resolve()
        actual_files = dict(publication.files)
        expected_files = {path.relative_to(expected).as_posix(): path.read_bytes()
                          for path in expected.rglob("*") if path.is_file()}
        require(actual_files == expected_files, "generated publication differs from committed publication")

    manifest = json.loads((catalogue_root / "manifest.json").read_bytes())
    qualified_wrapper = wrapper_identity(repository_root)
    trust_policy = build_trust_policy(catalogue_root, policy, source_policy_raw, manifest["extractor"], qualified_wrapper)
    trust_policy_path = output_root / "trust-policy.json"
    _write_canonical(trust_policy_path, trust_policy, publisher)
    trust_policy_sha256 = sha256(trust_policy_path.read_bytes())
    consumer = repository_root / "conformance/source_catalogue_v1/consumer.py"
    replay = run([sys.executable, "-I", "-S", "-B", str(consumer), "--catalogue-root", str(catalogue_root),
                  "--policy", str(trust_policy_path), "--policy-sha256", trust_policy_sha256,
                  "--audit-imports"], capture=True)
    require(json.loads(replay.stdout) == RESULT, "local independent consumer result mismatch")
    audit = json.loads(replay.stderr)
    require(audit["isolated"] and audit["no_site"] and audit["dont_write_bytecode"]
            and not audit["forbidden_imports"] and audit["network_access"] == "NOT_USED",
            "local independent consumer isolation/import audit failed")

    publication_files = _publication_inventory(catalogue_root)
    report = {
        "schema": "mathgraph.source-catalogue-qualification-report.v1",
        "status": "GENERATION_COMPLETE_AWAITING_ISOLATED_INDEPENDENT_REPLAY",
        "catalogue_id": policy["catalogue_id"],
        "source": {"repository": policy["source"]["repository"], "commit": policy["source"]["commit"],
                   "tree": policy["source"]["tree"], "descriptive_tag_observation": tag_observation},
        "producer": {"commit": PRODUCER_COMMIT, "identity_sha256": sha256(identity_path.read_bytes())},
        "qualification_wrapper": qualified_wrapper,
        "orchestration_runtime": host_runtime_identity(),
        "runtime": container_receipt,
        "toolchain_inventory": toolchain_summary,
        "dependency_inventory": {"sha256": dependency_sha256, "size_bytes": len(inventory_raw),
                                 "file_count": len(inventory["files"]), "package_count": len(inventory["packages"]),
                                 "selected_cached_outputs_removed": len(removed_outputs), "authority": "NONE"},
        "two_pass_extraction": {"identical": True, "sha256": sha256(raw_first), "size_bytes": len(raw_first)},
        "publication": {"files": publication_files, "manifest_counts": manifest["counts"]},
        "trust_policy_sha256": trust_policy_sha256,
        "local_consumer_result": RESULT,
        "expected_publication_compared": arguments.expected_publication is not None,
        "network_boundary": "DOCKER_NETWORK_NONE_DURING_BOTH_EXTRACTIONS",
        "authority": "NONE",
    }
    _write_canonical(evidence / "qualification-report.json", report, publisher)
    size_report = {"schema": "mathgraph.source-catalogue-size-report.v1",
                   "raw_bytes": sum(item["size_bytes"] for item in publication_files),
                   "file_count": len(publication_files), "limits": manifest["limits"], "authority": "NONE"}
    _write_canonical(evidence / "size-report.json", size_report, publisher)
    isolation = {"schema": "mathgraph.source-catalogue-isolation-preflight.v1", **container_receipt,
                 "extraction_network": "none", "publication_authority": "NONE"}
    _write_canonical(evidence / "isolation-preflight.json", isolation, publisher)
    checksums = [f"{item['sha256']}  catalogue/{item['path']}" for item in publication_files]
    checksums += [f"{trust_policy_sha256}  trust-policy.json"]
    (evidence / "checksums.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    write_artifact_checksum_manifest(output_root)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-publication", type=Path)
    parser.add_argument("--minimum-free-gib", type=int, default=12)
    arguments = parser.parse_args()
    try:
        report = qualify(arguments)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        print("CATALOGUE_QUALIFICATION_DECLINED: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
