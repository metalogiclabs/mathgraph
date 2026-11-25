"""Retrospective OpenC3 accessor-only calibration; no blind discovery claim."""
import argparse
import ast
import hashlib
import json
import platform
import random
from pathlib import Path
from types import SimpleNamespace

PINS = {
    "before": "97c3f9bd2401532bd2bc11db5af54e0dd8a560b4",
    "after": "a541c9c574994fa41e4d9681fffb00ab3fae5278",
}


def load(path, expected):
    raw = Path(path).read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if blob != expected:
        raise ValueError(f"source identity mismatch: {blob} != {expected}")
    tree = ast.parse(raw, filename=str(path))
    # Remove only an unused import for the INT/UINT paths. No production
    # function body is changed. Calls to ConfigParser would fail explicitly.
    removed = [n for n in tree.body if isinstance(n, ast.ImportFrom)
               and n.module == "openc3.config.config_parser"]
    assert len(removed) == 1
    tree.body = [n for n in tree.body if n not in removed]
    ns = {}
    exec(compile(tree, str(path), "exec"), ns)
    return ns["Accessor"], blob, hashlib.sha256(raw).hexdigest()


def cases():
    rng = random.Random(2601126)
    rows = []
    def add(dtype, label, value, expected, group, array=False):
        rows.append(dict(id=f"{dtype}/{label}", dtype=dtype, value=value,
                         expected=expected, group=group, array=array))
    for dtype, lo, hi in (("INT", -(2**63), 2**63-1), ("UINT", 0, 2**64-1)):
        controls = [0, 1, 42, 2**53-1, 2**53, 2**53+2]
        if dtype == "INT":
            controls += [-1, -(2**53), -(2**63)]
        large = [2**53+1, 2**60+1, hi, hi-1]
        if dtype == "INT":
            large += [-(2**53+1), lo+1]
        large += [rng.randrange(lo, hi+1) for _ in range(64)]
        for group, vals in (("exact-controls", controls), ("precision-probes", large)):
            for i, v in enumerate(vals):
                for label, x in (("int", v), ("decimal", str(v)),
                                 ("padded", ("-" if v<0 else "")+"000"+str(abs(v)))):
                    add(dtype, f"{group}/{i}/{label}", x, v, group)
            for label, x in (("array", vals), ("array-decimal", list(map(str, vals))),
                             ("literal-array", repr(vals)), ("literal-string-array", repr(list(map(str, vals))))):
                add(dtype, f"{group}/{label}", x, vals, group, True)
        for i, (v, e) in enumerate([(3.7,3),(-3.7,-3),("3.7",3),("-3.7",-3),
                                     ("1e3",1000),(True,1),(False,0),("010",10)]):
            add(dtype,f"compat/{i}",v,e,"compat-controls")
            add(dtype,f"compat-array/{i}",[v],[e],"compat-controls",True)
        for i,v in enumerate(["0x10","0b10","invalid"]):
            add(dtype,f"reject/{i}",v,"ValueError","reject-controls")
            add(dtype,f"reject-array/{i}",[v],"ValueError","reject-controls",True)
    assert len({x["id"] for x in rows}) == len(rows)
    return rows


def evaluate(accessor, case):
    item = SimpleNamespace(data_type=case["dtype"], array_size=64 if case["array"] else None)
    try:
        value = accessor.convert_to_type(case["value"], item)
        observed = {"value": value}
        correct_type = (type(value) is list and all(type(x) is int for x in value)
                        and len(value)==len(case["expected"])) if case["array"] else type(value) is int
        structural = correct_type and case["group"] != "reject-controls"
        exact = structural and value == case["expected"]
    except Exception as e:
        observed = {"error": type(e).__name__}
        structural = exact = case["group"] == "reject-controls" and type(e).__name__ == case["expected"]
    return dict(id=case["id"], group=case["group"], observed=observed,
                structural=structural, exact=exact)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("before"); p.add_argument("after"); p.add_argument("output")
    a = p.parse_args()
    cohort = cases()
    report = {"scope": "exact-source INT/UINT conversion only; known-defect retrospective calibration",
              "python": platform.python_version(), "cohort": cohort, "arms": {}}
    for arm, path in (("before",a.before),("after",a.after)):
        accessor, blob, sha256 = load(path, PINS[arm])
        rows = [evaluate(accessor,c) for c in cohort]
        groups = {}
        for group in sorted({r["group"] for r in rows}):
            g = [r for r in rows if r["group"]==group]
            groups[group] = dict(total=len(g), structural=sum(r["structural"] for r in g), exact=sum(r["exact"] for r in g))
        report["arms"][arm] = dict(blob=blob, sha256=sha256, groups=groups,
                                  total=len(rows), structural=sum(r["structural"] for r in rows),
                                  exact=sum(r["exact"] for r in rows), rows=rows)
    Path(a.output).write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:{x:y for x,y in v.items() if x!="rows"} for k,v in report["arms"].items()},indent=2))
    # Fail closed; no success by absence of observations.
    before, after = report["arms"]["before"], report["arms"]["after"]
    assert before["structural"] == len(cohort) and before["exact"] < len(cohort)
    assert after["exact"] == len(cohort)
    assert all(v["total"]==v["exact"] for k,v in before["groups"].items() if k.endswith("controls"))

if __name__ == "__main__":
    main()
