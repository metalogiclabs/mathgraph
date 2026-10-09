#!/usr/bin/env python3
"""Check exact source identity of published OpenAI Logspace model definitions.

This checks text and blob pins, not compiled Lean declaration identities.
"""
import hashlib
import json
import urllib.request
from pathlib import Path

PIN = "fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb"
BASE = f"https://raw.githubusercontent.com/openai/math/{PIN}/"
SOURCES = {
    "challenge": (
        "lean/ComparatorChallenges/LogspaceEquality.lean",
        "692a4bdc0de7de093d83abdcb7a2bb1ccb7d476b",
    ),
    "solution_model": (
        "lean/OAI/Computability/Logspace/Deterministic.lean",
        "ca35b7665ff47fddaaadc8fa0390c9cdf8dcebb1",
    ),
}
START = "abbrev Word := List Bool"
END = "(x ∉ A → M.acceptanceProbability x (polynomialClock c k x.length) ≤ (1 / 3 : ℚ))}"

def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\\0" + data).hexdigest()

def model_block(source: str) -> str:
    first = source.find(START)
    if first < 0:
        raise ValueError("MODEL_START_NOT_FOUND")
    last = source.find(END, first)
    if last < 0:
        raise ValueError("MODEL_END_NOT_FOUND")
    if source.find(START, first+1) >= 0:
        raise ValueError("AMBIGUOUS_MODEL_START")
    return source[first:last+len(END)]

def audit(loader):
    raw = {}
    for key, (path, sha) in SOURCES.items():
        b = loader(path)
        if blob_sha(b) != sha:
            raise ValueError(f"SOURCE_BLOB_MISMATCH: {key}")
        raw[key] = b.decode("utf-8")
    a = model_block(raw["challenge"])
    b = model_block(raw["solution_model"])
    if a != b:
        index = next((i for i,(x,y) in enumerate(zip(a,b)) if x != y), min(len(a), len(b)))
        raise ValueError(f"MODEL_SOURCE_MISMATCH: char {index}")
    return {
        "upstream_commit": PIN,
        "source_paths": {k: SOURCES[k][0] for k in SOURCES},
        "source_blobs": {k: SOURCES[k][1] for k in SOURCES},
        "characters_compared": len(a),
        "status": "WARRANTED_PINNED_MODEL_TEXT_IDENTITY",
        "compiled_declarations_equal": None,
        "comparator_default_definition_holes": 20,
        "limitation": "Exact UTF-8 source-block equality, not independently verified environment identity or paper-to-model semantic adequacy",
    }

def load_remote(path):
    with urllib.request.urlopen(BASE + path, timeout=45) as resp:
        return resp.read()

def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output")
    opt = p.parse_args()
    data = audit(load_remote)
    result = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if opt.output:
        Path(opt.output).write_text(result)
    print(result)

if __name__ == "__main__":
    main()
