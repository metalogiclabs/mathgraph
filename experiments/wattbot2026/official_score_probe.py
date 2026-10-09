#!/usr/bin/env python3
"""Invoke the PINNED official WattBot scorer on a trivial train-only baseline.

No official training labels are exposed or copied. No protected test labels are
used. This does not assert that the all-blank baseline is competitive.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import zipfile

EXPECTED = "e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075"
COLUMNS = ("id", "question", "answer", "answer_value", "answer_unit", "ref_id",
           "ref_url", "supporting_materials", "explanation")


def score_api_signature(scorer_bytes: bytes) -> dict:
    tree = ast.parse(scorer_bytes.decode("utf-8-sig"))
    node = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name=="score"), None)
    if node is None:
        raise ValueError("Official file has no score() function")
    return {
        "parameters": [a.arg for a in node.args.args],
        "defaults": [ast.unparse(d) for d in node.args.defaults],
        "return_annotation": ast.unparse(node.returns) if node.returns else None,
    }


def run(zip_path: str) -> None:
    import pandas as pd
    with zipfile.ZipFile(zip_path) as z:
        original = z.read("Score.py")
        original_sha = hashlib.sha256(original).hexdigest()
        if original_sha != EXPECTED:
            raise ValueError(f"Official Score.py changed: {original_sha}. Re-audit scorer")
        train = pd.read_csv(z.open("train_QA.csv"), keep_default_na=False)
        schema = score_api_signature(original)
        print("SCORE_API_SHAPE=" + json.dumps(schema, sort_keys=True))
        print("PINNED_SCORER_SHA256=" + original_sha)
        # Only IDs and questions are read from train to create the candidate.
        blank = pd.DataFrame([{k: (
            str(row["id"]) if k=="id" else
            str(row["question"]) if k=="question" else
            "Unable to establish an answer from the permitted corpus." if k=="answer" else
            "No claim made; no cited evidence." if k=="explanation" else
            "is_blank")
            for k in COLUMNS
        } for _, row in train[["id", "question"]].iterrows()], columns=list(COLUMNS))
        with tempfile.TemporaryDirectory(prefix="wattbot_scorer_") as td:
            path = Path(td) / "Score.py"
            path.write_bytes(original)
            spec = importlib.util.spec_from_file_location("wattbot_official_scorer", path)
            if spec is None or spec.loader is None:
                raise RuntimeError("Could not load pinned scorer")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            import inspect
            sig = inspect.signature(module.score)
            kwargs = {}
            if "row_id_column_name" in sig.parameters:
                kwargs["row_id_column_name"] = "id"
            if "verbose" in sig.parameters:
                kwargs["verbose"] = False
            outcome = module.score(train, blank, **kwargs)
            # Inspect output types only when the result is complex: never log rows.
            if isinstance(outcome, (int, float)):
                result = {"official_train_blank_score": float(outcome)}
            elif isinstance(outcome, tuple):
                result = {"return_type": "tuple", "length": len(outcome),
                          "scalar_values": [float(v) if isinstance(v, (int,float)) else str(type(v).__name__) for v in outcome]}
            elif isinstance(outcome, dict):
                result = {"return_type": "dict", "entries": {str(k): float(v) if isinstance(v, (int,float)) else str(type(v).__name__) for k,v in outcome.items()}}
            else:
                result = {"return_type": type(outcome).__name__, "return_repr": str(outcome)[:500]}
            print("OFFICIAL_TRAIN_BLANK_BASELINE=" + json.dumps(result, sort_keys=True))
            print("BASELINE_ROWS=" + str(len(blank)))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip",required=True)
    a=p.parse_args()
    run(a.official_zip)
