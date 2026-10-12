#!/usr/bin/env python3
"""Run the extractor with a local immutable container and verified dependency closure.

The environment JSON names image, dependency_root, inventory, and
dependency_inventory_sha256. The dependency root is an externally acquired
fresh exact-commit .lake cache. Its deterministic inventory contains schema,
acquisition=FRESH_EXACT_COMMIT_CACHE, source_commit, source_tree, packages
({name,path,commit,tree,repository,git_metadata_sha256}), and files
({path,sha256,size_bytes,mode}), all sorted. git_metadata_sha256 is computed by
git_metadata_digest(sanitized_git_files(package_root, package_record)). The
public HTTPS repository and commit must match the source dependency lock.
Only generated detached Git identities are mounted, read-only; original Git
configurations, credentials, hooks, and sockets are never exposed to the build.
Modes are Git-style 100644/100755 strings; executable permissions are pinned.
Acquisition receipts assert process provenance; their hashes protect bytes,
not mathematical truth. No cache is admitted solely because it is in .lake.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "mathgraph")]
import source_catalogue_publisher_v1 as publisher


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--source-policy", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    policy = publisher.load_source_policy(args.source_policy)
    source = publisher.verify_source_checkout(policy, args.checkout)
    config = publisher.contract._load(args.environment.read_bytes(), publisher.contract.LIMITS["max_manifest_bytes"])
    result = publisher.run_offline_extraction(source, ROOT / "tools/mathlib_catalogue/Extract.lean", [m["module"] for m in policy["modules"]], config)
    with args.output.open("xb") as output:
        output.write(result)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, publisher.subprocess.CalledProcessError) as error:
        print(f"offline extraction declined: {error}", file=sys.stderr)
        sys.exit(1)
