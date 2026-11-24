#!/usr/bin/env python3
"""Reproduce bounded Yamcs conversion contracts; never starts a Yamcs server."""
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPSTREAM = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
PIN = "4af5abd2b5d8535f77e902de717c77d657f0093e"
MAIN = Path("yamcs-core/src/main/java/org/yamcs/mdb/DataTypeProcessor.java")
LONG = Path("yamcs-core/src/main/java/org/yamcs/parameter/UInt64Value.java")
TEST = Path("yamcs-core/src/test/java/org/yamcs/mdb/MathGraphNumericalProbeTest.java")
ORIGINAL = "DataTypeProcessorTest,IntegerDataTypeTest,DataEncodingUtilsTest"

def git(*args):
    return subprocess.check_output(["git", *args], cwd=UPSTREAM, text=True)

def run(label, extra, expected, suites=None):
    stage = OUT / label
    stage.mkdir()
    command = ["mvn", "-B", "-pl", "yamcs-core", "-am",
               "-Dsurefire.failIfNoSpecifiedTests=false", *extra, "test"]
    (stage / "command.json").write_text(json.dumps(command, indent=2))
    with (stage / "maven.log").open("w") as log:
        p = subprocess.run(command, cwd=UPSTREAM, stdout=log, stderr=subprocess.STDOUT)
    summaries = []
    failed = []
    for module in ["yamcs-xtce", "yamcs-core"]:
        for report in (UPSTREAM / module / "target/surefire-reports").glob("TEST-*.xml"):
            if suites and not any(report.name.endswith(s + ".xml") for s in suites):
                continue
            shutil.copy2(report, stage / report.name)
            e = ET.parse(report).getroot()
            summaries.append({k: e.get(k) for k in ["name", "tests", "failures", "errors", "skipped"]})
            for t in e.findall("testcase"):
                if t.find("failure") is not None:
                    failed.append(t.get("name"))
    (stage / "summary.json").write_text(json.dumps({"exit": p.returncode, "suites": summaries}, indent=2))
    assert summaries, (label, "no JUnit reports; harness/environment failure")
    assert all(int(s["errors"]) == 0 for s in summaries), (label, summaries)
    if expected == "pass":
        assert p.returncode == 0 and all(int(s["failures"]) == 0 for s in summaries), (label, p.returncode, summaries)
    else:
        assert p.returncode == 1, (label, p.returncode)
        assert set(failed) == {"integerConversionMatrix", "floatingConversionMatrix", "unsignedLongDocumentedContract"}, (label, failed)
    print(label, json.dumps({"exit": p.returncode, "suites": summaries}), flush=True)
    return stage

def replace(path, old, new):
    p = UPSTREAM / path
    s = p.read_text()
    assert s.count(old) == 1, (path, old)
    p.write_text(s.replace(old, new))

assert git("rev-parse", "HEAD").strip() == PIN
assert git("status", "--porcelain").strip() == ""
(OUT / "source.txt").write_text(PIN + "\n")
(OUT / "source-hashes.json").write_text(json.dumps({str(p): hashlib.sha256((UPSTREAM / p).read_bytes()).hexdigest() for p in [MAIN, LONG, Path("pom.xml")]}, indent=2))
for tool in [["java", "-version"], ["mvn", "-version"], ["git", "--version"]]:
    p = subprocess.run(tool, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (OUT / (tool[0] + "-version.txt")).write_text(p.stdout)
shutil.copy2(ROOT / "MathGraphNumericalProbeTest.java", OUT)
baseline = run("author-baseline", ["-Dtest=" + ORIGINAL], "pass", ORIGINAL.split(","))
shutil.copy2(ROOT / "MathGraphNumericalProbeTest.java", UPSTREAM / TEST)
before = run("before", ["-Dtest=MathGraphNumericalProbeTest", "-Dmathgraph.strict=true", "-Dmathgraph.out=" + str(OUT / "before")], "fail", ["MathGraphNumericalProbeTest"])

replace(MAIN, "v.getUint32Value() & Long.MAX_VALUE", "Integer.toUnsignedLong(v.getUint32Value())")
replace(MAIN, "int uintValue = v.getUint32Value();", "long uintValue = Integer.toUnsignedLong(v.getUint32Value());")
replace(MAIN, "unsignedSizeInBits(uintValue) - 1", "unsignedSizeInBits(uintValue) + (type.isSigned() ? 1 : 0)")
replace(MAIN, "unsignedSizeInBits(ulongValue) - 1", "unsignedSizeInBits(ulongValue) + (type.isSigned() ? 1 : 0)")
replace(LONG, "if (v < 0) {\n            return v;", "if (v >= 0) {\n            return v;")
(OUT / "candidate.patch").write_text(git("diff", "--", str(MAIN), str(LONG)))
after = run("after", ["-Dtest=" + ORIGINAL + ",MathGraphNumericalProbeTest", "-Dmathgraph.strict=true", "-Dmathgraph.out=" + str(OUT / "after")], "pass", ORIGINAL.split(",") + ["MathGraphNumericalProbeTest"])
subprocess.run(["git", "apply", "-R", str(OUT / "candidate.patch")], cwd=UPSTREAM, check=True)
withdraw = run("withdraw", ["-Dtest=MathGraphNumericalProbeTest", "-Dmathgraph.strict=true", "-Dmathgraph.out=" + str(OUT / "withdraw")], "fail", ["MathGraphNumericalProbeTest"])
for name in ["integers.tsv", "floats.tsv", "to-long.tsv"]:
    assert (before / name).read_bytes() == (withdraw / name).read_bytes(), name
assert git("diff", "--exit-code") == ""
result = {"status": "WARRANTED_BOUNDED_NATIVE_CONTRACT_DISCREPANCIES",
          "source": PIN, "boundary": "direct public Java conversion APIs; finite synthetic unit tests; no running server, operational link or safety consequence", "matrices": {}}
for name in ["integers.tsv", "floats.tsv", "to-long.tsv"]:
    result["matrices"][name] = {}
    for label in ["before", "after", "withdraw"]:
        with (OUT / label / name).open() as f:
            rows = list(csv.DictReader(f, delimiter="\t"))
        result["matrices"][name][label] = {"cases": len(rows), "mismatches": sum(r["match"] == "false" for r in rows)}
(OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
(OUT / "upstream-production-restored.txt").write_text(git("diff", "--exit-code") + git("rev-parse", "HEAD"))
hashes = {str(p.relative_to(OUT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.rglob("*")) if p.is_file()}
(OUT / "manifest.json").write_text(json.dumps(hashes, indent=2) + "\n")
print(json.dumps(result, indent=2), flush=True)
