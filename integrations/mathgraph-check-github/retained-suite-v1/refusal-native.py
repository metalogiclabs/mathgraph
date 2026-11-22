"""Fresh source-bound execution of the real suite runner's projected runTest.

The caller supplies exact Git objects and unchanged declaration/function spans.
Full project dependencies are not substituted: the four small actual dependencies
are compiled. This module does not claim full Main CLI or YAML parser coverage.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time


def sha(data):
    return hashlib.sha256(data).hexdigest()


# An explicitly recorded forwarding instrument. The actual source still invokes
# IO.Process.output "timeout"; this proxy records the real timeout child's raw
# result and forwards its bytes and conventional process exit status unchanged.
TIMEOUT_PROXY = r'''import json, os, subprocess, sys, time
from pathlib import Path
started = time.monotonic()
args = [os.environ["MATHGRAPH_EA03_TIMEOUT"], *sys.argv[1:]]
p = subprocess.run(args, capture_output=True)
code = p.returncode if p.returncode >= 0 else 128 - p.returncode
record = {"argv": args, "cwd": os.getcwd(), "raw_returncode": p.returncode,
          "exit_code": code, "stdout": p.stdout.decode("utf-8"),
          "stderr": p.stderr.decode("utf-8"),
          "protocol_environment": os.environ.get("L4YAML_SUITE_PROTOCOL"),
          "wall_seconds": time.monotonic() - started}
Path("process.json").write_text(json.dumps(record, indent=2) + "\n")
sys.stdout.buffer.write(p.stdout)
sys.stderr.buffer.write(p.stderr)
sys.stdout.buffer.flush()
sys.stderr.buffer.flush()
sys.exit(code)
'''


def fixture_source(case, python):
    data = json.dumps(case, ensure_ascii=True)
    return (f"#!{python}\n" +
            "import hashlib, json, os, resource, signal, sys, time\n"
            "from pathlib import Path\n" +
            f"case = json.loads({data!r})\n" +
            "payload = Path(sys.argv[1]).read_bytes()\n"
            "record = {'id': case['id'], 'argv': sys.argv[1:], 'pid': os.getpid(),\n"
            "          'input_sha256': hashlib.sha256(payload).hexdigest(),\n"
            "          'input': payload.decode('utf-8'),\n"
            "          'protocol_environment': os.environ.get('L4YAML_SUITE_PROTOCOL')}\n"
            "Path('backend.json').write_text(json.dumps(record, indent=2) + '\\n')\n"
            "if case['behavior'] == 'sleep':\n"
            "    time.sleep(3)\n"
            "    sys.exit(0)  # Natural completion must not imitate a deadline.\n"
            "elif case['behavior'] == 'signal':\n"
            "    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))\n"
            "    os.kill(os.getpid(), signal.SIGSEGV)\n"
            "sys.stdout.write(case['stdout'])\n"
            "sys.stderr.write(case['stderr'])\n"
            "sys.stdout.flush()\n"
            "sys.stderr.flush()\n"
            "sys.exit(case['exit_code'])\n")


def observer_source(rich, cases):
    extra = '''
    | .error reason => [("kind", Lean.toJson "ERROR"), ("reason", Lean.toJson reason)]
    | .timeout => [("kind", Lean.toJson "TIMEOUT")]
''' if rich else ""
    roster = ",\n    ".join("(" + json.dumps(c["id"]) + ", " +
                               ("true" if c["expect_fail"] else "false") + ")" for c in cases)
    return '''import RefusalProjection
open Tests.SuiteRunner
def observe (id : String) (expectFail : Bool) : IO Lean.Json := do
  let tc : TestCase := { id := id, name := id, tags := [], expectFail := expectFail, yaml := (if expectFail then "[\\n" else "[a]\\n"), tree := "", variant := 0 }
  let actual ← runTest tc 1 .lean none
  let fields : List (String × Lean.Json) := match actual with
    | .pass stdout => [("kind", Lean.toJson "PASS"), ("stdout", Lean.toJson stdout)]
    | .fail reason stdout => [("kind", Lean.toJson "FAIL"), ("reason", Lean.toJson reason), ("stdout", Lean.toJson stdout)]
    | .skip reason => [("kind", Lean.toJson "SKIP"), ("reason", Lean.toJson reason)]
''' + extra + '''
  return Lean.Json.mkObj ([("id", Lean.toJson id), ("repr", Lean.toJson (reprStr actual))] ++ fields)
def main : IO Unit := do
  let project ← IO.currentDir
  let cases : List (String × Bool) := [
    ''' + roster + ''']
  for (id, expectFail) in cases do
    IO.Process.setCurrentDir (project / "cases" / id)
    IO.println (← observe id expectFail).compress
    (← IO.getStdout).flush
'''


def validate_process(case, process, invocation, protocol, case_root):
    """Check the apparatus ran the stipulated fixture, not the target verdict."""
    if not isinstance(process, dict):
        return "PROCESS_EVIDENCE_ABSENT"
    if process.get("exit_code") != case["exit_code"]:
        return "CONTROLLED_EXIT_NOT_OBSERVED"
    argv = process.get("argv", [])
    if len(argv) != 4 or argv[1] != "1" or argv[2] != ".lake/build/bin/tryparse":
        return "PROCESS_INVOCATION_CHANGED"
    expected_path = f"tmp/yaml_suite_test_{case['id']}{'_0' if protocol else ''}.yaml"
    if argv[3] != expected_path or process.get("cwd") != str(case_root):
        return "PROCESS_INPUT_IDENTITY_CHANGED"
    if process.get("protocol_environment") != ("1" if protocol else None):
        return "PROTOCOL_ENVIRONMENT_CHANGED"
    if process.get("stdout") != case["stdout"]:
        return "CONTROLLED_STDOUT_NOT_OBSERVED"
    if case["behavior"] == "exit" and process.get("stderr") != case["stderr"]:
        return "CONTROLLED_STDERR_NOT_OBSERVED"
    if case["behavior"] == "missing":
        if invocation is not None:
            return "MISSING_BACKEND_WAS_EXECUTED"
    else:
        expected_input = "[\n" if case["expect_fail"] else "[a]\n"
        if not isinstance(invocation, dict):
            return "BACKEND_INVOCATION_ABSENT"
        if (invocation.get("id") != case["id"] or
                invocation.get("argv") != [expected_path] or
                invocation.get("input") != expected_input or
                invocation.get("input_sha256") != sha(expected_input.encode()) or
                invocation.get("protocol_environment") != ("1" if protocol else None)):
            return "BACKEND_INPUT_OR_ENVIRONMENT_CHANGED"
    if case["behavior"] == "sleep" and process.get("wall_seconds", 0) < 0.7:
        return "ACTUAL_DEADLINE_NOT_OBSERVED"
    if case["behavior"] == "signal" and process.get("raw_returncode") not in (-11, 139):
        return "ACTUAL_SIGNAL_NOT_OBSERVED"
    return None


def main():
    request_path, output_path, lean_arg, budget_arg = sys.argv[1:]
    output = Path(output_path).resolve()
    request_path = Path(request_path)
    request_bytes = request_path.read_bytes()
    request = json.loads(request_bytes)
    began = time.monotonic()
    deadline = began + float(budget_arg)
    logs = output / "native-logs"
    logs.mkdir()
    processes = []
    result = {"runtime": {}, "processes": processes}

    def persist():
        result["wall_seconds"] = time.monotonic() - began
        (output / "native.json").write_text(json.dumps(result, indent=2) + "\n")

    def execute(label, args, cwd, env):
        started = time.monotonic()
        remaining = deadline - started
        executed = remaining > 0
        stdout = stderr = ""
        if not executed:
            code, stderr = 124, "TOTAL_EXECUTION_BUDGET_EXHAUSTED\n"
        else:
            try:
                p = subprocess.run(args, cwd=cwd, env=env, capture_output=True,
                                   text=True, timeout=min(30, remaining))
                code, stdout, stderr = p.returncode, p.stdout, p.stderr
            except subprocess.TimeoutExpired as error:
                code, stderr = 124, "NATIVE_DRIVER_TIMEOUT\n"
                if error.stdout:
                    stdout = error.stdout.decode() if isinstance(error.stdout, bytes) else error.stdout
            except OSError as error:
                code, stderr, executed = 127, str(error), False
        out_log = f"native-logs/{label}.stdout"
        err_log = f"native-logs/{label}.stderr"
        (output / out_log).write_text(stdout)
        (output / err_log).write_text(stderr)
        processes.append({"label": label, "argv": args, "cwd": str(cwd),
                          "exit_code": code, "executed": executed,
                          "wall_seconds": time.monotonic() - started,
                          "stdout": out_log, "stderr": err_log,
                          "stdout_sha256": sha(stdout.encode()), "stderr_sha256": sha(stderr.encode())})
        persist()
        return code, stdout, stderr

    env = dict(os.environ)
    for key in ("LEAN_PATH", "LEAN_SRC_PATH", "LEAN_SYSROOT", "L4YAML_SUITE_PROTOCOL"):
        env.pop(key, None)
    (output / "lean-toolchain").write_text("leanprover/lean4:v4.35.0\n")
    try:
        launcher = shutil.which(lean_arg)
        if launcher is None:
            raise RuntimeError("LEAN_NOT_FOUND")
        launcher = str(Path(launcher).absolute())
        code, version, _ = execute("lean-version", [launcher, "--version"], output, env)
        if code or not version.startswith("Lean (version 4.35.0,"):
            raise RuntimeError("LEAN_VERSION_UNSUPPORTED")
        code, prefix, _ = execute("lean-prefix", [launcher, "--print-prefix"], output, env)
        if code:
            raise RuntimeError("LEAN_PREFIX_UNAVAILABLE")
        lean = str((Path(prefix.strip()) / "bin/lean").resolve())
        code, direct_version, _ = execute("lean-direct-version", [lean, "--version"], output, env)
        if code or direct_version != version:
            raise RuntimeError("LEAN_LAUNCHER_TOOLCHAIN_MISMATCH")
        timeout_bin = shutil.which("timeout")
        if timeout_bin is None:
            raise RuntimeError("SYSTEM_TIMEOUT_UNAVAILABLE")
        timeout_bin = str(Path(timeout_bin).resolve())
        code, timeout_version, _ = execute("timeout-version", [timeout_bin, "--version"], output, env)
        if code or not timeout_version.startswith("timeout (GNU coreutils)"):
            raise RuntimeError("SYSTEM_TIMEOUT_UNSUPPORTED")
        python = str(Path(sys.executable).resolve())
        proxy = f"#!{python}\n" + TIMEOUT_PROXY
        result["runtime"] = {
            "lean": version.strip(), "lean_launcher": launcher, "lean_path": lean,
            "lean_executable_sha256": sha(Path(lean).read_bytes()),
            "python": sys.version, "python_path": python,
            "python_executable_sha256": sha(Path(python).read_bytes()),
            "timeout_path": timeout_bin, "timeout_version": timeout_version.splitlines()[0],
            "timeout_executable_sha256": sha(Path(timeout_bin).read_bytes()),
            "timeout_proxy_sha256": sha(proxy.encode()),
            "isolation": "REVIEWED_LOCAL_SOURCE_WITH_CONTROLLED_CHILD_PROCESSES",
        }

        def arm(label, snapshot):
            project = output / "work" / label
            project.mkdir(parents=True)
            observed = {"build_exit": None, "source_hashes": {},
                        "projection_sha256": snapshot["projection"]["sha256"], "cases": []}
            result[label] = observed
            dependencies = ["L4YAML/CapstoneAttr.lean", "L4YAML/Init.lean",
                            "L4YAML/Spec/Types.lean", "Tests/SuiteRunner/Meta.lean"]
            if snapshot["projection"]["protocol"]:
                dependencies.append("Tests/SuiteRunner/Protocol.lean")
            for path, data in snapshot["files"].items():
                raw = data["content"].encode()
                if sha(raw) != data["source_sha256"]:
                    raise RuntimeError("SOURCE_DIGEST_MISMATCH")
                destination = project / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(raw)
                observed["source_hashes"][path] = sha(raw)
            projection = snapshot["projection"]["code"].encode()
            if sha(projection) != snapshot["projection"]["sha256"]:
                raise RuntimeError("PROJECTION_DIGEST_MISMATCH")
            (project / "RefusalProjection.lean").write_bytes(projection)
            (project / "lean-toolchain").write_text("leanprover/lean4:v4.35.0\n")
            local_env = {**env, "LEAN_PATH": str(project)}
            for index, path in enumerate(dependencies + ["RefusalProjection.lean"]):
                code, _, _ = execute(f"{label}-build-{index}",
                                     [lean, "-o", str(Path(path).with_suffix(".olean")), path], project, local_env)
                observed["build_exit"] = code
                if code:
                    observed["reason"] = "SOURCE_PROJECTION_BUILD_FAILED: " + path
                    return
            observed["projection_olean_sha256"] = sha((project / "RefusalProjection.olean").read_bytes())
            observer = observer_source(snapshot["projection"]["rich_result"], request["cases"])
            (project / "Observer.lean").write_text(observer)
            observed["observer_sha256"] = sha(observer.encode())
            proxy_path = project / "instrument-bin/timeout"
            proxy_path.parent.mkdir()
            proxy_path.write_text(proxy)
            proxy_path.chmod(0o755)
            fixtures = {}
            for case in request["cases"]:
                case_root = project / "cases" / case["id"]
                case_root.mkdir(parents=True)
                fixture = case_root / ".lake/build/bin/tryparse"
                fixture_data = None
                if case["behavior"] != "missing":
                    fixture.parent.mkdir(parents=True)
                    fixture_data = fixture_source(case, python)
                    fixture.write_text(fixture_data)
                    fixture.chmod(0o755)
                fixtures[case["id"]] = fixture_data
            case_env = {**local_env, "PATH": str(proxy_path.parent) + os.pathsep + env.get("PATH", ""),
                        "MATHGRAPH_EA03_TIMEOUT": timeout_bin}
            code, stdout, _ = execute(label + "-observations",
                                     [lean, "--run", "Observer.lean"], project, case_env)
            parsed = []
            try:
                parsed = [json.loads(line) for line in stdout.splitlines()]
            except ValueError:
                observed["reason"] = "INVALID_NATIVE_OBSERVATION_OUTPUT"
            for case in request["cases"]:
                case_root = project / "cases" / case["id"]
                process_record = case_root / "process.json"
                backend_record = case_root / "backend.json"
                fixture = case_root / ".lake/build/bin/tryparse"
                fixture_data = fixtures[case["id"]]
                row = {"id": case["id"], "exit_code": code, "complete": False,
                       "fixture_sha256": sha(fixture_data.encode()) if fixture_data else None}
                observed["cases"].append(row)
                try:
                    if code:
                        raise RuntimeError("OBSERVER_EXECUTION_FAILED")
                    matching = [item for item in parsed if item.get("id") == case["id"]]
                    if len(matching) != 1 or len(parsed) != len(request["cases"]):
                        raise RuntimeError("OBSERVATION_ROSTER_MISMATCH")
                    row["observation"] = matching[0]
                    row["process"] = json.loads(process_record.read_text())
                    row["backend_invocation"] = json.loads(backend_record.read_text()) if backend_record.exists() else None
                    error = validate_process(case, row["process"], row["backend_invocation"],
                                             snapshot["projection"]["protocol"], case_root)
                    if error:
                        raise RuntimeError(error)
                    if fixture_data is not None and fixture.read_text() != fixture_data:
                        raise RuntimeError("FIXTURE_CHANGED_DURING_EXECUTION")
                    if fixture_data is None and fixture.exists():
                        raise RuntimeError("ABSENT_FIXTURE_APPEARED")
                    row["complete"] = True
                except (OSError, ValueError, RuntimeError) as error:
                    row["reason"] = str(error)
                    observed.setdefault("reason", "CASE_EXECUTION_INCOMPLETE: " + case["id"] + ": " + str(error))
                persist()
            if (project / "RefusalProjection.lean").read_bytes() != projection:
                raise RuntimeError("SOURCE_PROJECTION_CHANGED_DURING_EXECUTION")
            for path, data in snapshot["files"].items():
                if sha((project / path).read_bytes()) != data["source_sha256"]:
                    raise RuntimeError("SOURCE_DEPENDENCY_CHANGED_DURING_EXECUTION")
            if proxy_path.read_text() != proxy or (project / "Observer.lean").read_text() != observer:
                raise RuntimeError("INSTRUMENT_CHANGED_DURING_EXECUTION")

        for label in ("base", "head"):
            arm(label, request["sources"][label])
        for path, key in ((lean, "lean_executable_sha256"), (python, "python_executable_sha256"),
                          (timeout_bin, "timeout_executable_sha256")):
            if sha(Path(path).read_bytes()) != result["runtime"][key]:
                raise RuntimeError("APPARATUS_EXECUTABLE_CHANGED")
        if request_path.read_bytes() != request_bytes:
            raise RuntimeError("REQUEST_CHANGED_DURING_EXECUTION")
    except Exception as error:
        result["reason"] = type(error).__name__ + ": " + str(error)
        for label in ("base", "head"):
            result.setdefault(label, {"build_exit": None, "cases": [], "reason": result["reason"]})
    finally:
        persist()


if __name__ == "__main__":
    main()
