"""Stdlib-only gate, entered with -I -S -B before importing checkout code.

The pinned launcher/bootstrap, Python runtime, and Git executable are the trust
root. All tracked producer bytes are verified against the requested commit's
tree; imports use only fresh verified sources, never checkout bytecode.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

PRODUCER_FILES = (
    "mathgraph/source_catalogue_publisher_v1.py", "mathgraph_protocol/__init__.py",
    "mathgraph_protocol/discovery_ranking.py", "mathgraph_protocol/json_strict.py",
    "mathgraph_protocol/source_catalogue_v1.py", "scripts/catalogue_bootstrap_v1.py",
    "scripts/publish_mathlib_source_catalogue_v1.py", "scripts/run_mathlib_source_catalogue_offline_v1.py",
    "tools/mathlib_catalogue/CompileOrder.lean", "tools/mathlib_catalogue/Extract.lean")


def require(condition, message):
    if not condition:
        raise ValueError("producer bootstrap: " + message)


def git(root, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_NO_REPLACE_OBJECTS="1", GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    return subprocess.check_output(["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-C", str(root), *args], env=env, stderr=subprocess.PIPE)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate identity key")
        result[key] = value
    return result


def verified_sources(root, identity):
    commit = identity.get("source_commit")
    require(isinstance(commit, str) and re.fullmatch("[0-9a-f]{40}", commit), "exact commit required")
    require(git(root, "rev-parse", "HEAD").decode().strip() == commit, "wrong commit")
    require(Path(git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve() == root.resolve(), "wrong checkout root")
    require(not git(root, "status", "--porcelain=v1", "--untracked-files=all").strip(), "dirty checkout")
    require([f["path"] for f in identity["sources"]] == list(PRODUCER_FILES), "incomplete import/bootstrap closure")
    required = {f["path"]: f["sha256"] for f in identity["sources"]}
    verified = {}
    # The exact commit binds its tree; index flags cannot substitute for bytes.
    for item in git(root, "ls-tree", "-rz", commit).split(b"\0"):
        if not item:
            continue
        meta, encoded_path = item.split(b"\t", 1)
        mode, kind, oid = meta.split()
        relative = encoded_path.decode("utf-8")
        require(not relative.startswith("/") and all(p not in {"", ".", ".."} for p in relative.split("/")), "unsafe tracked path")
        path = root / relative
        require(kind == b"blob" and mode in {b"100644", b"100755"}, "unsupported producer tree entry")
        require(not any(p.is_symlink() for p in [path, *path.parents] if p.is_relative_to(root)), "symlink producer path")
        raw = path.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        require(blob == oid.decode(), "tracked producer bytes differ from commit: " + relative)
        require(bool(path.stat().st_mode & 0o111) == (mode == b"100755"), "tracked producer executable mode differs")
        if relative in required:
            require(hashlib.sha256(raw).hexdigest() == required[relative], "source identity digest mismatch")
            verified[relative] = raw
    require(set(verified) == set(required), "missing tracked producer source")
    return verified


def main():
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, "isolated -I -S -B invocation required")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["publish", "extract"], required=True)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--source-policy", type=Path, required=True)
    parser.add_argument("--extractor-identity", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--environment", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    identity = json.loads(args.extractor_identity.read_bytes(), object_pairs_hook=unique_object)
    root = Path(__file__).resolve().parents[1]
    sources = verified_sources(root, identity)
    with tempfile.TemporaryDirectory(prefix="mathgraph-producer-verified-") as temporary:
        snapshot = Path(temporary)
        for relative, raw in sources.items():
            path = snapshot / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        sys.path[:0] = [str(snapshot), str(snapshot / "mathgraph")]
        import source_catalogue_publisher_v1 as publisher
        publisher.verify_extractor_identity(identity, root)
        policy = publisher.load_source_policy(args.source_policy)
        source = publisher.verify_source_checkout(policy, args.checkout)
        config_path = args.environment if args.mode == "extract" else os.environ.get("MATHGRAPH_CATALOGUE_ENVIRONMENT")
        require(bool(config_path), "local environment configuration required")
        config = publisher.contract._load(Path(config_path).read_bytes(), publisher.contract.LIMITS["max_manifest_bytes"])
        require(config["image"] == identity["environment"]["image"] and config["dependency_inventory_sha256"] == identity["environment"]["dependency_inventory_sha256"], "environment identity mismatch")
        require(("toolchain" in config) == ("toolchain" in identity["environment"]), "toolchain identity mismatch")
        result = publisher.run_offline_extraction(source, snapshot / "tools/mathlib_catalogue/Extract.lean", [m["module"] for m in policy["modules"]], config)
        if args.mode == "publish":
            require(args.output_dir is not None and args.output is None and args.environment is None, "publishing output directory required")
            publisher.publish_catalogue(publisher.build_publication(policy, source, identity, result), args.output_dir, check=args.check)
        else:
            require(args.output is not None and args.output_dir is None and not args.check, "fresh extraction output required")
            with args.output.open("xb") as handle:
                handle.write(result)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f"catalogue producer declined: {error}", file=sys.stderr)
        sys.exit(1)
