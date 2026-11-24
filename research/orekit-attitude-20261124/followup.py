#!/usr/bin/env python3
"""Separate development regression, released behavior, metadata and direction defects.

Only stated finite matrices and native JUnit results are accepted. No upstream writes.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = Path.cwd()
OUT = ROOT / "orekit-followup-evidence"
OUT.mkdir()
BASELINES = {
    "develop": {"sha": "48d3dad9619f7c5627f89c80878b3c1b2e1bd257", "hip": "5.0-20261122.181226-3"},
    "release": {"sha": "cf611eab6b30a1fc2ccc7e6f2d1991e029b30568", "hip": "4.0.3"},
}
TEST_PATH = "src/test/java/org/orekit/files/ccsds/ndm/adm/aem/MathGraphAttitudeAuditTest.java"
META_PATH = "src/main/java/org/orekit/files/ccsds/ndm/adm/aem/AemMetadata.java"
ATT_PATH = "src/main/java/org/orekit/files/ccsds/ndm/adm/AttitudeType.java"
PROBES = "MathGraphAttitudeAuditTest#independentOrientationAndDerivativeControls+directAngularVelocityFrames+parsedAemAngularVelocityFrames+originalAuthorFixtureBodyRate+generatedAngularVelocityFrames"
AUTHOR_TESTS = "org.orekit.files.ccsds.**.*Test,!*MathGraphAttitudeAuditTest"
summary = {"baselines": BASELINES, "phases": {}, "boundary": "Pinned native source; all original CCSDS tests, five rate/orientation probe methods, selected A/B rate frames. No whole-project or arbitrary third-frame qualification. Endpoint compatibility excluded from this follow-up."}

def save_summary():
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

def cmd(args, cwd=ROOT, log=None):
    if log:
        with (OUT / (log + ".log")).open("w") as f:
            result = subprocess.run(args, cwd=cwd, stdout=f, stderr=subprocess.STDOUT)
        return result.returncode
    subprocess.run(args, cwd=cwd, check=True)

def phase(label, repo, mvn, selector):
    name = repo.name + "-" + label
    destination = OUT / name
    destination.mkdir()
    reports = repo / "target/surefire-reports"
    if reports.exists(): shutil.rmtree(reports)
    for p in (repo / "target").glob("mathgraph-*.csv"): p.unlink()
    status = cmd(mvn + ["-Dtest=" + selector, "test"], repo, name)
    xml_files = list(reports.glob("TEST-*.xml"))
    assert xml_files, f"No native reports for {name}; inspect build log"
    result = {"exit": status, "tests": 0, "failures": 0, "errors": 0, "skipped": 0, "methods": {}}
    for p in xml_files:
        root = ET.parse(p).getroot()
        for k in ["tests", "failures", "errors", "skipped"]: result[k] += int(root.attrib.get(k, 0))
        if p.name.endswith("MathGraphAttitudeAuditTest.xml"):
            for case in root.findall("testcase"):
                result["methods"][case.attrib["name"]] = "FAIL" if case.find("failure") is not None or case.find("error") is not None else "PASS"
        shutil.copy2(p, destination / p.name)
    for p in (repo / "target").glob("mathgraph-*.csv"):
        rows = [r.split(",") for r in p.read_text().splitlines()]
        by_frame = {}
        for row in rows:
            key = "forward=" + row[2] + ",body=" + row[3]
            cell = by_frame.setdefault(key, {"cases": 0, "discrepancies": 0})
            cell["cases"] += 1
            cell["discrepancies"] += float(row[5]) > 3e-13
        result[p.stem] = {"cases": len(rows), "discrepancies": sum(float(r[5]) > 3e-13 for r in rows), "by_frame": by_frame}
        shutil.copy2(p, destination / p.name)
    summary["phases"][name] = result
    save_summary()
    print(name, json.dumps(result), flush=True)
    return result

def patch_metadata(repo, released):
    path = repo / META_PATH
    text = path.read_text()
    old = ("return rateFrameIsA() ^ endpoints.getFrameA().asSpacecraftBodyFrame() == null;" if released else
           "return rateFrameIsA() ^ endpoints.getFrameA().asSpacecraftBodyFrame().isPresent();")
    assert text.count(old) == 1
    check = "angvelFrame.asSpacecraftBodyFrame() != null" if released else "angvelFrame.asSpacecraftBodyFrame().isPresent()"
    fallback = ("rateFrameIsA() ^ endpoints.getFrameA().asSpacecraftBodyFrame() == null" if released else
                "rateFrameIsA() ^ endpoints.getFrameA().asSpacecraftBodyFrame().isEmpty()")
    text = text.replace(old, "if (angvelFrame != null) {\n            return " + check + ";\n        }\n        return " + fallback + ";")
    path.write_text(text)

def patch_direction(repo):
    path = repo / ATT_PATH
    text = path.read_text()
    for name in ["QUATERNION_ANGVEL", "EULER_ANGLE_ANGVEL"]:
        for operation in ["metadataRate", "orekitRate"]:
            old = name + "." + operation + "(isSpacecraftBodyRate,"
            assert text.count(old) == 1
            text = text.replace(old, name + "." + operation + "(isSpacecraftBodyRate == isExternal2SpacecraftBody,")
    path.write_text(text)

settings = OUT / "maven-settings.xml"
settings.write_text('''<settings><profiles><profile><id>orekit-snapshots</id>
<activation><activeByDefault>true</activeByDefault></activation><repositories>
<repository><id>orekit-snapshots</id><url>https://packages.orekit.org/repository/maven-snapshots/</url>
<releases><enabled>false</enabled></releases><snapshots><enabled>true</enabled></snapshots>
</repository></repositories></profile></profiles></settings>''')

for baseline, config in BASELINES.items():
    repo = ROOT / baseline
    cmd(["git", "init", str(repo)])
    cmd(["git", "remote", "add", "origin", "https://github.com/CS-SI/Orekit.git"], repo)
    cmd(["git", "fetch", "--depth=1", "origin", config["sha"]], repo)
    cmd(["git", "checkout", "--detach", config["sha"]], repo)
    mvn = ["mvn", "-B", "-s", str(settings), "-Dorekit.hipparchus.version=" + config["hip"]]
    originals = {p: (repo / p).read_bytes() for p in [META_PATH, ATT_PATH]}
    assert phase("all-ccsds-authors-before", repo, mvn, AUTHOR_TESTS)["exit"] == 0
    shutil.copy2(HERE / "MathGraphAttitudeAuditTest.java", repo / TEST_PATH)
    before = phase("before", repo, mvn, PROBES)
    assert before["tests"] == 5 and before["exit"] != 0
    assert before["methods"]["independentOrientationAndDerivativeControls"] == "PASS"
    if baseline == "develop":
        p = repo / META_PATH
        text = p.read_text()
        old = "return rateFrameIsA() ^ endpoints.getFrameA().asSpacecraftBodyFrame().isPresent();"
        assert text.count(old) == 1
        p.write_text(text.replace(old, old.replace(".isPresent()", ".isEmpty()")))
        single = phase("one-line-regression-repair", repo, mvn, PROBES)
        assert single["methods"]["originalAuthorFixtureBodyRate"] == "PASS"
        (repo / META_PATH).write_bytes(originals[META_PATH])
    else:
        assert before["methods"]["originalAuthorFixtureBodyRate"] == "PASS"
        patch_metadata(repo, True)
        metadata_only = phase("metadata-only", repo, mvn, PROBES)
        assert metadata_only["mathgraph-parsed"]["discrepancies"] > 0
        (repo / META_PATH).write_bytes(originals[META_PATH])
        patch_direction(repo)
        direction_only = phase("direction-only", repo, mvn, PROBES)
        assert direction_only["mathgraph-parsed"]["discrepancies"] > 0
        (repo / ATT_PATH).write_bytes(originals[ATT_PATH])
    patch_metadata(repo, baseline == "release")
    patch_direction(repo)
    with (OUT / (baseline + "-diagnostic-rate-repair.patch")).open("w") as f:
        subprocess.run(["git", "diff", "--", META_PATH, ATT_PATH], cwd=repo, stdout=f, check=True)
    assert phase("combined-rate-repair", repo, mvn, PROBES)["exit"] == 0
    assert phase("all-ccsds-authors-after", repo, mvn, AUTHOR_TESTS)["exit"] == 0
    for p, data in originals.items(): (repo / p).write_bytes(data)
    assert cmd(["git", "diff", "--exit-code", "--", "src/main", "pom.xml"], repo, baseline + "-restored") == 0
    after = phase("withdrawal", repo, mvn, PROBES)
    assert before == after
    config["production_bytes_restored"] = True

summary["dependency_hashes"] = {}
for p in (Path.home() / ".m2/repository/org/hipparchus").rglob("*.jar"):
    if "5.0-20261122.181226-3" in p.name or "4.0.3" in p.name:
        summary["dependency_hashes"][str(p.relative_to(Path.home() / ".m2/repository"))] = hashlib.sha256(p.read_bytes()).hexdigest()
save_summary()
cmd(["java", "-version"], log="java-version")
cmd(["mvn", "-version"], log="maven-version")
for name in ["followup.py", "MathGraphAttitudeAuditTest.java"]: shutil.copy2(HERE / name, OUT / name)
manifest = {str(p.relative_to(OUT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.rglob("*")) if p.is_file()}
(OUT / "SHA256SUMS.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("QUALIFIED finite counterexamples, isolated mechanisms, release/develop, and withdrawals", flush=True)
