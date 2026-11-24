"""Local native backport qualification. Does not contact any operational system."""
from pathlib import Path
import hashlib
import difflib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
SRC = ROOT / "endurosat-csp-es"
CMAKE = ROOT / "build-tools/cmake/data/bin/cmake"
CHECK = ROOT / "libcheck-installed"
ENV = dict(os.environ, LD_LIBRARY_PATH=str(CHECK / "lib"))
SOURCE = SRC / "src/csp_dedup.c"
original = SOURCE.read_bytes()
old_time = b"if (time > csp_dedup_timestamp[i] + CSP_DEDUP_WINDOW_MS)"
new_time = b"if (time - csp_dedup_timestamp[i] > CSP_DEDUP_WINDOW_MS)"
old_loop = b"while (i != csp_dedup_in)"
new_loop = b"for (unsigned int n = 0; n < CSP_DEDUP_COUNT; n++)"
assert original.count(old_time) == original.count(old_loop) == 1
patched = original.replace(old_time, new_time).replace(old_loop, new_loop)

def command(args, name, allowed=(0,)):
    result = subprocess.run(list(map(str, args)), cwd=SRC, env=ENV, capture_output=True)
    (OUT / (name + ".stdout")).write_bytes(result.stdout)
    (OUT / (name + ".stderr")).write_bytes(result.stderr)
    with (OUT / "commands.jsonl").open("a") as stream:
        stream.write(json.dumps({"name": name, "args": list(map(str, args)), "exit": result.returncode}) + "\n")
    assert result.returncode in allowed, (name, result.returncode, result.stderr.decode(errors="replace")[-1000:])
    return result

def qualify(stage):
    command([CMAKE, "--build", "build-mathgraph", "-j", "2", "--target", "csp_es", "csp_tests"], stage + "-build")
    includes = ["-Iinclude", "-Ibuild-mathgraph/include", "-Isrc"]
    library = SRC / "build-mathgraph/libcsp_es.a"
    probe = OUT / (stage + "-probe")
    command(["gcc", "-std=gnu11", "-O0", "-g", *includes, OUT / "probe.c", library,
             "-Wl,--wrap=csp_get_ms", "-lpthread", "-o", probe], stage + "-compile-probe")
    matrix = command([sys.executable, OUT / "matrix.py", probe], stage + "-matrix")
    author = command([SRC / "build-mathgraph/unittests/csp_tests"], stage + "-author-tests")
    upstream = OUT / (stage + "-upstream-tests")
    command(["gcc", "-std=gnu11", *includes, "-I" + str(CHECK / "include"), OUT / "upstream-dedup-tests.c",
             OUT / "upstream-test-main.c", library, "-L" + str(CHECK / "lib"), "-lcheck", "-lpthread", "-lm", "-lrt", "-o", upstream], stage + "-compile-upstream-tests")
    upstream_result = command([upstream], stage + "-upstream-tests", allowed=(0, 1))
    return {"matrix": json.loads(matrix.stderr), "upstream_tests_exit": upstream_result.returncode,
            "author_tests": author.stdout.decode().splitlines()[-1]}

(OUT / "commands.jsonl").write_text("")
receipt = {}
try:
    receipt["before"] = qualify("before")
    SOURCE.write_bytes(patched)
    receipt["after"] = qualify("after")
finally:
    SOURCE.write_bytes(original)
receipt["withdrawn"] = qualify("withdrawn")
assert (OUT / "before-matrix.stdout").read_bytes() == (OUT / "withdrawn-matrix.stdout").read_bytes()
assert receipt["after"]["matrix"]["mismatches"] == 0
assert receipt["before"]["upstream_tests_exit"] == receipt["withdrawn"]["upstream_tests_exit"] == 1
assert receipt["after"]["upstream_tests_exit"] == 0
receipt["source_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=SRC, text=True).strip()
receipt["source_restored"] = SOURCE.read_bytes() == original
receipt["original_source_sha256"] = hashlib.sha256(original).hexdigest()
receipt["patched_source_sha256"] = hashlib.sha256(patched).hexdigest()
receipt["gcc"] = subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0]
receipt["cmake"] = subprocess.check_output([CMAKE, "--version"], text=True).splitlines()[0]
receipt["libcheck_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT / "libcheck", text=True).strip()
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
(OUT / "candidate.patch").write_text("".join(difflib.unified_diff(original.decode().splitlines(keepends=True), patched.decode().splitlines(keepends=True), fromfile="a/src/csp_dedup.c", tofile="b/src/csp_dedup.c")))
print(json.dumps(receipt, indent=2))
