#!/usr/bin/env python3
"""Publish a local, verified source catalogue; never acquire remote inputs."""
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
    parser.add_argument("--extractor-identity", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    policy = publisher.load_source_policy(args.source_policy)
    identity = publisher.contract._load(args.extractor_identity.read_bytes(), publisher.contract.LIMITS["max_manifest_bytes"])
    publisher.verify_extractor_identity(identity)
    source = publisher.verify_source_checkout(policy, args.checkout)
    config_path = publisher.os.environ.get("MATHGRAPH_CATALOGUE_ENVIRONMENT")
    publisher.require(bool(config_path), "local offline environment configuration required")
    config = publisher.contract._load(Path(config_path).read_bytes(), publisher.contract.LIMITS["max_manifest_bytes"])
    publisher.require(config["image"] == identity["environment"]["image"] and
        config["dependency_inventory_sha256"] == identity["environment"]["dependency_inventory_sha256"], "extractor environment pin mismatch")
    output = publisher.run_offline_extraction(source, ROOT / "tools/mathlib_catalogue/Extract.lean", [m["module"] for m in policy["modules"]], config)
    publication = publisher.build_publication(policy, source, identity, output)
    publisher.publish_catalogue(publication, args.output_dir, check=args.check)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, publisher.subprocess.CalledProcessError) as error:
        print(f"catalogue declined: {error}", file=sys.stderr)
        sys.exit(1)
