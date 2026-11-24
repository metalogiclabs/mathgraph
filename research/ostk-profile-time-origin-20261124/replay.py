#!/usr/bin/env python3
"""Recompile the pinned profile translation unit; verify original/fix/withdrawal.

Network is used only to prepare public source and versioned build dependencies.
The actual native experiments use an empty data repository and synthetic states.
This is a focused translation-unit qualification, not a whole-project build.
"""
import concurrent.futures
import csv
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request
import xml.etree.ElementTree as ET

SOURCE = "ddc1924a0912bfafc89ef3a217ad21cfc2d98b1f"
GTEST = "52eb8108c5bdec04579160ae17225d66034bd723"
TARGET = "src/OpenSpaceToolkit/Astrodynamics/Flight/Profile/Model/Tabulated.cpp"
BLOB = "a07b0f3cba89f7a44924e7420ca7399771b43ceb"
HERE = Path(__file__).resolve().parent
ROOT = Path.cwd()
WORK = ROOT / "ostk-replay-work"
OUT = ROOT / "ostk-native-evidence"
WORK.mkdir()
OUT.mkdir()
ROOTFS = WORK / "deps"
ROOTFS.mkdir()
commands = []

def run(args, cwd=WORK, log=None, env=None):
    commands.append({"args": list(map(str, args)), "cwd": str(cwd), "log": log})
    if log:
        with (OUT / (log + ".log")).open("w") as f:
            result = subprocess.run(list(map(str, args)), cwd=cwd, env=env, stdout=f, stderr=subprocess.STDOUT)
        assert result.returncode == 0, (log, result.returncode)
    else:
        subprocess.run(list(map(str, args)), cwd=cwd, env=env, check=True)

def clone(repo, sha, dest):
    run(["git", "init", dest])
    run(["git", "remote", "add", "origin", "https://github.com/" + repo + ".git"], cwd=dest)
    run(["git", "fetch", "--depth=1", "origin", sha], cwd=dest)
    run(["git", "checkout", "--detach", sha], cwd=dest)

source = WORK / "source"
clone("open-space-collective/open-space-toolkit-astrodynamics", SOURCE, source)
gtest = WORK / "googletest"
clone("google/googletest", GTEST, gtest)
original_bytes = (source / TARGET).read_bytes()
assert hashlib.sha1(b"blob " + str(len(original_bytes)).encode() + b"\0" + original_bytes).hexdigest() == BLOB

deps = json.loads((HERE / "dependencies.json").read_text())
def download(item):
    url = item["url"]
    data = urllib.request.urlopen(url, timeout=120).read()
    assert hashlib.sha256(data).hexdigest() == item["sha256"], url
    if item.get("published_digest"):
        assert item["published_digest"] == "sha256:" + item["sha256"]
    path = WORK / url.rsplit("/", 1)[1]
    path.write_bytes(data)
    return path
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    packages = list(pool.map(download, deps))
for package in packages:
    run(["dpkg-deb", "-x", package, ROOTFS])

# Identical build-only compatibility shim for GCC 14's lvalue-only make_format_args.
header = ROOTFS / "usr/local/include/OpenSpaceToolkit/Core/Type/String.hpp"
text = header.read_text()
old = "std::make_format_args(std::forward<Args>(anArgumentList)...)"
assert text.count(old) == 1
patched = text.replace(old, "std::make_format_args(anArgumentList...)")
header.write_text(patched)
(OUT / "core-format-build-compatibility.patch").write_text("".join(difflib.unified_diff(
    text.splitlines(True), patched.splitlines(True), fromfile="Core/String.hpp", tofile="Core/String.hpp")))

original = WORK / "Tabulated-original.cpp"
original.write_bytes(original_bytes)
fixed_text = original_bytes.decode()
old = "    const State& firstState = aStateArray.getFirst();\n\n    // Ensure the states are sorted by instant"
assert fixed_text.count(old) == 1
fixed_text = fixed_text.replace(old, "    // Ensure the states are sorted by instant")
old = "    aTimestampVector.resize(stateArray_.getSize());"
assert fixed_text.count(old) == 1
fixed_text = fixed_text.replace(old, "    const State& firstState = stateArray_.getFirst();\n\n" + old)
fixed = WORK / "Tabulated-fixed.cpp"
fixed.write_text(fixed_text)
(OUT / "profile-time-origin.patch").write_text("".join(difflib.unified_diff(
    original_bytes.decode().splitlines(True), fixed_text.splitlines(True), fromfile="a/" + TARGET, tofile="b/" + TARGET)))

inc = ["-I" + str(p) for p in [source / "include", source / "test", ROOTFS / "usr/local/include",
    ROOTFS / "usr/include", ROOTFS / "usr/include/eigen3", gtest / "googletest/include", gtest / "googletest"]]
base = ["g++", "-std=c++20", "-O1", "-fPIC", "-pthread", *inc]
units = {
    "original": original,
    "fixed": fixed,
    "probe": HERE / "profile_permutation_probe.cpp",
    "authors": source / "test/OpenSpaceToolkit/Astrodynamics/Flight/Profile/Tabulated.test.cpp",
    "gtest": gtest / "googletest/src/gtest-all.cc",
    "main": source / "test/Main.test.cxx",
}
# Commands stay ordered and explicit; independent compiler processes may overlap.
def compile_unit(item):
    name, unit = item
    run([*base, "-c", unit, "-o", WORK / (name + ".o")], log="compile-" + name)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    list(pool.map(compile_unit, units.items()))
libdir = ROOTFS / "usr/local/lib"
libs = list(dict.fromkeys(p.resolve() for p in sorted(libdir.glob("libopen*.so"))))
assert len(libs) == 5
link = [*libs, "-Wl,-rpath," + str(libdir)]
for name in ["original", "fixed"]:
    run(["g++", "-shared", "-o", WORK / ("libprofile-" + name + ".so"), WORK / (name + ".o"), *link], log="link-" + name)
run(["g++", "-o", WORK / "probe", WORK / "probe.o", *link], log="link-probe")
run(["g++", "-pthread", "-o", WORK / "authors", WORK / "authors.o", WORK / "gtest.o", WORK / "main.o", *link], log="link-authors")

data = WORK / "empty-data"
data.mkdir()
env = dict(os.environ, LD_LIBRARY_PATH=str(libdir), OSTK_PHYSICS_DATA_LOCAL_REPOSITORY=str(data),
           OSTK_PHYSICS_ENVIRONMENT_EPHEMERIS_SPICE_ENGINE_MODE="Manual")
summary = {"source": SOURCE, "target_blob": BLOB, "phases": {}, "dependencies": deps,
           "boundary": "Pinned translation unit and unchanged 10-test C++ profile suite; released 18.0.1 native dependencies; one build-only Core formatting shim identical in every arm; empty data repository; no full-project build or qualification."}
for phase, overlay, expected in [("released", None, 594), ("before", "original", 594),
                                  ("repair", "fixed", 0), ("withdrawal", "original", 594)]:
    e = dict(env)
    if overlay: e["LD_PRELOAD"] = str(WORK / ("libprofile-" + overlay + ".so"))
    run([WORK / "authors", "--gtest_output=xml:" + str(OUT / (phase + "-authors.xml"))], log=phase + "-authors", env=e)
    xml = ET.parse(OUT / (phase + "-authors.xml")).getroot()
    assert int(xml.attrib["tests"]) == 10 and int(xml.attrib["failures"]) == 0 and int(xml.attrib["errors"]) == 0
    run([WORK / "probe", OUT / (phase + ".csv")], log=phase + "-probe", env=e)
    rows = list(csv.DictReader((OUT / (phase + ".csv")).open()))
    wrong = sum(float(r["position_error"]) > 1e-7 for r in rows)
    assert len(rows) == 840 and wrong == expected, (phase, len(rows), wrong)
    for key in ["velocity_error", "rate_error", "attitude_error", "timestamp_error"]:
        assert max(float(r[key]) for r in rows) < 1e-9, (phase, key)
    summary["phases"][phase] = {"cases": len(rows), "position_discrepancies": wrong, "original_cpp_tests": 10,
                                "trace_sha256": hashlib.sha256((OUT / (phase + ".csv")).read_bytes()).hexdigest()}
    print(phase, json.dumps(summary["phases"][phase]), flush=True)
assert (OUT / "released.csv").read_bytes() == (OUT / "before.csv").read_bytes() == (OUT / "withdrawal.csv").read_bytes()
assert (source / TARGET).read_bytes() == original_bytes
run(["git", "diff", "--exit-code"], cwd=source, log="source-unchanged")
run(["g++", "--version"], log="compiler-version")
summary["shared_libraries"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in libs}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
(OUT / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
for p in [original, fixed, HERE / "profile_permutation_probe.cpp", HERE / "replay.py", HERE / "dependencies.json"]:
    shutil.copy2(p, OUT / p.name)
manifest = {str(p.relative_to(OUT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.rglob("*")) if p.is_file()}
(OUT / "SHA256SUMS.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("QUALIFIED bounded sample-order counterexample, native repair, withdrawal, and author controls", flush=True)
