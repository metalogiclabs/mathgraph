#!/usr/bin/env python3
"""Frozen, source-independent normalization/slug semantic-obligation proposal arms.

Both arms read exactly the same public-API snapshot and metadata.
'Expert' means an independently specified conventional rulebook, NOT a human participant.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

NORMAL_TOKENS = ("normaliz", "normalis", "canonical", "standardiz", "standardis", "slug")
EXPERT_CONVENTIONAL = {
    "slugify": "slug",
    "slug": "slug",
    "to_slug": "slug",
    "normalize": "normalizer",
    "normalise": "normalizer",
    "canonicalize": "normalizer",
    "canonicalise": "normalizer",
    "standardize": "normalizer",
    "standardise": "normalizer",
}


def candidate_kind(symbol):
    # Morphological relation proposal: lexical hints in public names, not implementation.
    s = symbol.lower()
    if "slug" in s:
        return "slug"
    if any(k in s for k in NORMAL_TOKENS if k != "slug"):
        return "normalizer"
    return None


def expert_kind(symbol):
    # Matched conventional expert cookbook, with the same API/metadata access.
    return EXPERT_CONVENTIONAL.get(symbol.lower())


def propose(api, metadata, arm):
    assert arm in ("candidate", "expert")
    names = sorted(set(api["exports"]))
    kind_fn = candidate_kind if arm == "candidate" else expert_kind
    applicable = [(0 if kind_fn(name) == "slug" else 1, name, kind_fn(name))
                  for name in names if kind_fn(name)]
    result = {
        "protocol": "API_NORMALIZATION_CONTRACT_V3",
        "arm": arm, "repository": metadata["repository"],
        "source_sha": metadata["source_sha"],
        "description": metadata.get("description", ""),
        "api_sha256": api["api_sha256"], "api_module": api["module"],
        "relative_api_path": api["relative_api_path"],
        "public_symbols": names,
        "status": "UNKNOWN_NO_SUPPORTED_RELATION", "selected": None, "obligations": [],
        "assurance": "A predeclared finite relation grammar; no arbitrary intent extraction",
    }
    if not applicable:
        return result
    _, symbol, kind = sorted(applicable)[0]
    result["selected"] = {"symbol": symbol, "family": kind}
    result["status"] = "CANDIDATE_PENDING_NATIVE_AND_REFERENCE"
    result["obligations"].append({
        "id": "normalization-idempotence",
        "relation": "f(f(x)) = f(x) on the frozen input corpus",
        "authority": "metamorphic, source-native composition only",
        "verifier": "unmodified public function run twice",
    })
    if kind == "slug":
        result["obligations"].append({
            "id": "url-component-no-extra-encoding",
            "relation": "urllib.parse.quote(f(x), safe='') = f(x) on the frozen corpus",
            "authority": "independent Python 3.12 URL percent encoder; experimental path-segment policy",
            "verifier": "stdlib urllib.parse.quote, not a browser URL-security claim",
        })
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--api-view", type=Path, required=True)
    parser.add_argument("--arm", choices=("candidate", "expert"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    a = parser.parse_args()
    metadata = json.loads(a.metadata.read_text())
    assert re.fullmatch(r"[0-9a-f]{40}", metadata["source_sha"])
    api = json.loads(a.api_view.read_text())
    result = propose(api, metadata, a.arm)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("PRE_NATIVE_FROZEN_PROPOSAL", a.arm, result["status"],
          [(x["id"], result["selected"]) for x in result["obligations"]])


if __name__ == "__main__":
    main()
