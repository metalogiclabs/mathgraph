#!/usr/bin/env python3
"""Paired native regression on the pinned Yamcs core reactor; synthetic fixtures only."""
import collections
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPSTREAM = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
PARENT = Path(sys.argv[3]).resolve()
JDK = os.environ["QUALIFY_JAVA"]
PIN = "4af5abd2b5d8535f77e902de717c77d657f0093e"
MODULES = ["yamcs-api", "yamcs-client", "yamcs-xtce", "yamcs-core"]
REQUIRED = ["org.yamcs.mdb.UnsignedComparisonTest", "org.yamcs.mdb.DataEncodingUtilsTest",
            "org.yamcs.mdb.DataTypeProcessorTest", "org.yamcs.xtce.IntegerDataTypeTest"]
PROBE = "org.yamcs.mdb.MathGraphNumericalProbeTest"
OUT.mkdir(parents=True, exist_ok=True)

def git(*args):
    return subprocess.check_output(["git", *args], cwd=UPSTREAM, text=True)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def stage(label):
    directory = OUT / label
    directory.mkdir()
    for module in MODULES:
        path = UPSTREAM / module / "target/surefire-reports"
        if path.exists():
            shutil.rmtree(path)
    command = ["mvn", "-B", "--no-transfer-progress", "-pl", "yamcs-core", "-am",
               "-Dmaven.test.failure.ignore=true", "-Dmathgraph.strict=true",
               "-Dmathgraph.out=" + str(directory), "test"]
    (directory / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    with (directory / "maven.log").open("w") as f:
        result = subprocess.run(command, cwd=UPSTREAM, stdout=f, stderr=subprocess.STDOUT)
    cases, suites, dependency_hashes = [], [], {}
    for module in MODULES:
        reports = UPSTREAM / module / "target/surefire-reports"
        destination = directory / module
        destination.mkdir()
        for p in sorted(reports.glob("*")):
            if p.is_file() and p.suffix in [".xml", ".txt", ".dump", ".dumpstream"]:
                shutil.copy2(p, destination / p.name)
        for p in sorted(reports.glob("TEST-*.xml")):
            e = ET.parse(p).getroot()
            suites.append({"module": module, **{k: e.get(k) for k in ["name", "tests", "failures", "errors", "skipped"]}})
            for t in e.findall("testcase"):
                failure = t.find("failure")
                error = t.find("error")
                skipped = t.find("skipped")
                status = "failure" if failure is not None else "error" if error is not None else "skipped" if skipped is not None else "passed"
                cases.append({"module": module, "class": t.get("classname"), "name": t.get("name"), "status": status})
            for prop in e.findall("properties/property"):
                if prop.get("name") == "java.class.path":
                    for entry in prop.get("value", "").split(os.pathsep):
                        jar = Path(entry)
                        if jar.is_file() and jar.suffix == ".jar":
                            dependency_hashes[str(jar).split("/.m2/repository/")[-1]] = sha(jar)
    counts = dict(collections.Counter(x["status"] for x in cases))
    summary = {"exit": result.returncode, "jdk": JDK, "case_count": len(cases), "counts": counts, "suites": suites}
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (directory / "case-inventory.json").write_text(json.dumps(cases, indent=2) + "\n")
    (directory / "dependency-sha256.json").write_text(json.dumps(dependency_hashes, indent=2) + "\n")
    print(label, json.dumps({k: summary[k] for k in ["exit", "jdk", "case_count", "counts"]}), flush=True)
    for s in suites:
        if s["name"] in REQUIRED or s["name"] == PROBE:
            print("REQUIRED_SUITE", label, json.dumps(s), flush=True)
    return summary, cases

assert git("rev-parse", "HEAD").strip() == PIN
assert git("status", "--porcelain").strip() == ""
(OUT / "source.txt").write_text(PIN + "\n")
(OUT / "parent-native-run.txt").write_text("45337311923 / 88c85b3d21ede2414096b8d78626c4e105595076\n")
(OUT / "boundary.txt").write_text(
    "Original default Maven tests in yamcs-core and its required reactor modules; JDK " + JDK +
    ". Original tests may use synthetic localhost fixtures. No production service, live telemetry, external command system or spacecraft access. "
    "maven.test.failure.ignore only continues discovery; every raw JUnit failure and error prevents qualification. "
    "The separate tests integration module, web tests, Javadoc and operating-system matrix are outside this run.\n")
for command in [["java", "-version"], ["mvn", "-version"]]:
    p = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (OUT / (command[0] + "-version.txt")).write_text(p.stdout)
tracked = git("ls-files").splitlines()
relevant = [p for p in tracked if p.endswith("pom.xml") or "/src/main/" in p or "/src/test/" in p]
(OUT / "source-hashes.json").write_text(json.dumps({p: sha(UPSTREAM / p) for p in relevant if (UPSTREAM / p).is_file()}, indent=2) + "\n")
parent_manifest = json.loads((PARENT / "manifest.json").read_text())
for name, digest in parent_manifest.items():
    assert sha(PARENT / name) == digest, name
assert (PARENT / "source.txt").read_text().strip() == PIN
assert sha(ROOT / "MathGraphNumericalProbeTest.java") == sha(PARENT / "MathGraphNumericalProbeTest.java")
(OUT / "parent-manifest.json").write_text(json.dumps(parent_manifest, indent=2) + "\n")
before, original_cases = stage("baseline")
shutil.copy2(PARENT / "candidate.patch", OUT / "candidate.patch")
subprocess.run(["git", "apply", "--check", str(PARENT / "candidate.patch")], cwd=UPSTREAM, check=True)
subprocess.run(["git", "apply", str(PARENT / "candidate.patch")], cwd=UPSTREAM, check=True)
assert git("diff", "--", "yamcs-core/src/main/java/org/yamcs/mdb/DataTypeProcessor.java",
           "yamcs-core/src/main/java/org/yamcs/parameter/UInt64Value.java") == (PARENT / "candidate.patch").read_text()
probe_path = UPSTREAM / "yamcs-core/src/test/java/org/yamcs/mdb/MathGraphNumericalProbeTest.java"
shutil.copy2(ROOT / "MathGraphNumericalProbeTest.java", probe_path)
(OUT / "probe-source-sha256.txt").write_text(sha(probe_path) + "\n")
after, repaired_cases = stage("repair")
subprocess.run(["git", "apply", "-R", str(PARENT / "candidate.patch")], cwd=UPSTREAM, check=True)
probe_path.unlink()
assert git("diff", "--exit-code") == ""
(OUT / "post-test-status.txt").write_text(git("status", "--porcelain"))
(OUT / "upstream-restored.txt").write_text(git("rev-parse", "HEAD"))
def key(c):
    return c["module"], c["class"], c["name"], c["status"]
repaired_original = [c for c in repaired_cases if c["class"] != PROBE]
inventory_equal = collections.Counter(map(key, original_cases)) == collections.Counter(map(key, repaired_original))
present = {s["name"]: s for s in before["suites"]}
required_present = all(n in present and int(present[n]["tests"]) > 0 and int(present[n]["skipped"]) == 0 for n in REQUIRED)
probes = [c for c in repaired_cases if c["class"] == PROBE]
green = all(s["exit"] == 0 and s["case_count"] > 9 and s["counts"].get("failure", 0) == 0 and s["counts"].get("error", 0) == 0 for s in [before, after])
matrices = {}
for name in ["integers.tsv", "floats.tsv", "to-long.tsv", "consumer.tsv"]:
    path = OUT / "repair" / name
    if path.exists():
        rows = list(csv.DictReader(path.open(), delimiter="\t"))
        matrices[name] = {"cases": len(rows), "mismatches": sum(r["match"] != "true" for r in rows)}
qualifies = green and inventory_equal and required_present and len(probes) == 4 and all(c["status"] == "passed" for c in probes) and len(matrices) == 4 and all(x["mismatches"] == 0 for x in matrices.values())
result = {"status": "QUALIFIED_BOUNDED_SELECTED_REACTOR" if qualifies else "UNKNOWN_REQUIRES_FAILURE_ANALYSIS",
          "jdk": JDK, "source": PIN, "baseline": {k: before[k] for k in ["exit", "case_count", "counts"]},
          "repair": {k: after[k] for k in ["exit", "case_count", "counts"]},
          "original_case_status_multisets_equal": inventory_equal, "required_regressions_present": required_present,
          "new_regression_cases": len(probes), "matrices": matrices}
(OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
manifest = {str(p.relative_to(OUT)): sha(p) for p in sorted(OUT.rglob("*")) if p.is_file()}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(result, indent=2), flush=True)
sys.exit(0 if qualifies else 1)
