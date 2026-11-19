"""Frozen prospective 24-project source-side calibration selection.

No network, project documents, defect labels, or model responses are read.
Input: committed 1408-identifier ASCII roster at pinned OSS-Fuzz tree.
"""
from __future__ import annotations
import json
from pathlib import Path

PINNED_COMMIT = "cdd107021c20428647db0699c33d6cb1f717474a"
PINNED_TREE = "f4005bbe6406d83b414112624b2a3d6cf461aa44"
EXCLUSIONS = frozenset((
    "aspectj", "cpp-httplib", "flex", "grpc-swift", "jaxb", "libexif",
    "mariadb-connector-j", "openapi-schema-validator", "protoc-gen-validate",
    "rust-regex", "teleport", "wolfboot",
))
SEED = (int(PINNED_COMMIT[:8], 16) ^ 0x4D475635) & 0xFFFFFFFF
MASK32 = 0xFFFFFFFF


def xorshift32(x: int) -> int:
    x ^= (x << 13) & MASK32
    x ^= (x >> 17)
    x ^= (x << 5) & MASK32
    return x & MASK32


def select() -> dict:
    raw = Path(__file__).with_name("oss_fuzz_ids_20261120.txt").read_bytes()
    assert raw.endswith(b"\n") and b"\r" not in raw
    ids = raw.decode("ascii").splitlines()
    assert len(ids) == 1408 and ids == sorted(ids)
    assert len(set(ids)) == len(ids)
    assert EXCLUSIONS.issubset(ids)
    remaining = [p for p in ids if p not in EXCLUSIONS]
    state = SEED
    for i in range(len(remaining) - 1, 0, -1):
        state = xorshift32(state)
        j = state % (i + 1)
        remaining[i], remaining[j] = remaining[j], remaining[i]
    selected = remaining[:24]
    assert len(selected) == len(set(selected)) == 24
    assert not EXCLUSIONS.intersection(selected)
    return {
        "schema": "mathgraph.eligibility.calibration.v0.5",
        "registry_commit": PINNED_COMMIT,
        "registry_projects_tree": PINNED_TREE,
        "id_count": len(ids),
        "prior_exclusions": sorted(EXCLUSIONS),
        "seed_uint32": SEED,
        "ordering": "ASCII ID sort; excluded 12; xorshift32 Fisher-Yates",
        "selection": selected,
        "status": "SELECTION_ONLY_NOT_ELIGIBILITY",
    }


if __name__ == "__main__":
    print(json.dumps(select(), sort_keys=True, indent=2))
