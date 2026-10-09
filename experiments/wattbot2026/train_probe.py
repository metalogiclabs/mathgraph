#!/usr/bin/env python3
"""WattBot 2026: source-only retrieval diagnostic on official training labels.

No test labels used. No private row text, references, or full data is printed.
This is not the official WattBot score or an answer-generation system.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import csv
import hashlib
import io
import json
import math
import re
import zipfile

TOKEN = re.compile(r"[a-z]+|\d+(?:\.\d+)?", re.I)
NA = {"", "is_blank", "nan", "none", "null", "[]", "n/a", "na"}


def parse_refs(value: str) -> list[str]:
    s = str(value or "").strip()
    if s.casefold() in NA:
        return []
    try:
        parsed = ast.literal_eval(s)
    except (SyntaxError, ValueError, TypeError, MemoryError):
        parsed = s
    if isinstance(parsed, (list, tuple, set)):
        values = list(parsed)
    elif isinstance(parsed, (str, int, float)):
        values = [parsed]
    else:
        return []
    output = []
    for item in values:
        if item is None:
            continue
        for element in re.split(r"[,;|]", str(item)):
            t = element.strip().strip("'\"")
            if t and t.casefold() not in NA and t not in output:
                output.append(t)
    return output


def tokens(s: str) -> list[str]:
    return TOKEN.findall(str(s).casefold())


def score_metadata(question: str, metadata: list[dict], top_k: int = 8) -> list[str]:
    docs = [(d["id"], tokens(" ".join(
        str(d.get(k, "") or "") for k in ("title", "citation", "year", "venue")
    ))) for d in metadata]
    n = len(docs)
    if not n:
        return []
    avgl = max(1., sum(len(x) for _, x in docs) / n)
    df = Counter(t for _, words in docs for t in set(words))
    q = set(tokens(question))
    scores = []
    for doc_id, words in docs:
        tf = Counter(words)
        L = 0.25 + 0.75 * len(words) / avgl
        value = sum(math.log(1 + (n - df[t] + .5) / (df[t] + .5))
                    * (tf[t] * 2.2 / (tf[t] + 1.2 * L))
                    for t in q if tf[t])
        scores.append((value, doc_id))
    scores.sort(key=lambda p: (-p[0], p[1]))
    return [doc_id for v, doc_id in scores[:top_k] if v > 0]


def load_csv(z, name):
    return list(csv.DictReader(io.StringIO(z.read(name).decode("utf-8-sig"))))


def scorer_shape(source):
    tree = ast.parse(source.decode("utf-8-sig"))
    methods = []
    imports = set()
    has_main_guard = False
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append({"name": node.name, "positional": [p.arg for p in node.args.args]})
        elif isinstance(node, ast.Import):
            imports.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
            has_main_guard |= isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__"
    return {"functions": methods, "imports": sorted(imports), "main_guard": has_main_guard}


def summarize(path):
    with zipfile.ZipFile(path) as z:
        meta = load_csv(z, "metadata.csv")
        train = load_csv(z, "train_QA.csv")
        test = load_csv(z, "test_Q.csv")
        known = {str(row["id"]) for row in meta}
        gold = {r["id"]: parse_refs(r.get("ref_id", "")) for r in train}
        nonblank = [(row, gold[row["id"]]) for row in train if gold[row["id"]]]
        unresolved = [(row, ids) for row, ids in nonblank if not set(ids) <= known]
        shape = Counter("blank" if not ids else "one" if len(ids) == 1 else "multiple" for ids in gold.values())
        fields = ("Quote", "Table", "Figure", "Math", "is_NA", "CrossPaper", "Reconcile")
        flags = {key: dict(Counter(str(x.get(key, "")).strip().casefold() for x in train)) for key in fields}
        print("TRAIN_SHAPE=" + json.dumps({
            "train_rows": len(train), "test_rows": len(test), "source_records": len(meta),
            "citation_shape": dict(shape), "unknown_ref_rows": len(unresolved),
            "unknown_ref_total": sum(len(set(ids)-known) for _, ids in unresolved),
            "gold_ref_lengths": dict(Counter(str(len(ids)) for ids in gold.values())),
            "metadata_types": dict(Counter(str(d.get("type", "")).strip() for d in meta)),
            "flags": flags,
        }, sort_keys=True))
        print("SCORER_AST=" + json.dumps(scorer_shape(z.read("Score.py")), sort_keys=True))
        metrics = {}
        for k in (1, 3, 8):
            evaluable = [(r, refs) for r, refs in nonblank if set(refs) <= known]
            any_hits = 0
            all_hits = 0
            frac_sum = 0.
            zero_hits = 0
            for row, ids in evaluable:
                predicted = set(score_metadata(row["question"], meta, top_k=k))
                hit = len(predicted.intersection(ids))
                any_hits += hit > 0
                all_hits += hit == len(ids)
                frac_sum += hit / len(ids)
                zero_hits += not predicted
            n = len(evaluable)
            metrics[f"at_{k}"] = {"evaluable": n, "any_gold": round(any_hits/n, 4) if n else None,
                                 "all_gold": round(all_hits/n, 4) if n else None,
                                 "mean_gold_fraction": round(frac_sum/n, 4) if n else None,
                                 "zero_lexical_hits": zero_hits}
        print("METADATA_BM25_TRAIN_DIAGNOSTIC=" + json.dumps(metrics, sort_keys=True))
        # Test columns are visible, but do not inspect any test answers or labels.
        assert len({r["id"] for r in train}) == len(train)
        assert len({r["id"] for r in test}) == len(test)


def self_test():
    assert parse_refs("['d1', 'd2']") == ["d1", "d2"]
    assert parse_refs('["d1","d2"]') == ["d1", "d2"]
    assert parse_refs("is_blank") == []
    assert parse_refs("d1") == ["d1"]
    assert parse_refs("d1;d2") == ["d1", "d2"]
    assert score_metadata("energy consumption in satellite", [
        {"id":"d1","title":"Satellite energy consumption","citation":""},
        {"id":"d2","title":"Agricultural biodiversity","citation":""}
    ], 1) == ["d1"]
    print("SELF_TESTS=PASS (synthetic only)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--official-zip")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        self_test()
    elif args.official_zip:
        summarize(args.official_zip)
    else:
        p.error("Provide --self-test or --official-zip")
