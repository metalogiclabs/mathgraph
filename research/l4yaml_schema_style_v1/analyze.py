#!/usr/bin/env python3
"""Independent original-RED baseline audit, not a repair or a universal YAML theorem."""
import argparse, hashlib, json
from pathlib import Path
import yaml
from ruamel.yaml import YAML

ap=argparse.ArgumentParser()
ap.add_argument("--lean-log",type=Path,required=True)
ap.add_argument("--out",type=Path,required=True)
ap.add_argument("--expect",choices=["original-red","fixed-green"],required=True)
a=ap.parse_args()
raw=a.lean_log.read_text()
checks={}; dumps={}
for line in raw.splitlines():
    if line.startswith("CHECK:"):
        key,sep,v=line[len("CHECK:"):].partition("=")
        assert sep and key not in checks and v in ("true","false"),line
        checks[key]=(v=="true")
    if line.startswith("DUMP:"):
        key,sep,v=line[len("DUMP:"):].partition("=")
        assert sep and key not in dumps,line
        dumps[key]=v.replace("\\n","\n")

broken=[
    "quoted_42_string","quoted_true_string","quoted_true_not_bool",
    "quoted_null_string_option","quoted_null_struct","distinct_dump_option_values",
    "round_trip_some_null",
]
positive=["plain_null_option","plain_true_bool","plain_42_nat","ordinary_string"]
assert set(checks)==set(broken+positive),checks
assert set(dumps)=={"true","none","qNone","qStringNull"},dumps
assert all(checks[k] for k in positive),checks

p12=YAML(typ="safe")
p12.version=(1,2)
consumer={}
for k,text in dumps.items():
    consumer[k]={"yaml12":p12.load(text),"pyyaml":yaml.safe_load(text),"source":text}
assert p12.load('"null"')=='null' and yaml.safe_load('"null"')=='null'
assert p12.load('null') is None and yaml.safe_load('null') is None
assert p12.load('"true"')=='true' and yaml.safe_load('"true"')=='true'
assert p12.load('true') is True and yaml.safe_load('true') is True

independent={
"bool_true_is_bool_in_both":all(consumer["true"][p] is True for p in ("yaml12","pyyaml")),
"none_is_null_in_both":all(consumer["none"][p] is None for p in ("yaml12","pyyaml")),
"qNone_is_null_in_both":all(consumer["qNone"][p]=={"x":None} for p in ("yaml12","pyyaml")),
"qStringNull_is_string_in_both":all(consumer["qStringNull"][p]=={"x":"null"} for p in ("yaml12","pyyaml")),
}
failures=[k for k,v in checks.items() if not v]+[k for k,v in independent.items() if not v]
if a.expect=="original-red":
    expected=set(broken+["bool_true_is_bool_in_both","none_is_null_in_both","qNone_is_null_in_both"])
    assert set(failures)==expected, {"actual":failures,"expected":sorted(expected)}
else: assert not failures,failures

result={
"protocol":"L4YAML_STYLE_RED_V1",
"upstream":"nasa-jpl/L4YAML@fdef03caf19e8862792034793da11020b39d6110",
"verifier":"Original Lean parseAs/toYaml/Dump + ruamel.yaml explicit YAML 1.2 + PyYAML common subset",
"native_correctness_checks":checks,
"external_consumer_semantics":consumer,
"independent_checks":independent,
"known_original_failures":sorted(failures),
"source_modified":False,
"lean_stdout_sha256":hashlib.sha256(a.lean_log.read_bytes()).hexdigest(),
"status":"WARRANTED_BOUNDED_ORIGINAL_RED" if a.expect=="original-red" else "WARRANTED_BOUNDED_FIXED_GREEN",
"bounds":"Narrow scalar cases only; PyYAML is not general YAML 1.2 authority. No fix or universal law claimed.",
}
a.out.parent.mkdir(parents=True,exist_ok=True)
a.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
print("SOURCE_NATIVE_RESULTS",json.dumps(checks,sort_keys=True))
print("EXTERNAL_CONSUMER_RESULTS",json.dumps(independent,sort_keys=True))
print("EXPECTED_ORIGINAL_FAILURES",sorted(failures))
print(result["status"])
