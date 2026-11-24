"""Qualify the actual proposed three-file contribution, not just a probe."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "libcsp-route-review"
OUT = Path(__file__).resolve().parent
CMAKE = ROOT / "build-tools/cmake/data/bin/cmake"
CHECK = ROOT / "libcheck-installed"
SOURCE = SRC / "src/csp_rtable_cidr.c"
candidate = SOURCE.read_bytes()
original = subprocess.check_output(["git", "show", "HEAD:src/csp_rtable_cidr.c"], cwd=SRC)
new_tests = {"test_rtable_last_entry_visible", "test_rtable_full_replaces_last", "test_rtable_full_updates_existing"}
commands, results = [], {}

def cmd(args, label, env=None, allowed=(0,)):
    r = subprocess.run(list(map(str, args)), cwd=SRC, env=env, capture_output=True)
    (OUT / (label + ".stdout")).write_bytes(r.stdout)
    (OUT / (label + ".stderr")).write_bytes(r.stderr)
    commands.append({"label": label, "args": list(map(str, args)), "exit": r.returncode})
    assert r.returncode in allowed, (label, r.stderr.decode(errors="replace")[-1500:])
    return r

def xml_results(path):
    tree = ET.parse(path)
    records = {}
    for test in tree.findall(".//{*}test"):
        name = test.find("{*}id").text
        records[name] = test.attrib["result"]
    assert records, "No executed tests in XML"
    return records

try:
    for shared in ("OFF", "ON"):
        build = SRC / ("build-review-" + shared)
        env = dict(os.environ, PKG_CONFIG_PATH=str(CHECK / "lib/pkgconfig"))
        base = [CMAKE, "-S", SRC, "-B", build, "-DCSP_BUILD_SAMPLES=OFF", "-DCSP_USE_RTABLE=ON",
                "-DCMAKE_BUILD_TYPE=Debug", "-DBUILD_SHARED_LIBS=" + shared,
                "-DCMAKE_C_FLAGS=-I" + str(CHECK / "include"), "-DCMAKE_EXE_LINKER_FLAGS=-L" + str(CHECK / "lib")]
        cmd(base, "review-" + shared + "-configure", env)
        results[shared] = {}
        for stage, source_bytes in (("before", original), ("after", candidate), ("withdrawn", original)):
            SOURCE.write_bytes(source_bytes)
            label = f"review-{shared}-{stage}"
            cmd([CMAKE, "--build", build, "-j", "2", "--target", "csp_tests"], label + "-build")
            xml = OUT / (label + ".xml")
            test_env = dict(os.environ, LD_LIBRARY_PATH=str(CHECK / "lib") + ":" + str(build), CK_XML_LOG_FILE_NAME=str(xml))
            r = cmd([build / "unittests/csp_tests", "--verbose"], label + "-tests", test_env, allowed=(0,) if stage == "after" else (1,))
            records = xml_results(xml)
            existing = {k: v for k, v in records.items() if k not in new_tests}
            added = {k: v for k, v in records.items() if k in new_tests}
            assert len(existing) == 12 and all(v == "success" for v in existing.values())
            assert set(added) == new_tests
            assert all(v == ("success" if stage == "after" else "failure") for v in added.values())
            results[shared][stage] = {"existing": existing, "added": added, "exit": r.returncode,
                                     "binary_sha256": hashlib.sha256((build / "unittests/csp_tests").read_bytes()).hexdigest()}
        # Default routing-disabled compatibility: no added routing references or tests.
        SOURCE.write_bytes(candidate)
        off_build = SRC / ("build-review-disabled-" + shared)
        off_args = [str(x) for x in base]
        off_args[off_args.index(str(build))] = str(off_build)
        off_args[off_args.index("-DCSP_USE_RTABLE=ON")] = "-DCSP_USE_RTABLE=OFF"
        label = "review-disabled-" + shared
        cmd(off_args, label + "-configure", env)
        cmd([CMAKE, "--build", off_build, "-j", "2", "--target", "csp_tests"], label + "-build")
        xml = OUT / (label + ".xml")
        cmd([off_build / "unittests/csp_tests", "--verbose"], label + "-tests",
            dict(os.environ, LD_LIBRARY_PATH=str(CHECK / "lib") + ":" + str(off_build), CK_XML_LOG_FILE_NAME=str(xml)))
        records = xml_results(xml)
        assert len(records) == 12 and all(v == "success" for v in records.values()) and not (set(records) & new_tests)
        results[shared]["routing_disabled"] = records
finally:
    SOURCE.write_bytes(candidate)

patch = subprocess.check_output(["git", "diff", "--", "src/csp_rtable_cidr.c", "unittests/route.c", ".github/workflows/unit-test.yml"], cwd=SRC)
(OUT / "upstream-review.patch").write_bytes(patch)
(OUT / "review-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
receipt = {"source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=SRC, text=True).strip(),
           "original_production_sha256": hashlib.sha256(original).hexdigest(), "candidate_production_sha256": hashlib.sha256(candidate).hexdigest(),
           "patch_sha256": hashlib.sha256(patch).hexdigest(), "compiler": subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0],
           "scope": "GCC Linux x86-64, capacity10, static/shared, actual Check registrations; no hosted Clang job executed", "results": results}
(OUT / "review-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"patch_sha256": receipt["patch_sha256"], "static_and_shared": "12 existing + 3 added PASS after; 12 existing PASS + 3 added FAIL before/withdrawal", "routing_disabled": "12/12 PASS in static and shared"}, indent=2))
