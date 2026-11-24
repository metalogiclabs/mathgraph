"""Native capacity qualification for the fork and current upstream, with rollback."""
from pathlib import Path
import difflib
import hashlib
import json
import os
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
CMAKE = ROOT / "build-tools/cmake/data/bin/cmake"
CHECK = ROOT / "libcheck-installed"
COMMANDS = OUT / "route-commands.jsonl"
COMMANDS.write_text("")

def cmd(args, src, name, env=None):
    result = subprocess.run(list(map(str, args)), cwd=src, capture_output=True, env=env)
    (OUT / (name + ".stdout")).write_bytes(result.stdout)
    (OUT / (name + ".stderr")).write_bytes(result.stderr)
    with COMMANDS.open("a") as f:
        f.write(json.dumps({"name": name, "cwd": str(src), "args": list(map(str, args)), "exit": result.returncode}) + "\n")
    assert result.returncode == 0, (name, result.stderr.decode(errors="replace")[-1500:])
    return result.stdout

def oracle(raw):
    lines = raw.decode().splitlines()
    capacity = int(lines[0].split("\t")[1])
    model, errors = [], []
    for line in lines[2:]:
        op, key, rc, count, found, via = line.split("\t")
        key, rc, count, found, via = map(int, (key, rc, count, found, via))
        if op in ("insert", "update"):
            value = 7 if op == "update" else 65535
            matches = [i for i, (k, v) in enumerate(model) if k == key]
            if matches:
                model[matches[0]] = (key, value)
            elif len(model) < capacity:
                model.append((key, value))
            else:
                model[-1] = (key, value)  # Maintainer's #350 last-slot replacement policy.
        if op == "clear":
            model.clear()
        matched = [v for k, v in model if k == key]
        expected = [len(model), int(bool(matched)), matched[0] if matched else 0]
        rc_ok = rc != 0 if op == "reject-null" else rc == 0
        if [count, found, via] != expected or not rc_ok:
            errors.append({"actual": line, "expected_count_found_via": expected, "rc_ok": rc_ok})
    return {"capacity": capacity, "observations": len(lines) - 2, "discrepancies": len(errors), "failures": errors}

receipts = {}
for name, folder, target in (("endurosat", "endurosat-csp-es", "csp_es"), ("libcsp", "libcsp-current", "csp")):
    src = ROOT / folder
    source = src / "src/csp_rtable_cidr.c"
    original = source.read_bytes()
    expression = rb"\t\tentry = &rtable\[rtable_inptr\+\+\];\n\t\tif \(rtable_inptr >= CSP_RTABLE_SIZE\) \{\n\t\t\trtable_inptr = CSP_RTABLE_SIZE\s*-\s*1;\n\t\t\}"
    replacement = (b"\t\tif (rtable_inptr < CSP_RTABLE_SIZE) {\n"
                   b"\t\t\tentry = &rtable[rtable_inptr++];\n"
                   b"\t\t} else {\n"
                   b"\t\t\tentry = &rtable[CSP_RTABLE_SIZE - 1];\n\t\t}")
    patched, replacements = re.subn(expression, lambda _: replacement, original)
    assert replacements == 1
    (OUT / ("route-" + name + ".patch")).write_text("".join(difflib.unified_diff(original.decode().splitlines(keepends=True), patched.decode().splitlines(keepends=True), fromfile="a/src/csp_rtable_cidr.c", tofile="b/src/csp_rtable_cidr.c")))
    repo_receipt = {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=src, text=True).strip(),
                    "before_source_sha256": hashlib.sha256(original).hexdigest(),
                    "after_source_sha256": hashlib.sha256(patched).hexdigest(), "arms": {}}
    builds = {}
    for capacity in (1, 2, 10):
        build = src / ("build-route-" + str(capacity))
        builds[capacity] = build
        env = dict(os.environ, PKG_CONFIG_PATH=str(CHECK / "lib/pkgconfig"))
        cmd([CMAKE, "-S", src, "-B", build, "-DCSP_USE_RTABLE=ON", "-DCSP_BUILD_SAMPLES=OFF", "-DBUILD_SHARED_LIBS=OFF",
             "-DCMAKE_BUILD_TYPE=Debug", "-DCSP_RTABLE_SIZE=" + str(capacity),
             "-DCMAKE_C_FLAGS=-I" + str(CHECK / "include"), "-DCMAKE_EXE_LINKER_FLAGS=-L" + str(CHECK / "lib")],
            src, f"route-{name}-configure-{capacity}", env)
    try:
        for stage, content in (("before", original), ("after", patched), ("withdrawn", original)):
            source.write_bytes(content)
            repo_receipt["arms"][stage] = {}
            for capacity, build in builds.items():
                prefix = f"route-{name}-{stage}-{capacity}"
                cmd([CMAKE, "--build", build, "-j", "2", "--target", target], src, prefix + "-build")
                binary = OUT / (prefix + "-probe")
                library = build / ("lib" + target + ".a")
                cmd(["gcc", "-std=gnu11", "-O0", "-g", "-I" + str(src / "include"), "-I" + str(build / "include"),
                     OUT / "route-capacity-probe.c", library, "-lpthread", "-o", binary], src, prefix + "-compile")
                for version in (1, 2):
                    raw = cmd([binary, version], src, prefix + "-v" + str(version))
                    result = oracle(raw)
                    if stage == "after":
                        assert result["discrepancies"] == 0
                    else:
                        assert result["discrepancies"] > 0
                    if stage == "withdrawn":
                        before = (OUT / (f"route-{name}-before-{capacity}-v{version}.stdout")).read_bytes()
                        assert raw == before
                    repo_receipt["arms"][stage][f"capacity{capacity}-v{version}"] = result
                if capacity == 10:
                    cmd([CMAKE, "--build", build, "-j", "2", "--target", "csp_tests"], src, prefix + "-author-build")
                    tests = cmd([build / "unittests/csp_tests"], src, prefix + "-author-tests", dict(os.environ, LD_LIBRARY_PATH=str(CHECK / "lib")))
                    repo_receipt["arms"][stage]["author_tests"] = tests.decode().splitlines()[-1]
    finally:
        source.write_bytes(original)
    repo_receipt["source_restored"] = source.read_bytes() == original
    receipts[name] = repo_receipt

(OUT / "route-receipt.json").write_text(json.dumps(receipts, indent=2) + "\n")
print(json.dumps({name: {stage: {"discrepant_observations": sum(x["discrepancies"] for x in result.values() if isinstance(x, dict)),
                               "observations": sum(x["observations"] for x in result.values() if isinstance(x, dict)),
                               "author_tests": result["author_tests"]} for stage, result in repo["arms"].items()} for name, repo in receipts.items()}, indent=2))
