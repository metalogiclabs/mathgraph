"""Deterministic local source publication, independent of the terminal-form kernel.

No acquisition takes place here. The CLI requires clean, pinned source and
producer checkouts, and runs Lean through a network-denied container. Library
``build_publication`` is a pure transformation: its caller supplies the verified
extractor output and identity. Environment/cache byte trust is explicitly
separate from source identity and mathematical verification.
"""
from __future__ import annotations

from dataclasses import dataclass
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import subprocess
import tempfile
from typing import Sequence
import zlib

from mathgraph_protocol import source_catalogue_v1 as contract

MAX_EXTRACTION_BYTES = 16 * 1024 * 1024
MAX_PUBLICATION_BYTES = 4 * 1024 * 1024
MAX_PUBLICATION_GZIP_BYTES = 1536 * 1024
REPRODUCE = ("MATHGRAPH_CATALOGUE_ENVIRONMENT={ENVIRONMENT} python scripts/publish_mathlib_source_catalogue_v1.py --checkout {CHECKOUT} "
             "--source-policy {SOURCE_POLICY} --extractor-identity {EXTRACTOR_IDENTITY} --output-dir {OUTPUT}")
ROOT = Path(__file__).resolve().parents[1]
PRODUCER_FILES = (
    "mathgraph/source_catalogue_publisher_v1.py", "mathgraph_protocol/__init__.py",
    "mathgraph_protocol/discovery_ranking.py", "mathgraph_protocol/json_strict.py",
    "mathgraph_protocol/source_catalogue_v1.py", "scripts/catalogue_bootstrap_v1.py",
    "scripts/publish_mathlib_source_catalogue_v1.py",
    "scripts/run_mathlib_source_catalogue_offline_v1.py", "tools/mathlib_catalogue/CompileOrder.lean", "tools/mathlib_catalogue/Extract.lean")
COMPILE_FLAGS = ("-DautoImplicit=false", "-DmaxSynthPendingDepth=3", "-Dpp.unicode.fun=true")
BASE_IMAGE = "docker.io/library/buildpack-deps@sha256:17923645546d74acef88727bce62c23bbaed953fc7097c41a8b777bba3ca98de"
BASE_IMAGE_CONFIG = "sha256:12d2284be437af82eaf8ebf5d1965223b8f259d82c1a523fff8e46de50ed5b54"
TOOLCHAIN_PROFILE = {
    "archive_url": "https://github.com/leanprover/lean4/releases/download/v4.34.1/lean-4.34.1-linux.tar.zst",
    "archive_sha256": "47bf4bbd78f70c2e9670598ab7124d92b6efb7330ff33e5fbb4030f6fd72e4e4", "archive_size_bytes": 580432872,
    "archive_root": "lean-4.34.1-linux", "mount": "/opt/lean", "lean_version": "4.34.1", "lean_commit": "5045d0056413266e57c625dcd7c365b10e377c52",
    "base_image": BASE_IMAGE, "base_image_config": BASE_IMAGE_CONFIG, "platform": "linux/amd64",
    "inventory_schema": "mathgraph.toolchain-tree.v1", "inventory_sha256": "dce115ba9934df63c9c59f53297d90ffefa702b3736cab41eac4900351754c88",
    "inventory_size_bytes": 3206496, "entry_count": 18381, "file_count": 17738, "directory_count": 631, "symlink_count": 12,
    "regular_bytes": 3068313425, "authority": "NONE"}


@dataclass(frozen=True)
class VerifiedSource:
    root: Path
    policy_bytes: bytes
    files: tuple[tuple[str, bytes], ...]
    tracked_paths: tuple[str, ...]


@dataclass(frozen=True)
class CataloguePublication:
    files: tuple[tuple[str, bytes], ...]


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def _git(root: Path, *args: str) -> bytes:
    try:
        return subprocess.check_output(["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-C", str(root), *args], stderr=subprocess.PIPE,
                                       env=_git_environment())
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("local Git verification failed") from error


def _git_environment() -> dict:
    return {**{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
            "GIT_NO_REPLACE_OBJECTS": "1", "GIT_OPTIONAL_LOCKS": "0", "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0"}


def _safe_file(root: Path, relative: str) -> Path:
    contract._path(relative)
    require(not root.is_symlink(), "symlink input root is not admitted")
    root = root.resolve()
    path = root / relative
    require(not any(p.is_symlink() for p in [path, *path.parents] if p.is_relative_to(root)), "symlink input is not admitted")
    require(path.resolve().is_relative_to(root.resolve()) and path.is_file(), "file outside verified root or missing")
    return path


def _policy(policy: dict) -> dict:
    p = contract._load(policy, contract.LIMITS["max_manifest_bytes"])
    contract._shape(p, {"schema", "catalogue_id", "source", "modules", "build_inputs"})
    require(p["schema"] == "mathgraph.source-catalogue-policy.v1", "unsupported source policy")
    contract._text(p["catalogue_id"])
    s = p["source"]
    contract._shape(s, {"repository", "commit", "tree", "tag", "license", "citation", "lean_toolchain", "lake_manifest", "root_module"})
    for field in ["repository", "tag"]: contract._text(s[field])
    for field in ["commit", "tree"]: contract._digest(s[field], 40)
    for field in ["license", "citation", "lake_manifest", "root_module"]: contract._file(s[field])
    contract._file(s["lean_toolchain"], {"value"})
    require(re.fullmatch(r"leanprover/lean4:v\d+\.\d+\.\d+", s["lean_toolchain"]["value"]) is not None, "pinned release toolchain required")
    contract._array(p["modules"])
    require(bool(p["modules"]), "explicit modules required")
    names = set()
    for m in p["modules"]:
        contract._shape(m, {"module", "path", "sha256", "size_bytes"})
        contract._file({k: m[k] for k in ["path", "sha256"]})
        contract._integer(m["size_bytes"], 1)
        require(re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*", m["module"]) is not None, "invalid module name")
        require(m["path"] == m["module"].replace(".", "/") + ".lean", "module path mismatch")
        contract._unique(m["module"], names)
    contract._ordered([m["module"] for m in p["modules"]])
    contract._array(p["build_inputs"])
    require(bool(p["build_inputs"]), "declared build inputs required")
    paths = set()
    for entry in p["build_inputs"]:
        contract._file(entry)
        contract._unique(entry["path"], paths)
    contract._ordered([e["path"] for e in p["build_inputs"]])
    return p


def load_source_policy(path: Path) -> dict:
    return _policy(contract._load(path.read_bytes(), contract.LIMITS["max_manifest_bytes"]))


def _tree_entries(root: Path, commit: str):
    for item in _git(root, "ls-tree", "-rz", commit).split(b"\0"):
        if not item: continue
        meta, rawpath = item.split(b"\t", 1)
        mode, kind, blob = meta.split()
        require(kind == b"blob" and mode in {b"100644", b"100755", b"120000"}, "unsupported Git source entry")
        yield rawpath.decode("utf-8"), mode, blob.decode()


def _tracked_bytes(root: Path, path: str, mode: bytes) -> bytes:
    if mode != b"120000": return _safe_file(root, path).read_bytes()
    contract._path(path)
    leaf = root / path
    require(leaf.is_symlink() and leaf.is_file() and leaf.resolve().is_relative_to(root.resolve()), "tracked symlink escape or missing target")
    require(not any(p.is_symlink() for p in leaf.parents if p.is_relative_to(root)), "symlink source parent")
    target = os.readlink(leaf)
    require(not Path(target).is_absolute(), "absolute source symlink is not portable")
    return target.encode("utf-8")


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _verify_tree(root: Path, commit: str, tree: str) -> tuple[str, ...]:
    require(root.is_dir() and not root.is_symlink(), "local checkout required")
    require(Path(_git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve() == root.resolve(), "checkout must be verified root")
    require(_git(root, "rev-parse", "HEAD").decode().strip() == commit, "wrong commit")
    require(_git(root, "rev-parse", "HEAD^{tree}").decode().strip() == tree, "wrong tree")
    require(not _git(root, "status", "--porcelain=v1", "--untracked-files=all").strip(), "dirty checkout")
    paths = []
    # Compare all tracked source bytes, including skip-worktree/assume-unchanged
    # files that Git's status optimization could otherwise overlook.
    for path, mode, blob in _tree_entries(root, commit):
        require(_git_blob(_tracked_bytes(root, path, mode)) == blob, "tracked source bytes differ from Git tree")
        paths.append(path)
    return tuple(paths)


def verify_source_checkout(policy: dict, checkout: Path) -> VerifiedSource:
    p = _policy(policy)
    root = checkout.absolute()
    tracked = _verify_tree(root, p["source"]["commit"], p["source"]["tree"])
    files = {}
    entries = p["modules"] + p["build_inputs"] + [v for v in p["source"].values() if isinstance(v, dict)]
    for entry in entries:
        require(entry["path"] in tracked, "untracked policy source")
        raw = _safe_file(root, entry["path"]).read_bytes()
        require(sha256(raw) == entry["sha256"], "source digest mismatch")
        if "size_bytes" in entry: require(len(raw) == entry["size_bytes"], "source byte size mismatch")
        if "value" in entry: require(raw.decode("utf-8").strip() == entry["value"], "toolchain mismatch")
        raw.decode("utf-8", errors="strict")
        files[entry["path"]] = raw
    return VerifiedSource(root, contract.canonical_bytes(p), tuple(sorted(files.items())), tracked)


def validate_image_digest(image: str) -> None:
    require(isinstance(image, str) and re.fullmatch(r"[A-Za-z0-9./_:-]+@sha256:[0-9a-f]{64}", image) is not None,
            "an immutable container image digest is required")


def _environment(identity: dict) -> dict:
    e = identity["environment"]
    contract._shape(e, {"image", "dependency_inventory_sha256", "authority"} | ({"toolchain"} if "toolchain" in e else set()))
    validate_image_digest(e["image"])
    contract._digest(e["dependency_inventory_sha256"])
    require(e["authority"] == "NONE", "environment trust grants no authority")
    if "toolchain" in e:
        require(e["image"] == BASE_IMAGE and e["toolchain"] == TOOLCHAIN_PROFILE, "external toolchain profile mismatch")
    else:
        require(e["image"] != BASE_IMAGE, "base image requires verified external toolchain")
    return e


def toolchain_inventory(root: Path) -> dict:
    """Exact portable archive-tree recipe: paths sorted by UTF-8 bytes."""
    require(root.is_dir() and not root.is_symlink(), "regular toolchain root required")
    root = root.resolve()
    entries = []
    for path in sorted([root, *root.rglob("*")], key=lambda p: p.relative_to(root).as_posix().encode("utf-8")):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        entry = {"path": relative, "mode": format(stat.S_IMODE(info.st_mode), "04o")}
        if stat.S_ISLNK(info.st_mode):
            target = os.readlink(path)
            require(not Path(target).is_absolute() and path.resolve(strict=True).is_relative_to(root), "external toolchain symlink")
            entry.update(kind="symlink", target=target)
        elif stat.S_ISDIR(info.st_mode):
            entry.update(kind="directory")
        else:
            require(stat.S_ISREG(info.st_mode), "unsupported toolchain entry")
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
            entry.update(kind="file", sha256=digest.hexdigest(), size_bytes=info.st_size)
        entries.append(entry)
    return {"schema": "mathgraph.toolchain-tree.v1", "entries": entries}


def verify_toolchain_tree(root: Path, receipt: Path, profile: dict) -> None:
    raw = receipt.read_bytes()
    require(len(raw) == profile["inventory_size_bytes"] and sha256(raw) == profile["inventory_sha256"], "toolchain receipt pin mismatch")
    expected = contract._load(raw, 8 * 1024 * 1024)
    actual = toolchain_inventory(root)
    require(raw == contract.canonical_bytes(expected) and actual == expected, "toolchain bytes/modes/inventory mismatch")
    entries = actual["entries"]
    require(len(entries) == profile["entry_count"] and sum(e.get("size_bytes", 0) for e in entries) == profile["regular_bytes"], "toolchain inventory totals mismatch")
    for kind in ["file", "directory", "symlink"]:
        require(sum(e["kind"] == kind for e in entries) == profile[kind + "_count"], "toolchain entry count mismatch")


def verify_extractor_identity(identity: dict, root: Path = ROOT) -> None:
    contract._shape(identity, {"source_commit", "contract_version", "sources", "environment"})
    contract._digest(identity["source_commit"], 40)
    require(type(identity["contract_version"]) is int and identity["contract_version"] == 1, "unsupported extractor contract")
    _environment(identity)
    head = _git(root, "rev-parse", "HEAD").decode().strip()
    require(head == identity["source_commit"], "producer source commit mismatch")
    _verify_tree(root, head, _git(root, "rev-parse", "HEAD^{tree}").decode().strip())
    require([f["path"] for f in identity["sources"]] == list(PRODUCER_FILES), "every producer source must be pinned")
    for f in identity["sources"]:
        contract._file(f)
        raw = _safe_file(root, f["path"]).read_bytes()
        require(sha256(raw) == f["sha256"], "producer source digest mismatch")
        require(_git(root, "show", f"{head}:{f['path']}") == raw, "producer bytes differ from commit")


def verify_dependency_inventory(root: Path, inventory: dict, expected_sha256: str) -> None:
    require(sha256(contract.canonical_bytes(inventory)) == expected_sha256, "dependency inventory digest mismatch")
    contract._shape(inventory, {"schema", "acquisition", "source_commit", "source_tree", "packages", "files"})
    require(inventory["schema"] == "mathgraph.catalogue-environment-inventory.v1"
            and inventory["acquisition"] == "FRESH_EXACT_COMMIT_CACHE", "fresh exact-commit acquisition receipt required")
    for field in ["source_commit", "source_tree"]: contract._digest(inventory[field], 40)
    contract._array(inventory["packages"])
    contract._array(inventory["files"])
    require(root.is_dir() and not root.is_symlink(), "local dependency closure required")
    names = set()
    for package in inventory["packages"]:
        contract._shape(package, {"name", "path", "commit", "tree", "repository", "git_metadata_sha256"})
        contract._unique(package["name"], names)
        require(re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", package["name"]) is not None, "literal package name required")
        contract._path(package["path"])
        for field in ["commit", "tree"]: contract._digest(package[field], 40)
        require(package["path"] == "packages/" + package["name"], "package path mismatch")
        contract._digest(package["git_metadata_sha256"])
        metadata = sanitized_git_files(root / package["path"], package)
        require(git_metadata_digest(metadata) == package["git_metadata_sha256"], "sanitized Git metadata digest mismatch")
    contract._ordered([p["name"] for p in inventory["packages"]])
    paths = set()
    for f in inventory["files"]:
        require(type(f) is dict, "dependency inventory file must be an object")
        link = f.get("mode") == "120000"
        contract._file(f, {"size_bytes", "mode", "target"} if link else {"size_bytes", "mode"})
        contract._integer(f["size_bytes"])
        require(f["mode"] in {"100644", "100755", "120000"}, "unsupported environment file mode")
        contract._unique(f["path"], paths)
        require(".git" not in Path(f["path"]).parts, "Git administration is not an environment artifact")
        if link:
            package, relative = _dependency_package_for_path(inventory["packages"], f["path"])
            target = dependency_symlink_target(root / package["path"], package, relative)
            require(type(f["target"]) is str and f["target"] == target,
                    "dependency symlink target differs from exact Git tree")
            raw = target.encode("utf-8", errors="strict")
        else:
            path = _safe_file(root, f["path"])
            require(("100755" if path.stat().st_mode & 0o111 else "100644") == f["mode"], "dependency executable mode changed")
            raw = path.read_bytes()
        require(len(raw) == f["size_bytes"] and sha256(raw) == f["sha256"], "dependency artifact changed")
    contract._ordered([f["path"] for f in inventory["files"]])
    actual = set()
    git_roots = {p["path"] + "/.git" for p in inventory["packages"]}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            prefix = Path(*relative.parts[:relative.parts.index(".git") + 1]).as_posix()
            require(prefix in git_roots, "unlisted package Git state")
            require(not path.is_symlink(), "symlink in dependency Git administration")
            continue
        if path.is_symlink():
            actual.add(relative.as_posix())
        elif path.is_file():
            actual.add(relative.as_posix())
    require(paths == actual and bool(paths), "arbitrary or incomplete dependency build state")


def git_metadata_digest(files: tuple[tuple[str, bytes], ...]) -> str:
    """Digest canonical file identity records, not a host's Git configuration."""
    return sha256(contract.canonical_bytes([{"path": path, "sha256": sha256(raw), "size_bytes": len(raw)} for path, raw in files]))


def git_runtime_environment(packages: list[dict], runtime_root: str = "/work/.lake") -> dict[str, str]:
    """Protected config trusts only inventoried runtime roots, never a wildcard.

    The producer commit binds this construction; the environment inventory
    binds the complete package path list. Host/container UIDs need not match.
    """
    for package in packages:
        require(re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", package["name"]) is not None
                and package["path"] == "packages/" + package["name"], "literal package root required")
    settings = [("credential.helper", "")] + [("safe.directory", runtime_root + "/" + p["path"]) for p in packages]
    env = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_TERMINAL_PROMPT": "0",
           "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_REPLACE_OBJECTS": "1", "GIT_CONFIG_COUNT": str(len(settings))}
    for index, (key, value) in enumerate(settings):
        env[f"GIT_CONFIG_KEY_{index}"] = key
        env[f"GIT_CONFIG_VALUE_{index}"] = value
    return env


def _dependency_symlink_target(root: Path, package: dict, path: str, mode: bytes, blob: str,
                               entries: tuple[tuple[str, bytes, str], ...]) -> str:
    context = f"package={package['name']} path={path} mode={mode.decode()}"
    require(mode == b"120000", "dependency link mode mismatch: " + context)
    contract._path(path)
    require(root.is_dir() and not root.is_symlink(), "dependency root is unsafe: " + context)
    root = root.resolve()
    leaf = root / path
    require(leaf.is_symlink(), "tracked dependency link is not a symlink: " + context)
    target = os.readlink(leaf)
    require(not Path(target).is_absolute() and "\\" not in target
            and not any(ord(character) < 32 or ord(character) == 127 for character in target),
            "dependency symlink target is not portable relative text: " + context)
    target_bytes = target.encode("utf-8", errors="strict")
    require(_git_blob(target_bytes) == blob, "dependency symlink bytes differ from Git tree: " + context)
    lexical_target = Path(os.path.normpath(str(leaf.parent / target)))
    require(lexical_target.is_relative_to(root) and ".git" not in lexical_target.relative_to(root).parts,
            "dependency symlink target escapes package tree: " + context)
    require(lexical_target.exists(), "dependency symlink target is missing: " + context)
    current = root
    for part in lexical_target.relative_to(root).parts:
        current /= part
        require(not current.is_symlink(), "dependency symlink chain is not admitted: " + context)
    target_path = lexical_target.relative_to(root).as_posix()
    tracked = {entry_path: (entry_mode, entry_blob) for entry_path, entry_mode, entry_blob in entries}
    require(target_path in tracked and tracked[target_path][0] in {b"100644", b"100755"},
            "dependency symlink target is not an exact tracked file: " + context)
    require(lexical_target.is_file(), "dependency symlink target is not a regular file: " + context)
    require(_git_blob(lexical_target.read_bytes()) == tracked[target_path][1],
            "dependency symlink target bytes differ from Git tree: " + context)
    return target


def dependency_symlink_target(root: Path, package: dict, path: str) -> str:
    """Return an exact Git-bound relative link target or decline with context."""
    entries = tuple(_tree_entries(root, package["commit"]))
    matches = [entry for entry in entries if entry[0] == path]
    require(len(matches) == 1,
            f"dependency symlink is not uniquely tree-bound: package={package['name']} path={path} mode=unknown")
    relative, mode, blob = matches[0]
    return _dependency_symlink_target(root, package, relative, mode, blob, entries)


def _dependency_package_for_path(packages: list[dict], path: str) -> tuple[dict, str]:
    """Locate the one exact package root that owns an inventoried link."""
    contract._path(path)
    matches = [package for package in packages if path.startswith(package["path"] + "/")]
    require(len(matches) == 1, "dependency symlink is not inside one pinned package tree")
    package = matches[0]
    relative = path[len(package["path"]) + 1:]
    contract._path(relative)
    return package, relative


def sanitized_git_files(root: Path, package: dict) -> tuple[tuple[str, bytes], ...]:
    """Generate a detached shallow Git identity with only the pinned tree objects.

    No original Git administrative file is copied. The fixed index v2 has zero
    stat-cache fields. Parent commits, hooks, alternate object stores, refs,
    credentials, and host configuration are excluded.
    """
    repository = package["repository"]
    require(isinstance(repository, str) and re.fullmatch(r"https://[A-Za-z0-9.-]+/[A-Za-z0-9_./-]+", repository) is not None,
            "public HTTPS dependency repository required")
    require((root / ".git").is_dir() and not (root / ".git").is_symlink(), "standalone dependency Git directory required")
    entries = tuple(_tree_entries(root, package["commit"]))
    for path, mode, blob in entries:
        if mode == b"120000":
            _dependency_symlink_target(root, package, path, mode, blob, entries)
    _verify_tree(root, package["commit"], package["tree"])
    require(_git(root, "config", "--local", "--get-all", "remote.origin.url").decode().strip() == repository, "dependency remote mismatch")
    objects = {package["commit"], package["tree"]}
    for item in _git(root, "ls-tree", "-rtz", package["commit"]).split(b"\0"):
        if item: objects.add(item.split(b"\t", 1)[0].split()[2].decode())
    response = subprocess.check_output(["git", "-C", str(root), "cat-file", "--batch"],
        input=("\n".join(sorted(objects)) + "\n").encode(), env=_git_environment(), stderr=subprocess.PIPE)
    files = {"HEAD": (package["commit"] + "\n").encode(), "shallow": (package["commit"] + "\n").encode(),
             "config": ("[core]\n\trepositoryformatversion = 0\n\tbare = false\n\tfilemode = true\n\thooksPath = /dev/null\n\tfsmonitor = false\n[credential]\n\thelper =\n[remote \"origin\"]\n\turl = " + repository + "\n").encode()}
    offset = 0
    for expected in sorted(objects):
        end = response.index(b"\n", offset)
        object_id, kind, size = response[offset:end].split()
        require(object_id.decode() == expected and kind in {b"commit", b"tree", b"blob"}, "unexpected Git object")
        size = int(size)
        raw = kind + b" " + str(size).encode() + b"\0" + response[end + 1:end + 1 + size]
        require(hashlib.sha1(raw).hexdigest() == expected, "Git object digest mismatch")
        files["objects/" + expected[:2] + "/" + expected[2:]] = zlib.compress(raw)
        offset = end + size + 2
    require(offset == len(response), "unexpected Git object stream bytes")
    index = b"DIRC" + struct.pack("!II", 2, len(entries))
    for path, mode, blob in entries:
        name = path.encode()
        entry = struct.pack("!10I", 0, 0, 0, 0, 0, 0, int(mode, 8), 0, 0, 0) + bytes.fromhex(blob) + struct.pack("!H", min(len(name), 4095)) + name + b"\0"
        index += entry + b"\0" * (-len(entry) % 8)
    files["index"] = index + hashlib.sha1(index).digest()
    return tuple(sorted(files.items()))


def _range_bytes(value: dict, raw: bytes) -> None:
    contract._range(value, len(raw))
    for p in value.values():
        prefix = raw[:p["byte"]]
        try: prefix.decode("utf-8")
        except UnicodeError as error: raise ValueError("range splits a UTF-8 scalar") from error
        require(p["line"] == prefix.count(b"\n") + 1 and p["column"] == len(prefix.rsplit(b"\n", 1)[-1]),
                "range coordinates disagree with source bytes")


def _strings(value: list) -> None:
    contract._array(value)
    seen = set()
    for text in value: contract._unique(text, seen)
    contract._ordered(value)


def build_publication(policy: dict, source: VerifiedSource, extractor_identity: dict,
                      extractor_output: bytes) -> CataloguePublication:
    p = _policy(policy)
    require(contract.canonical_bytes(p) == source.policy_bytes, "verified source policy changed")
    identity = contract._load(extractor_identity, contract.LIMITS["max_manifest_bytes"])
    contract._shape(identity, {"source_commit", "contract_version", "sources", "environment"})
    environment = _environment(identity)
    raw = contract._load(extractor_output, MAX_EXTRACTION_BYTES)
    contract._shape(raw, {"contract_version", "modules"})
    require(type(raw["contract_version"]) is int and raw["contract_version"] == 1, "unsupported extraction contract")
    contract._array(raw["modules"])
    require([m["module"] for m in raw["modules"]] == [m["module"] for m in p["modules"]], "extracted module order or inventory mismatch")
    all_names, omissions = set(), set()
    modules, objects = {}, {}
    for policy_module, m in zip(p["modules"], raw["modules"]):
        contract._shape(m, {"module", "imports", "declarations", "omissions"})
        _strings(m["imports"])
        contract._array(m["declarations"])
        contract._array(m["omissions"])
        mid = contract.module_id(p["source"]["repository"], p["source"]["commit"], m["module"], policy_module["path"])
        module = {"module_id": mid, **policy_module, "objects": []}
        modules[m["module"]] = module
        for d in m["declarations"]:
            contract._shape(d, {"qualified_name", "kind", "statement", "range", "type_references"})
            contract._unique(d["qualified_name"], all_names, "DUPLICATE_NAME")
            require(d["kind"] in contract.CONSTANT_KINDS, "unsupported declaration kind")
            contract._text(d["statement"])
            _strings(d["type_references"])
            _range_bytes(d["range"], dict(source.files)[policy_module["path"]])
            oid = contract.occurrence_id(p["source"]["repository"], p["source"]["commit"], m["module"], policy_module["path"], d["qualified_name"])
            objects[d["qualified_name"]] = oid
            module["objects"].append({"object_id": oid, "qualified_name": d["qualified_name"]})
        contract._ordered([d["qualified_name"] for d in m["declarations"]])
        for omission in m["omissions"]:
            contract._shape(omission, {"qualified_name", "kind", "reason"})
            contract._unique(omission["qualified_name"], omissions, "DUPLICATE_NAME")
        contract._ordered([o["qualified_name"] for o in m["omissions"]])
    require(not all_names & omissions, "declaration both admitted and omitted")
    require(len(objects) <= contract.LIMITS["max_declarations"], "declaration count overflow")
    files, shards, search_rows = [], [], []
    for m in raw["modules"]:
        meta = modules[m["module"]]
        pin = {k: p["source"][k] for k in ["repository", "commit", "tree"]}
        locator = {**pin, "module": meta["module"], "path": meta["path"]}
        shard = {"schema": contract.SHARD_SCHEMA, "catalogue_version": 1, "catalogue_id": p["catalogue_id"],
                 **contract.AXES, "module": {**{k: v for k, v in meta.items() if k != "objects"}, **pin, **contract.AXES},
                 "objects": [], "relations": [], "omissions": {"imports": [], "type_references": [], "declarations": m["omissions"]}, "extensions": []}
        def edge(kind, source_id, target_id):
            sk, tk = contract.RELATION_KINDS[kind]
            shard["relations"].append({"relation_id": contract.relation_id(p["catalogue_id"], kind, source_id, target_id),
                "type": kind, "source_id": source_id, "target_id": target_id, "source_kind": sk, "target_kind": tk,
                "authority": "NONE", "logical_implication": False, "semantic_equivalence": False, "extensions": []})
        for d in m["declarations"]:
            oid = objects[d["qualified_name"]]
            shard["objects"].append({"object_id": oid, "object_contract_version": 1, "source": {**locator, "range": d["range"]},
                "qualified_name": d["qualified_name"], "kind": d["kind"], "statement": d["statement"],
                "statement_sha256": sha256(d["statement"].encode()), **contract.AXES, "extensions": []})
            search_rows.append({"object_id": oid, "qualified_name": d["qualified_name"], "module": m["module"], "kind": d["kind"], "statement": d["statement"]})
            edge("DECLARES", meta["module_id"], oid)
            for target in d["type_references"]:
                if target in objects: edge("TYPE_REFERENCES", oid, objects[target])
                else: shard["omissions"]["type_references"].append({"source_id": oid, "target_name": target})
        for target in m["imports"]:
            if target in modules: edge("IMPORTS_MODULE", meta["module_id"], modules[target]["module_id"])
            else: shard["omissions"]["imports"].append(target)
        shard["relations"].sort(key=lambda r: r["relation_id"])
        shard["omissions"]["type_references"].sort(key=lambda r: contract._key(r["source_id"] + "\0" + r["target_name"]))
        data = contract.canonical_bytes(shard)
        digest = sha256(data)
        path = f"shards/{digest}.json"
        shards.append({"module_id": meta["module_id"], "path": path, "sha256": digest, "size_bytes": len(data),
                       "object_count": len(shard["objects"]), "relation_count": len(shard["relations"]),
                       **{"omitted_" + k: len(v) for k, v in shard["omissions"].items()}})
        files.append((path, data))
    search_rows.sort(key=lambda r: contract._key(r["qualified_name"]))
    search = contract.canonical_bytes(search_rows)
    manifest = {"schema": contract.MANIFEST_SCHEMA, "catalogue_version": 1, "catalogue_id": p["catalogue_id"],
        "source": {**p["source"], "dependency_inventory_sha256": environment["dependency_inventory_sha256"]},
        "extractor": {k: v for k, v in identity.items() if k != "environment"}, "selection_policy": contract.SELECTION_POLICY,
        "modules": list(modules.values()), "counts": {"modules": len(modules), "objects": len(objects),
            "relations": sum(s["relation_count"] for s in shards), **{k: sum(s[k] for s in shards) for k in contract.OMISSION_COUNTS}},
        "limits": contract.LIMITS, "truncation": {"occurred": False, "reason": None}, "reproduce_command": REPRODUCE,
        "search": {"path": "search.json", "sha256": sha256(search), "size_bytes": len(search), "object_count": len(objects)},
        "shards": shards, **contract.AXES, "extensions": [
            {"id": "mathgraph.catalogue-environment-byte-trust", "version": 1, "critical": False, "payload": environment},
            {"id": "mathgraph.catalogue-source-policy", "version": 1, "critical": False,
             "payload": {"sha256": sha256(source.policy_bytes), "build_inputs": p["build_inputs"]}}]}
    files.extend([("manifest.json", contract.canonical_bytes(manifest)), ("search.json", search)])
    publication = CataloguePublication(tuple(sorted(files)))
    validate_publication(publication)
    return publication


def validate_publication(publication: CataloguePublication) -> None:
    files = dict(publication.files)
    require(len(files) == len(publication.files), "duplicate publication path")
    manifest = contract.validate_manifest(files["manifest.json"])
    require(files["manifest.json"] == contract.canonical_bytes(manifest), "noncanonical manifest")
    require(set(files) == {"manifest.json", "search.json", *(s["path"] for s in manifest["shards"])}, "publication file inventory mismatch")
    search = files["search.json"]
    require(sha256(search) == manifest["search"]["sha256"] and len(search) == manifest["search"]["size_bytes"], "search integrity mismatch")
    expected = []
    for s in manifest["shards"]:
        shard = contract.validate_shard(files[s["path"]], manifest)
        for o in shard["objects"]:
            expected.append({"object_id": o["object_id"], "qualified_name": o["qualified_name"], "module": o["source"]["module"], "kind": o["kind"], "statement": o["statement"]})
    expected.sort(key=lambda r: contract._key(r["qualified_name"]))
    require(search == contract.canonical_bytes(expected), "search must be derived from occurrences")
    require(sum(len(b) for b in files.values()) <= MAX_PUBLICATION_BYTES, "publication raw budget exceeded")
    require(sum(len(gzip.compress(b, mtime=0)) for b in files.values()) <= MAX_PUBLICATION_GZIP_BYTES, "publication gzip budget exceeded")


def publish_catalogue(publication: CataloguePublication, output_dir: Path, *, check: bool = False) -> None:
    validate_publication(publication)
    output = output_dir.absolute()
    require(not output.is_symlink() and all(not p.is_symlink() for p in output.parents), "symlink publication root")
    require(output not in {Path("/"), Path.home(), ROOT} and not ROOT.is_relative_to(output), "unsafe publication root")
    expected = dict(publication.files)
    if output.exists():
        actual = {}
        for path in output.rglob("*"):
            require(not path.is_symlink(), "symlink publication entry")
            if path.is_file(): actual[path.relative_to(output).as_posix()] = path.read_bytes()
        if check:
            require(actual == expected, "publication differs: changed, added, or missing bytes")
            return
        # Existing publications may be replaced; unrelated output is never erased.
        validate_publication(CataloguePublication(tuple(sorted(actual.items()))))
    else:
        require(not check, "publication missing")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".catalogue-staging-", dir=output.parent))
    backup = staging.with_name(staging.name + "-previous")
    try:
        for relative, data in publication.files:
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        if output.exists(): output.rename(backup)
        try: staging.rename(output)
        except OSError:
            if backup.exists(): backup.rename(output)
            raise
        if backup.exists(): shutil.rmtree(backup)
    finally:
        if staging.exists(): shutil.rmtree(staging)


def run_lean_extractor(source: VerifiedSource, extractor: Path, modules: Sequence[str]) -> bytes:
    """Invoke only the offline harness; its environment inputs are local paths.

    MATHGRAPH_CATALOGUE_ENVIRONMENT names JSON with image, inventory path,
    dependency root, and inventory digest. Acquisition is a separate operation.
    """
    config_path = os.environ.get("MATHGRAPH_CATALOGUE_ENVIRONMENT")
    require(bool(config_path), "local offline environment configuration required")
    config = contract._load(Path(config_path).read_bytes(), contract.LIMITS["max_manifest_bytes"])
    return run_offline_extraction(source, extractor, modules, config)


def _prepare_container_output(root: Path) -> None:
    """Open one fresh scratch leaf to an otherwise non-owner container UID."""
    require(not root.exists() and not root.is_symlink(), "container output leaf must be new")
    require(root.parent.is_dir() and not root.parent.is_symlink(), "container output parent is unsafe")
    root.mkdir(mode=0o700)
    root.chmod(0o733)
    require(stat.S_IMODE(root.stat().st_mode) == 0o733,
            "container output leaf is not non-owner writable")


def _revoke_container_output(root: Path) -> None:
    require(root.is_dir() and not root.is_symlink(), "container output leaf changed type")
    root.chmod(0o700)
    require(stat.S_IMODE(root.stat().st_mode) == 0o700,
            "container output permissions could not be revoked")


def _container_output_type(path: Path) -> str:
    mode = path.lstat().st_mode
    if stat.S_ISREG(mode):
        return "regular"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISLNK(mode):
        return "symlink"
    return "other"


def _seal_container_output(
    root: Path,
    allowed: set[str],
    required: set[str],
    *,
    stage: str,
) -> tuple[Path, ...]:
    """Revoke container writes and accept only exact regular output names."""
    _revoke_container_output(root)
    require(re.fullmatch(r"[a-z0-9-]{1,64}", stage) is not None,
            "invalid container output stage")
    require(required <= allowed and bool(required), "invalid container output contract")
    entries = tuple(sorted(root.iterdir(), key=lambda path: path.name.encode("utf-16-be")))
    names = {path.name for path in entries}
    if not required <= names <= allowed:
        # Output names and node kinds locate a hosted-runtime contract mismatch
        # without exposing source or compiled file contents. Keep the diagnostic
        # bounded even if a compromised child creates many entries.
        observed = [
            {"name": path.name, "type": _container_output_type(path)}
            for path in entries[:16]
        ]
        detail = " ".join((
            f"stage={stage}",
            f"observed_count={len(entries)}",
            "observed=" + json.dumps(observed, sort_keys=True, separators=(",", ":")),
            "allowed=" + json.dumps(sorted(allowed), separators=(",", ":")),
            "required=" + json.dumps(sorted(required), separators=(",", ":")),
        ))
        raise ValueError("container output set mismatch: " + detail)
    for path in entries:
        metadata = path.lstat()
        require(not path.is_symlink() and stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1,
                "container output must be a single regular file")
    return entries


def run_offline_extraction(source: VerifiedSource, extractor: Path, modules: Sequence[str], config: dict) -> bytes:
    contract._shape(config, {"image", "dependency_root", "inventory", "dependency_inventory_sha256"} | ({"toolchain"} if "toolchain" in config else set()))
    validate_image_digest(config["image"])
    toolchain = config.get("toolchain")
    if toolchain is not None:
        contract._shape(toolchain, {"root", "inventory"})
        require(config["image"] == BASE_IMAGE, "external toolchain requires exact base image")
        verify_toolchain_tree(Path(toolchain["root"]), Path(toolchain["inventory"]), TOOLCHAIN_PROFILE)
        inspected = subprocess.check_output(["docker", "image", "inspect", "--format", '{"id":"{{.Id}}","os":"{{.Os}}","arch":"{{.Architecture}}"}', BASE_IMAGE])
        require(json.loads(inspected) == {"id": BASE_IMAGE_CONFIG, "os": "linux", "arch": "amd64"}, "base manifest/config/platform mismatch")
    else:
        require(config["image"] != BASE_IMAGE, "base image requires verified external toolchain")
    policy = json.loads(source.policy_bytes)
    require(list(modules) == [m["module"] for m in policy["modules"]], "extraction must use exact selected module list")
    verified = verify_source_checkout(policy, source.root)
    require(verified == source, "source changed after verification")
    inventory = contract._load(Path(config["inventory"]).read_bytes(), 128 * 1024 * 1024)
    dependencies = Path(config["dependency_root"]).absolute()
    verify_dependency_inventory(dependencies, inventory, config["dependency_inventory_sha256"])
    require(inventory["source_commit"] == policy["source"]["commit"] and inventory["source_tree"] == policy["source"]["tree"], "cache acquisition pin mismatch")
    lock = json.loads(dict(source.files)[policy["source"]["lake_manifest"]["path"]])
    require({p["name"]: (p["rev"], p["url"]) for p in lock["packages"]} == {p["name"]: (p["commit"], p["repository"]) for p in inventory["packages"]}, "dependency lock mismatch")
    require(extractor.is_file() and not extractor.is_symlink(), "local extractor file required")
    with tempfile.TemporaryDirectory(prefix="mathgraph-catalogue-offline-") as scratch:
        work = Path(scratch)
        # Snapshot only verified Git source and explicitly inventoried artifacts.
        snapshot = work / "source"
        snapshot.mkdir()
        for relative, mode, blob in _tree_entries(source.root, policy["source"]["commit"]):
            path = snapshot / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = _tracked_bytes(source.root, relative, mode)
            require(_git_blob(raw) == blob, "source changed while snapshotting")
            if mode == b"120000": path.symlink_to(raw.decode())
            else:
                path.write_bytes(raw)
                path.chmod(0o755 if mode == b"100755" else 0o644)
        audit_source = work / "verified-source"
        shutil.copytree(snapshot, audit_source, symlinks=True)
        audit_dependencies = work / "verified-dependencies"
        audit_dependencies.mkdir()
        selected_paths = [m.replace(".", "/") for m in modules]
        build_roots = ["build/", *[p["path"] + "/.lake/build/" for p in inventory["packages"]]]
        for entry in inventory["files"]:
            path = audit_dependencies / entry["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            if entry["mode"] == "120000":
                package, relative = _dependency_package_for_path(inventory["packages"], entry["path"])
                target = dependency_symlink_target(dependencies / package["path"], package, relative)
                require(target == entry["target"], "dependency symlink target changed while snapshotting")
                raw = target.encode("utf-8", errors="strict")
            else:
                origin = _safe_file(dependencies, entry["path"])
                require(("100755" if origin.stat().st_mode & 0o111 else "100644") == entry["mode"], "dependency mode changed while snapshotting")
                raw = origin.read_bytes()
            require(len(raw) == entry["size_bytes"] and sha256(raw) == entry["sha256"], "dependency changed while snapshotting")
            # Exclude every selected-origin output suffix, including private,
            # server, trace, native and future sidecars, from all cache mounts.
            # Original inventoried bytes remain verified but never searchable.
            build_path = next((entry["path"][len(prefix):] for prefix in build_roots if entry["path"].startswith(prefix)), None)
            if build_path is not None and any("/" + selected + "." in "/" + build_path for selected in selected_paths):
                continue
            if entry["mode"] == "120000":
                path.symlink_to(entry["target"])
            else:
                path.write_bytes(raw)
                path.chmod(0o755 if entry["mode"] == "100755" else 0o644)
        shutil.copytree(audit_dependencies, snapshot / ".lake", symlinks=True)
        git_mounts = []
        for package in inventory["packages"]:
            metadata = sanitized_git_files(dependencies / package["path"], package)
            require(git_metadata_digest(metadata) == package["git_metadata_sha256"], "dependency Git changed while snapshotting")
            git_dir = work / "git-identities" / package["name"]
            for relative, raw in metadata:
                path = git_dir / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            (git_dir / "refs").mkdir()
            (snapshot / ".lake" / package["path"] / ".git").mkdir()
            git_mounts += ["--mount", f"type=bind,src={git_dir},dst=/work/.lake/{package['path']}/.git,readonly"]
        # Lean resolves a module prefix at its first search root, so selected
        # outputs must share the root with retained unselected siblings. Child
        # processes see this entire tree read-only; only the host inserts fresh
        # selected outputs after each isolated compiler exits successfully.
        compiled, plan = snapshot / ".lake/build/lib/lean", work / "plan"
        compiled.mkdir(parents=True, exist_ok=True)
        out = work / "output"
        # Image is deliberately --pull never; Docker itself cannot acquire it.
        # The actual compiled source/cache roots are read-only, not just audit
        # copies. Earlier compiled outputs also remain read-only in every process.
        command = ["docker", "run", "--rm", "--pull", "never", "--network", "none", "--read-only",
                   "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--tmpfs", "/tmp:rw,nosuid,nodev",
                   "--mount", f"type=bind,src={audit_source},dst=/verified-source,readonly",
                   "--mount", f"type=bind,src={audit_dependencies},dst=/verified-dependencies,readonly",
                   "--mount", f"type=bind,src={extractor.resolve()},dst=/extract/Extract.lean,readonly",
                   "--mount", f"type=bind,src={extractor.parent / 'CompileOrder.lean'},dst=/extract/CompileOrder.lean,readonly",
                   "--mount", f"type=bind,src={snapshot},dst=/work,readonly",
                   "--mount", f"type=bind,src={compiled},dst=/compiled,readonly", *git_mounts,
                   "--workdir", "/work", "--env", "HOME=/tmp",
                   "--env", "LEAN_PATH=" + ":".join(["/compiled", *["/work/.lake/" + p["path"] + "/.lake/build/lib/lean" for p in inventory["packages"]]]),
                   "--env", "LEAN_SRC_PATH=" + ":".join(["/work", *["/work/.lake/" + p["path"] for p in inventory["packages"]]]),
                   "--env", "MATHGRAPH_EXPECTED_TOOLCHAIN=" + policy["source"]["lean_toolchain"]["value"],
                   "--entrypoint", "/bin/sh"]
        for key, value in git_runtime_environment(inventory["packages"]).items():
            command += ["--env", key + "=" + value]
        lean_command = "/opt/lean/bin/lean" if toolchain is not None else "lean"
        if toolchain is not None:
            command += ["--platform", "linux/amd64", "--mount", f"type=bind,src={Path(toolchain['root']).resolve()},dst=/opt/lean,readonly",
                        "--env", "PATH=/opt/lean/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"]
        else:
            command += ["--env", "ELAN_HOME=/opt/elan"]
        toolchain_check = ('test "$(cat lean-toolchain)" = "$MATHGRAPH_EXPECTED_TOOLCHAIN"; '
                           'version=${MATHGRAPH_EXPECTED_TOOLCHAIN##*:v}; '
                           f'case "$({lean_command} --version)" in "Lean (version $version,"*) ;; *) exit 1 ;; esac; ')
        if toolchain is not None:
            toolchain_check += f'test "$({lean_command} --githash)" = "{TOOLCHAIN_PROFILE["lean_commit"]}"; '
        _prepare_container_output(plan)
        try:
            subprocess.run([*command, "--mount", f"type=bind,src={plan},dst=/plan", config["image"],
                            "-eu", "-c", toolchain_check + lean_command + ' --run /extract/CompileOrder.lean /plan/order.json "$@"', "catalogue", *modules], check=True)
        finally:
            _revoke_container_output(plan)
        _seal_container_output(
            plan, {"order.json"}, {"order.json"}, stage="compile-order")
        order = contract._load(_safe_file(plan, "order.json").read_bytes(), contract.LIMITS["max_manifest_bytes"])
        contract._shape(order, {"modules"})
        require(type(order["modules"]) is list and len(order["modules"]) == len(modules) and set(order["modules"]) == set(modules), "invalid compilation order")
        for index, module in enumerate(order["modules"]):
            destination = work / f"module-{index}"
            _prepare_container_output(destination)
            try:
                subprocess.run([*command, "--mount", f"type=bind,src={destination},dst=/module-output", config["image"],
                                "-eu", "-c", toolchain_check + lean_command + " " + " ".join(COMPILE_FLAGS) + ' -R /work -o /module-output/module.olean "$1"',
                                "catalogue", module.replace(".", "/") + ".lean"], check=True)
            finally:
                _revoke_container_output(destination)
            produced = _seal_container_output(
                destination,
                {"module.olean", "module.olean.private", "module.olean.server"},
                {"module.olean"},
                stage="compile-selected-module",
            )
            for artifact in produced:
                raw = _safe_file(destination, artifact.name).read_bytes()
                target = compiled / (module.replace(".", "/") + artifact.name.removeprefix("module"))
                require(not target.exists(), "selected output would replace retained artifact")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
        _prepare_container_output(out)
        try:
            subprocess.run([*command, "--mount", f"type=bind,src={out},dst=/output", config["image"], "-eu", "-c",
                            toolchain_check + lean_command + ' --run /extract/Extract.lean /work /output/extraction.json "$@"',
                            "catalogue", *modules], check=True)
        finally:
            _revoke_container_output(out)
        _seal_container_output(
            out, {"extraction.json"}, {"extraction.json"}, stage="extract-catalogue")
        result = _safe_file(out, "extraction.json").read_bytes()
        require(len(result) <= MAX_EXTRACTION_BYTES, "extractor output too large")
        return result
