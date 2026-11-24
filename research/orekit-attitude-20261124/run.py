#!/usr/bin/env python3
"""Pin Orekit, run author controls and independent probes, repair, withdraw.

Generated outputs belong in the Actions artifact, never in the source repository.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

SOURCE = "48d3dad9619f7c5627f89c80878b3c1b2e1bd257"
HIP = "5.0-20261122.181226-3"
HERE = Path(__file__).resolve().parent
ROOT = Path.cwd()
OUT = ROOT / "orekit-evidence"
REPO = ROOT / "orekit-native"
OUT.mkdir(exist_ok=True)

def command(args, cwd=ROOT, name=None):
    if name:
        with (OUT / (name + ".log")).open("w") as log:
            result = subprocess.run(args, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
        print(name, "exit", result.returncode, flush=True)
        return result.returncode
    subprocess.run(args, cwd=cwd, check=True)

command(["git", "clone", "--no-checkout", "--filter=blob:none", "https://github.com/CS-SI/Orekit.git", str(REPO)])
command(["git", "checkout", "--detach", SOURCE], REPO)
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip() == SOURCE
settings = OUT / "maven-settings.xml"
settings.write_text('''<settings><profiles><profile><id>orekit-snapshots</id>
<activation><activeByDefault>true</activeByDefault></activation><repositories>
<repository><id>orekit-snapshots</id><url>https://packages.orekit.org/repository/maven-snapshots/</url>
<releases><enabled>false</enabled></releases><snapshots><enabled>true</enabled></snapshots>
</repository></repositories></profile></profiles></settings>''')
mvn = ["mvn", "-B", "-s", str(settings), "-Dorekit.hipparchus.version=" + HIP]
authors = "AttitudeTypeTest,AEMParserTest,AemWriterTest,APMParserTest,ApmWriterTest,StreamingAemWriterTest,AttitudeWriterTest,EulerTest"
summary = {"source": SOURCE, "hipparchus_timestamp": HIP, "phases": {}}

def phase(name, selector):
    for pattern in ["target/surefire-reports", "target/mathgraph-direct.csv", "target/mathgraph-parsed.csv"]:
        p = REPO / pattern
        if p.is_dir(): shutil.rmtree(p)
        elif p.exists(): p.unlink()
    status = command(mvn + ["-Dtest=" + selector, "test"], REPO, name)
    reports = list((REPO / "target/surefire-reports").glob("TEST-*.xml"))
    assert reports, f"{name}: no native JUnit reports; inspect the log"
    destination = OUT / name
    destination.mkdir()
    stats = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "exit": status}
    for p in reports:
        tree = ET.parse(p).getroot()
        for k in ["tests", "failures", "errors", "skipped"]: stats[k] += int(tree.attrib.get(k, "0"))
        shutil.copy2(p, destination / p.name)
    for p in (REPO / "target").glob("mathgraph-*.csv"):
        rows = p.read_text().splitlines()
        discrepancies = sum(float(line.split(",")[5]) > 3e-13 for line in rows)
        stats[p.stem] = {"cases": len(rows), "discrepancies": discrepancies}
        shutil.copy2(p, destination / p.name)
    summary["phases"][name] = stats
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(name, json.dumps(stats), flush=True)
    return stats

assert phase("author-baseline", authors)["exit"] == 0
probe = REPO / "src/test/java/org/orekit/files/ccsds/ndm/adm/aem/MathGraphAttitudeAuditTest.java"
shutil.copy2(HERE / probe.name, probe)
original = phase("upstream-probe", "MathGraphAttitudeAuditTest")
assert original["exit"] != 0 and original["tests"] == 5

paths = ["src/main/java/org/orekit/files/ccsds/ndm/adm/aem/AemMetadata.java",
         "src/main/java/org/orekit/files/ccsds/ndm/adm/AttitudeType.java",
         "src/main/java/org/orekit/files/ccsds/ndm/adm/AttitudeEndpoints.java"]
originals = {path: (REPO / path).read_bytes() for path in paths}
metadata = REPO / paths[0]
text = metadata.read_text()
old = "return rateFrameIsA() ^ endpoints.getFrameA().asSpacecraftBodyFrame().isPresent();"
assert text.count(old) == 1
text = text.replace(old, """if (angvelFrame != null) {
            return angvelFrame.asSpacecraftBodyFrame().isPresent();
        }
        return rateFrameIsA() ^ endpoints.getFrameA().asSpacecraftBodyFrame().isEmpty();""")
metadata.write_text(text)
attitude = REPO / paths[1]
text = attitude.read_text()
for name in ["QUATERNION_ANGVEL", "EULER_ANGLE_ANGVEL"]:
    for operation in ["metadataRate", "orekitRate"]:
        old = name + "." + operation + "(isSpacecraftBodyRate,"
        assert text.count(old) == 1
        text = text.replace(old, name + "." + operation + "(isSpacecraftBodyRate == isExternal2SpacecraftBody,")
attitude.write_text(text)
endpoints = REPO / paths[2]
text = endpoints.read_text()
assert text.count("a2b.equals(other.a2b)") == 1
endpoints.write_text(text.replace("a2b.equals(other.a2b)", "isA2b() == other.isA2b()"))
with (OUT / "diagnostic-repair.patch").open("w") as f:
    subprocess.run(["git", "diff", "--", *paths], cwd=REPO, stdout=f, check=True)
assert phase("diagnostic-repair-probe", "MathGraphAttitudeAuditTest")["exit"] == 0
assert phase("diagnostic-repair-authors", authors)["exit"] == 0
for path, content in originals.items(): (REPO / path).write_bytes(content)
assert command(["git", "diff", "--exit-code", "--", "src/main", "pom.xml"], REPO, "source-restored") == 0
withdrawal = phase("withdrawal-probe", "MathGraphAttitudeAuditTest")
assert {k:v for k,v in original.items() if k != "exit"} == {k:v for k,v in withdrawal.items() if k != "exit"}

dependencies = []
for p in (Path.home() / ".m2/repository/org/hipparchus").rglob("*.jar"):
    if HIP in p.name or p.name.endswith("5.0-SNAPSHOT.jar"):
        dependencies.append({"path": str(p.relative_to(Path.home() / ".m2/repository")),
                             "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size})
assert dependencies
summary["hipparchus_jars"] = dependencies
summary["source_restored"] = True
summary["boundary"] = "Bounded offline synthetic and author-fixture audit; scoped author tests only; no whole-project qualification or operational inference. Diagnostic patch covers only ANGVEL_FRAME equal to endpoint A or B."
(OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
command(["java", "-version"], name="java-version")
command(["mvn", "-version"], name="maven-version")
shutil.copy2(probe, OUT / probe.name)
shutil.copy2(HERE / "run.py", OUT / "run.py")
command(["git", "status", "--short"], REPO, "final-git-status")
manifest = {}
for p in sorted(OUT.rglob("*")):
    if p.is_file(): manifest[str(p.relative_to(OUT))] = hashlib.sha256(p.read_bytes()).hexdigest()
(OUT / "SHA256SUMS.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("QUALIFIED bounded counterexamples and repair/withdrawal controls", flush=True)
