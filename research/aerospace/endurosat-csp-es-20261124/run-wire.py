from pathlib import Path
import hashlib
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
SRC = ROOT / "endurosat-csp-es"
CMAKE = ROOT / "build-tools/cmake/data/bin/cmake"
CHECK = ROOT / "libcheck-installed"
commands = []

def cmd(args, name, env=None):
    r = subprocess.run(list(map(str, args)), cwd=ROOT, capture_output=True, env=env)
    (OUT / (name + ".stdout")).write_bytes(r.stdout)
    (OUT / (name + ".stderr")).write_bytes(r.stderr)
    commands.append({"args": list(map(str, args)), "name": name, "exit": r.returncode})
    assert r.returncode == 0, (name, r.stderr.decode(errors="replace"))
    return r.stdout

original = (SRC / "src/csp_id.c").read_bytes()
summaries = {}
for label, buildname in (("native", "build-mathgraph"), ("portable", "build-portable-endian")):
    build = SRC / buildname
    env = dict(os.environ, PKG_CONFIG_PATH=str(CHECK / "lib/pkgconfig"))
    cmd([CMAKE, "-S", SRC, "-B", build, "-DCSP_BUILD_SAMPLES=OFF", "-DCMAKE_BUILD_TYPE=Debug",
         "-DHAVE_ENDIAN_H=" + ("ON" if label == "native" else "OFF")], "wire-" + label + "-configure", env)
    cmd([CMAKE, "--build", build, "-j", "2", "--target", "csp_es", "csp_tests"], "wire-" + label + "-build")
    cmd([build / "unittests/csp_tests"], "wire-" + label + "-author-tests", dict(os.environ, LD_LIBRARY_PATH=str(CHECK / "lib")))
    binary = OUT / ("wire-" + label)
    cmd(["gcc", "-std=gnu11", "-O0", "-g", "-I" + str(SRC / "include"), "-I" + str(build / "include"),
         OUT / "wire-probe.c", build / "libcsp_es.a", "-lpthread", "-o", binary], "wire-" + label + "-compile")
    cmd([os.sys.executable, OUT / "wire-matrix.py", binary, label], "wire-" + label + "-matrix")
    summaries[label] = json.loads((OUT / ("wire-" + label + ".json")).read_text())["summary"]
mutant = original.decode().replace("#define CSP_ID1_SRC_OFFSET   25", "#define CSP_ID1_SRC_OFFSET   20").replace("#define CSP_ID1_DST_OFFSET   20", "#define CSP_ID1_DST_OFFSET   25")
assert mutant != original.decode()
(OUT / "wire-srcdst-mutant.c").write_text(mutant)
cmd(["gcc", "-std=gnu11", "-O0", "-g", "-I" + str(SRC / "include"), "-I" + str(SRC / "build-mathgraph/include"),
     OUT / "wire-probe.c", OUT / "wire-srcdst-mutant.c", SRC / "build-mathgraph/libcsp_es.a", "-lpthread", "-o", OUT / "wire-mutant"], "wire-mutant-compile")
cmd([os.sys.executable, OUT / "wire-matrix.py", OUT / "wire-mutant", "mutant"], "wire-mutant-matrix")
summaries["injected_mutant"] = json.loads((OUT / "wire-mutant.json").read_text())["summary"]
assert (OUT / "wire-native.stdout").read_bytes() == (OUT / "wire-portable.stdout").read_bytes()
assert (SRC / "src/csp_id.c").read_bytes() == original
receipt = {"source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=SRC, text=True).strip(),
           "source_sha256": hashlib.sha256(original).hexdigest(), "mutant_sha256": hashlib.sha256(mutant.encode()).hexdigest(),
           "original_source_unchanged": True, "receipt_scope": "Linux x86-64; portable endian code also runs on x86-64, not a target/emulator", "results": summaries}
(OUT / "wire-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
(OUT / "wire-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
