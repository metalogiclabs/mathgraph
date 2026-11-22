"""Fresh isolated-module observations for reviewed local Lean source.

Uses the hosted runner's guard classifier. This local runner is not a sandbox and
does not assert correspondence to the upstream HtmlReport dependency or full CLI.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import pyexpat

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "mathgraph_native_guard", HERE.parent / "lean-investigator-v1/native.py")
GUARDS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARDS)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    request_path, output_path, lean_arg, timeout_arg = sys.argv[1:]
    output = Path(output_path).resolve()
    request = json.loads(Path(request_path).read_text())
    started = time.monotonic()
    deadline = started + float(timeout_arg)
    logs = output / "native-logs"
    logs.mkdir()
    processes = []
    lean = shutil.which(lean_arg)
    if lean is None:
        raise RuntimeError("LEAN_NOT_FOUND: provide --lean /path/to/lean-4.35.0/bin/lean")
    # elan-style launchers can dispatch on argv[0]; preserve the invocation name.
    lean = str(Path(lean).absolute())

    def execute(label, args, cwd, env=None):
        remaining = deadline - time.monotonic()
        began = time.monotonic()
        executed = remaining > 0
        if remaining <= 0:
            code, text = 124, "TOTAL_EXECUTION_BUDGET_EXHAUSTED\n"
        else:
            try:
                result = subprocess.run(args, cwd=cwd, env=env, capture_output=True,
                                        text=True, timeout=min(30, remaining))
                code, text = result.returncode, result.stdout + result.stderr
            except subprocess.TimeoutExpired:
                code, text = 124, "NATIVE_TIMEOUT\n"
            except OSError as error:
                code, text = 127, str(error)
                executed = False
        (logs / (label + ".log")).write_text(text)
        processes.append({"label": label, "argv": args, "exit_code": code, "executed": executed,
                          "wall_seconds": time.monotonic() - began,
                          "log": "native-logs/" + label + ".log",
                          "log_sha256": sha(text.encode())})
        return code, text

    env = dict(os.environ)
    for key in ("LEAN_PATH", "LEAN_SRC_PATH", "LEAN_SYSROOT"):
        env.pop(key, None)
    (output / "lean-toolchain").write_text("leanprover/lean4:v4.35.0\n")
    version_code, version = execute("lean-version", [lean, "--version"], output, env)
    if version_code or not version.startswith("Lean (version 4.35.0,"):
        raise RuntimeError("LEAN_VERSION_UNSUPPORTED: " + version.strip()[:300])
    prefix_code, prefix = execute("lean-prefix", [lean, "--print-prefix"], output, env)
    if prefix_code:
        raise RuntimeError("LEAN_TOOLCHAIN_IDENTITY_UNAVAILABLE")
    toolchain_lean = Path(prefix.strip()) / "bin/lean"
    if not toolchain_lean.is_file():
        raise RuntimeError("LEAN_TOOLCHAIN_BINARY_UNAVAILABLE")
    launcher = lean
    lean = str(toolchain_lean.resolve())
    direct_code, direct_version = execute("lean-toolchain-version", [lean, "--version"], output, env)
    if direct_code or direct_version != version:
        raise RuntimeError("LEAN_LAUNCHER_TOOLCHAIN_MISMATCH")
    # The fixed stub is an explicit experimental dependency, not upstream content.
    stub = "module\n"
    result = {"runtime": {
        "lean": version.strip(), "lean_path": lean, "lean_launcher": launcher,
        "lean_executable_sha256": sha(Path(lean).read_bytes()),
        "python": sys.version, "python_path": str(Path(sys.executable).resolve()),
        "python_executable_sha256": sha(Path(sys.executable).read_bytes()),
        "elementtree_sha256": sha(Path(ET.__file__).read_bytes()),
        "pyexpat": {"origin": pyexpat.__spec__.origin,
                     "sha256": sha(Path(pyexpat.__file__).read_bytes())
                     if getattr(pyexpat, "__file__", None) else None},
        "expat_version": pyexpat.EXPAT_VERSION,
        "htmlreport_stub_sha256": sha(stub.encode()),
        "isolation": "TRUSTED_LOCAL_SUBPROCESSES"}, "processes": processes}

    def arm(label, snapshot):
        project = output / "work" / label
        module_dir = project / "Tests/SuiteRunner"
        module_dir.mkdir(parents=True)
        source_path = module_dir / "Reports.lean"
        source = snapshot["source"].encode()
        if sha(source) != snapshot["source_sha256"]:
            raise RuntimeError("SOURCE_DIGEST_MISMATCH")
        source_path.write_bytes(source)
        (module_dir / "HtmlReport.lean").write_text(stub)
        (project / "MathGraphGate.lean").write_text(request["gate"])
        (project / "lean-toolchain").write_text("leanprover/lean4:v4.35.0\n")
        local_env = {**env, "LEAN_PATH": str(project)}
        observed = {"source_sha256": sha(source), "gate_kind": "SELECTED_MODULE_BUILD",
                    "probes": [], "cases": [], "repository_gate_exit": None}
        code, _ = execute(label + "-stub-build", [lean, "-o",
                          "Tests/SuiteRunner/HtmlReport.olean",
                          "Tests/SuiteRunner/HtmlReport.lean"], project, local_env)
        if code:
            observed["build_exit"] = code
            return observed
        code, _ = execute(label + "-module-build", [lean, "-o",
                          "Tests/SuiteRunner/Reports.olean",
                          "Tests/SuiteRunner/Reports.lean"], project, local_env)
        observed["build_exit"] = code
        if code:
            return observed
        observed["module_olean_sha256"] = sha((module_dir / "Reports.olean").read_bytes())

        def probe(item):
            path = project / (item["id"] + ".lean")
            data = item["code"].encode()
            if sha(data) != item["sha256"]:
                raise RuntimeError("PROBE_DIGEST_MISMATCH")
            path.write_bytes(data)
            code, text = execute(label + "-" + item["id"], [lean, path.name], project, local_env)
            if path.read_bytes() != data:
                raise RuntimeError("PROBE_CHANGED_DURING_EXECUTION")
            return {"id": item["id"], **GUARDS.guard_outcome(code, text),
                    "test_file_sha256": sha(data)}

        observed["controls"] = {name: probe(request["controls"][name]) for name in ("pass", "fail")}
        # Always attempt the complete frozen corpus; never stop on a discrepancy.
        observed["probes"] = [probe(item) for item in request["groups"]]
        observed["cases"] = [probe(item) for item in request["cases"]]
        code, _ = execute(label + "-selected-gate", [lean, "--run", "MathGraphGate.lean"], project, local_env)
        observed["repository_gate_exit"] = code
        if source_path.read_bytes() != source or (module_dir / "HtmlReport.lean").read_text() != stub:
            raise RuntimeError("SOURCE_OR_STUB_CHANGED_DURING_EXECUTION")
        return observed

    for label in ("base", "head"):
        result[label] = arm(label, request["sources"][label])
    if sha(Path(lean).read_bytes()) != result["runtime"]["lean_executable_sha256"]:
        raise RuntimeError("LEAN_CHANGED_DURING_EXECUTION")
    result["wall_seconds"] = time.monotonic() - started
    (output / "native.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(type(error).__name__ + ": " + str(error)[:1500], file=sys.stderr)
        sys.exit(2)
