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
    "mathgraph/source_catalogue_publisher_v1.py", "mathgraph_protocol/json_strict.py",
    "mathgraph_protocol/source_catalogue_v1.py", "scripts/publish_mathlib_source_catalogue_v1.py",
    "scripts/run_mathlib_source_catalogue_offline_v1.py", "tools/mathlib_catalogue/Extract.lean")


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
    contract._shape(e, {"image", "dependency_inventory_sha256", "authority"})
    validate_image_digest(e["image"])
    contract._digest(e["dependency_inventory_sha256"])
    require(e["authority"] == "NONE", "environment trust grants no authority")
    return e


def verify_extractor_identity(identity: dict, root: Path = ROOT) -> None:
    contract._shape(identity, {"source_commit", "contract_version", "sources", "environment"})
    contract._digest(identity["source_commit"], 40)
    require(type(identity["contract_version"]) is int and identity["contract_version"] == 1, "unsupported extractor contract")
    _environment(identity)
    head = _git(root, "rev-parse", "HEAD").decode().strip()
    require(head == identity["source_commit"], "producer source commit mismatch")
    require(not _git(root, "status", "--porcelain=v1", "--untracked-files=all").strip(), "MathGraph checkout must be clean")
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
    paths = set()
    for f in inventory["files"]:
        contract._file(f, {"size_bytes", "mode"})
        contract._integer(f["size_bytes"])
        require(f["mode"] in {"100644", "100755"}, "unsupported environment file mode")
        contract._unique(f["path"], paths)
        require(".git" not in Path(f["path"]).parts, "Git administration is not an environment artifact")
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
        require(not path.is_symlink(), "symlink in dependency closure")
        if path.is_file(): actual.add(relative.as_posix())
    require(paths == actual and bool(paths), "arbitrary or incomplete dependency build state")
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
    _verify_tree(root, package["commit"], package["tree"])
    require(_git(root, "config", "--local", "--get-all", "remote.origin.url").decode().strip() == repository, "dependency remote mismatch")
    entries = list(_tree_entries(root, package["commit"]))
    require(all(mode != b"120000" for _, mode, _ in entries), "dependency symlink not admitted")
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


def run_offline_extraction(source: VerifiedSource, extractor: Path, modules: Sequence[str], config: dict) -> bytes:
    contract._shape(config, {"image", "dependency_root", "inventory", "dependency_inventory_sha256"})
    validate_image_digest(config["image"])
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
        for entry in inventory["files"]:
            path = audit_dependencies / entry["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            origin = _safe_file(dependencies, entry["path"])
            require(("100755" if origin.stat().st_mode & 0o111 else "100644") == entry["mode"], "dependency mode changed while snapshotting")
            raw = origin.read_bytes()
            require(len(raw) == entry["size_bytes"] and sha256(raw) == entry["sha256"], "dependency changed while snapshotting")
            path.write_bytes(raw)
            path.chmod(0o755 if entry["mode"] == "100755" else 0o644)
        shutil.copytree(audit_dependencies, snapshot / ".lake")
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
        # Invalidate every selected origin's compilation, including private/server
        # data, IR, hashes, traces, native objects, and generated C.
        for module in modules:
            suffix = module.replace(".", "/")
            for base in [snapshot / ".lake/build/lib/lean", snapshot / ".lake/build/ir"]:
                parent = base / str(Path(suffix).parent)
                stem = Path(suffix).name
                if parent.exists():
                    for artifact in parent.iterdir():
                        if artifact.is_file() and artifact.name.startswith(stem + "."):
                            artifact.unlink()
        out = work / "output"
        out.mkdir()
        # Image is deliberately --pull never; Docker itself cannot acquire it.
        # Sources/dependencies are mounted read-only for audit; only fresh snapshot
        # build/output roots are writable. --network none applies to build + extract.
        command = ["docker", "run", "--rm", "--pull", "never", "--network", "none", "--read-only",
                   "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--tmpfs", "/tmp:rw,nosuid,nodev",
                   "--mount", f"type=bind,src={audit_source},dst=/verified-source,readonly",
                   "--mount", f"type=bind,src={audit_dependencies},dst=/verified-dependencies,readonly",
                   "--mount", f"type=bind,src={extractor.resolve()},dst=/extract/Extract.lean,readonly",
                   "--workdir", "/work", "--env", "HOME=/tmp", "--env", "ELAN_HOME=/opt/elan",
                   "--env", "MATHGRAPH_EXPECTED_TOOLCHAIN=" + policy["source"]["lean_toolchain"]["value"],
                   "--entrypoint", "/bin/sh"]
        for key, value in git_runtime_environment(inventory["packages"]).items():
            command += ["--env", key + "=" + value]
        toolchain_check = ('test "$(cat lean-toolchain)" = "$MATHGRAPH_EXPECTED_TOOLCHAIN"; '
                           'version=${MATHGRAPH_EXPECTED_TOOLCHAIN##*:v}; '
                           'case "$(lean --version)" in "Lean (version $version,"*) ;; *) exit 1 ;; esac; ')
        subprocess.run([*command, "--mount", f"type=bind,src={snapshot},dst=/work", *git_mounts, config["image"],
                        "-eu", "-c", toolchain_check + 'lake build "$@"', "catalogue", *modules], check=True)
        # Extraction gets a read-only compiled snapshot, distinct from the build
        # process; only its requested output directory and private /tmp can write.
        subprocess.run([*command, "--mount", f"type=bind,src={snapshot},dst=/work,readonly",
                        *git_mounts, "--mount", f"type=bind,src={out},dst=/output", config["image"], "-eu", "-c",
                        toolchain_check + 'lake env lean --run /extract/Extract.lean /work /output/extraction.json "$@"',
                        "catalogue", *modules], check=True)
        require([p.name for p in out.iterdir()] == ["extraction.json"], "extractor wrote unexpected output")
        result = _safe_file(out, "extraction.json").read_bytes()
        require(len(result) <= MAX_EXTRACTION_BYTES, "extractor output too large")
        return result
