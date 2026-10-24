"""Independent, unmodified ruamel.yaml oracle for L4YAML anchor separators.

Install the pinned wheel into sibling install/ with --no-deps before running.
This script does not execute L4YAML and makes no claim about its runtime.
"""
import datetime
import hashlib
import json
import pathlib
import platform
import sys
import warnings
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "install"))
from ruamel.yaml import YAML
from ruamel.yaml.error import ReusedAnchorWarning
import ruamel.yaml

WHEEL_SHA256 = "9c8ba9eb3e793efdf924b60d521820869d5bf0cb9c6f1b82d82de8295e290b9d"
CASES = [
    ("same-name-seq", "[&x [&x 1], *x]", [[1], 1]),
    ("same-name-seq-both-aliases", "[&x [&x 1, *x], *x]", [[1, 1], 1]),
    ("same-name-map", "a: &x {b: &x 1}\nc: *x\n", {"a": {"b": 1}, "c": 1}),
    ("same-name-map-both-aliases", "a: &x {b: &x 1, c: *x}\nd: *x\n", {"a": {"b": 1, "c": 1}, "d": 1}),
    ("sibling-rebind", "[&x 1, *x, &x 2, *x]", [1, 1, 2, 2]),
    ("nested-distinct", "[&o [&x 1], *x, *o]", [[1], 1, [1]]),
    ("noalias-same-name", "[&x [&x 1]]", [[1]]),
    ("same-name-string", "[&x [&x inner], *x]", [["inner"], "inner"]),
]

wheel = ROOT / "ruamel_yaml-0.18.17-py3-none-any.whl"
composer = ROOT / "install" / "ruamel" / "yaml" / "composer.py"
wheel_digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
assert wheel_digest == WHEEL_SHA256
assert ruamel.yaml.__version__ == "0.18.17"
with zipfile.ZipFile(wheel) as z:
    assert z.read("ruamel/yaml/composer.py") == composer.read_bytes()

receipt = {
    "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "boundary": "Native ruamel.yaml oracle only; does not execute L4YAML",
    "package": "ruamel.yaml",
    "version": ruamel.yaml.__version__,
    "python": platform.python_version(),
    "wheel_sha256": wheel_digest,
    "published_digest_url": "https://pypi.org/project/ruamel.yaml/0.18.17/#files",
    "composer_sha256": hashlib.sha256(composer.read_bytes()).hexdigest(),
    "composer_matches_wheel": True,
    "normative_sources": [
        "https://yaml.org/spec/1.2.2/#3222-anchors-and-aliases",
        "https://yaml.org/spec/1.2.2/#71-alias-nodes",
    ],
    "acyclic_cases": [],
    "graph_policy_controls": [],
}

for mode in ("safe", "rt"):
    for name, source, expected in CASES:
        parser = YAML(typ=mode, pure=True)
        parser.version = (1, 2)
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always", ReusedAnchorWarning)
            actual = parser.load(source)
        row = {
            "mode": mode,
            "name": name,
            "input": source,
            "actual": actual,
            "expected": expected,
            "agrees": actual == expected,
            "warnings": [type(w.message).__name__ for w in recorded],
        }
        receipt["acyclic_cases"].append(row)

for name, source, identity in [
    ("selfcycle", "&x [*x]", lambda v: v[0] is v),
    ("rebound-selfcycle", "[&x 0, &x [*x]]", lambda v: v[1][0] is v[1]),
]:
    parser = YAML(typ="safe", pure=True)
    parser.version = (1, 2)
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always", ReusedAnchorWarning)
        value = parser.load(source)
    receipt["graph_policy_controls"].append({
        "name": name,
        "input": source,
        "identity": identity(value),
        "warnings": [type(w.message).__name__ for w in recorded],
        "boundary": "Graph identity observation, not an acyclic JSON expected value",
    })

receipt["acyclic_passed"] = sum(r["agrees"] for r in receipt["acyclic_cases"])
receipt["acyclic_total"] = len(receipt["acyclic_cases"])
receipt["script_sha256"] = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
(ROOT / "oracle_results.json").write_text(text)
print(text)
assert receipt["acyclic_passed"] == receipt["acyclic_total"]
