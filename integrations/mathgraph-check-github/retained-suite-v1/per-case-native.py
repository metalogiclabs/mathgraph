"""Execute the real Reports comparison consumers in a disclosed module isolate.

Original subject bytes and original guards are retained. The empty HtmlReport
module is an experimental dependency, not upstream content. Backend observations
are controlled fixtures; neither the four parsers nor Main.runCompare execute.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time


def sha(data):
    return hashlib.sha256(data).hexdigest()


HEADER = '''import Tests.SuiteRunner.Reports
open Lean Tests.SuiteRunner

'''

LEGACY = '''def observeCase (c : Json) : Except String Json := do
  let id ← c.getObjValAs? String "id"
  let transcripts ← (← c.getObjVal? "legacy_transcripts").getArr?
  let mut results : List (String × List (String × Reports.Counts)) := []
  let mut lines : Array Json := #[]
  let mut agreement := true
  for preset in Reports.presets do
    let mut row : List (String × Reports.Counts) := []
    for r in transcripts do
      if (← r.getObjValAs? String "preset") == preset then
        let backend ← r.getObjValAs? String "backend"
        let stdout ← r.getObjValAs? String "stdout"
        let some counts := Reports.parseTotal? stdout | throw "missing TOTAL observation"
        row := row ++ [(backend, counts)]
    let (line, same) := Reports.presetLine preset row
    lines := lines.push (Json.mkObj [("preset", toJson preset), ("agreement", toJson same), ("line", toJson line)])
    if !same then agreement := false
    results := results ++ [(preset, row)]
  let serialized := Reports.crossLangJson results
  let data ← Json.parse serialized >>= Reports.readCrossLang
  let readbackAgreement := data.all (fun (preset, row) => (Reports.presetLine preset row).2)
  return Json.mkObj [("id", toJson id), ("agreement", toJson agreement),
    ("preset_agreement", toJson lines), ("verdict", toJson (Reports.verdictLine agreement)),
    ("serialized", toJson serialized), ("decoded_ok", toJson true),
    ("readback_agreement", toJson readbackAgreement),
    ("html", toJson (Reports.crossLangHtml data))]

'''

PER_CASE = '''def observeCase (c : Json) : Except String Json := do
  let id ← c.getObjValAs? String "id"
  let data : Reports.CrossLangEvidence ← fromJson? (← c.getObjVal? "evidence")
  let mut lines : Array Json := #[]
  for preset in Reports.presets do
    let (line, same) := Reports.presetLine preset (data.runs.filter (fun r => r.preset == preset))
    lines := lines.push (Json.mkObj [("preset", toJson preset), ("agreement", toJson same), ("line", toJson line)])
  let agreement := (Reports.validateCrossLang data).isOk
  let serialized := Reports.crossLangJson data
  let readback := Json.parse serialized >>= Reports.readCrossLang
  -- The real renderer executes even when the validator/readback rejects.
  -- Its refusal is observed here, never supplied by the harness.
  let html := Reports.crossLangHtml data
  return Json.mkObj [("id", toJson id), ("agreement", toJson agreement),
    ("preset_agreement", toJson lines), ("verdict", toJson (Reports.verdictLine agreement)),
    ("serialized", toJson serialized), ("decoded_ok", toJson readback.isOk),
    ("readback_agreement", toJson readback.isOk),
    ("html", toJson html)]

'''

FOOTER = '''def main (args : List String) : IO UInt32 := do
  let some path := args.head? | IO.eprintln "fixture path required"; return 2
  let raw ← IO.FS.readFile path
  let parsed := do
    let cases ← Json.parse raw >>= Json.getArr?
    let records ← cases.toList.mapM observeCase
    return Json.mkObj [("records", toJson records)]
  match parsed with
  | .error reason => IO.eprintln reason; return 2
  | .ok result => IO.println result.compress; return 0
'''


def observer(source):
    if "structure CrossLangEvidence where" in source and "def validateCrossLang " in source:
        return "per-case-acceptance-v2", HEADER + PER_CASE + FOOTER
    if "structure Counts where" in source and "def parseTotal? " in source:
        return "aggregate-counts-v1", HEADER + LEGACY + FOOTER
    raise ValueError("UNSUPPORTED_COMPARISON_API")


def main():
    request_path, output_path, lean_arg, timeout_arg = sys.argv[1:]
    output = Path(output_path).resolve()
    request = json.loads(Path(request_path).read_text())
    logs = output / "native-logs"
    logs.mkdir()
    deadline = time.monotonic() + float(timeout_arg)
    result = {"runtime": {}, "processes": []}
    fixture = output / "corpus.json"
    fixture_bytes = fixture.read_bytes()
    fixture_hash = sha(fixture_bytes)
    stub = "module\n"

    def execute(label, argv, cwd, env):
        remaining = deadline - time.monotonic()
        started = time.monotonic()
        executed = remaining > 0
        stdout, stderr = "", ""
        if remaining <= 0:
            code, stderr = 124, "TOTAL_EXECUTION_BUDGET_EXHAUSTED\n"
        else:
            try:
                p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True,
                                   timeout=min(60, remaining))
                code, stdout, stderr = p.returncode, p.stdout, p.stderr
            except subprocess.TimeoutExpired as error:
                code = 124
                stdout = error.stdout.decode(errors="replace") if isinstance(error.stdout, bytes) else error.stdout or ""
                stderr = error.stderr.decode(errors="replace") if isinstance(error.stderr, bytes) else error.stderr or ""
                stderr += "\nNATIVE_TIMEOUT\n"
            except OSError as error:
                code, stderr, executed = 127, str(error), False
        text = stdout + stderr
        (logs / (label + ".log")).write_text(text)
        result["processes"].append({"label": label, "argv": argv, "exit_code": code,
                                    "executed": executed, "wall_seconds": time.monotonic() - started,
                                    "log": "native-logs/" + label + ".log", "log_sha256": sha(text.encode())})
        return code, stdout, stderr

    env = dict(os.environ)
    for key in ("LEAN_PATH", "LEAN_SRC_PATH", "LEAN_SYSROOT"):
        env.pop(key, None)
    try:
        lean = shutil.which(lean_arg)
        if not lean:
            raise RuntimeError("LEAN_NOT_FOUND")
        lean = str(Path(lean).absolute())
        code, version, err = execute("lean-version", [lean, "--version"], output, env)
        if code or not version.startswith("Lean (version 4.35.0,"):
            raise RuntimeError("LEAN_VERSION_UNSUPPORTED: " + (version + err).strip()[:300])
        code, prefix, _ = execute("lean-prefix", [lean, "--print-prefix"], output, env)
        direct = Path(prefix.strip()) / "bin/lean"
        if code or not direct.is_file():
            raise RuntimeError("LEAN_TOOLCHAIN_IDENTITY_UNAVAILABLE")
        launcher = lean
        lean = str(direct.resolve())
        code, checked_version, _ = execute("lean-direct-version", [lean, "--version"], output, env)
        if code or checked_version != version:
            raise RuntimeError("LEAN_LAUNCHER_TOOLCHAIN_MISMATCH")
        result["runtime"] = {"lean": version.strip(), "lean_path": lean, "lean_launcher": launcher,
                             "lean_executable_sha256": sha(Path(lean).read_bytes()),
                             "python": sys.version, "python_path": str(Path(sys.executable).resolve()),
                             "python_executable_sha256": sha(Path(sys.executable).read_bytes()),
                             "htmlreport_stub_sha256": sha(stub.encode()),
                             "isolation": "TRUSTED_LOCAL_SUBPROCESSES",
                             "boundary": "Exact Reports module; controlled backend observations; empty HtmlReport dependency; no full CLI or parser execution"}

        def arm(label, snapshot):
            source = snapshot["source"].encode()
            if sha(source) != snapshot["source_sha256"]:
                raise ValueError("SOURCE_DIGEST_MISMATCH")
            project = output / "work" / label
            module = project / "Tests/SuiteRunner"
            module.mkdir(parents=True)
            (module / "Reports.lean").write_bytes(source)
            (module / "HtmlReport.lean").write_text(stub)
            (project / "lean-toolchain").write_text("leanprover/lean4:v4.35.0\n")
            observed = {"source_sha256": sha(source), "corpus_sha256": fixture_hash,
                        "build_exit": None, "observer_exit": None, "observations": []}
            result[label] = observed
            family, code = observer(snapshot["source"])
            observed.update(schema_family=family, observer_sha256=sha(code.encode()))
            (project / "Observer.lean").write_text(code)
            local_env = {**env, "LEAN_PATH": str(project)}
            status, _, _ = execute(label + "-stub", [lean, "-o", "Tests/SuiteRunner/HtmlReport.olean",
                                                       "Tests/SuiteRunner/HtmlReport.lean"], project, local_env)
            if status:
                observed.update(build_exit=status, reason="DEPENDENCY_BUILD_FAILED")
                return
            status, _, _ = execute(label + "-module", [lean, "-o", "Tests/SuiteRunner/Reports.olean",
                                                         "Tests/SuiteRunner/Reports.lean"], project, local_env)
            observed["build_exit"] = status
            if status:
                observed["reason"] = "MODULE_BUILD_FAILED"
                return
            observed["module_olean_sha256"] = sha((module / "Reports.olean").read_bytes())
            controls = {}
            for name, expression in (("pass", "true"), ("fail", "false")):
                path = project / ("Control_" + name + ".lean")
                path.write_text("import Tests.SuiteRunner.Reports\n#guard " + expression + "\n")
                status, stdout, stderr = execute(label + "-control-" + name, [lean, path.name], project, local_env)
                text = stdout + stderr
                false_guard = "did not evaluate to `true`" in text
                other = bool(re.findall(r"\berror:", text)) and not (false_guard and len(re.findall(r"\berror:", text)) == 1)
                controls[name] = {"exit": status, "guard_false": false_guard, "other_errors": other}
            observed["controls"] = controls
            status, stdout, stderr = execute(label + "-observer", [lean, "--run", "Observer.lean", str(fixture)], project, local_env)
            observed["observer_exit"] = status
            if status == 0:
                try:
                    records = json.loads(stdout)
                    if set(records) != {"records"} or not isinstance(records["records"], list):
                        raise ValueError("unexpected observer shape")
                    observed["observations"] = records["records"]
                except (ValueError, TypeError) as error:
                    observed["reason"] = "OBSERVER_OUTPUT_INVALID: " + str(error)
            else:
                observed["reason"] = "OBSERVER_EXECUTION_FAILED"
            observed["source_preserved"] = (module / "Reports.lean").read_bytes() == source
            observed["inputs_preserved"] = ((module / "HtmlReport.lean").read_text() == stub
                                            and (project / "Observer.lean").read_text() == code
                                            and fixture.read_bytes() == fixture_bytes)

        for label in ("base", "head"):
            try:
                arm(label, request["sources"][label])
            except Exception as error:
                result.setdefault(label, {}).update(reason=type(error).__name__ + ": " + str(error))
        if sha(Path(lean).read_bytes()) != result["runtime"]["lean_executable_sha256"]:
            raise RuntimeError("LEAN_BINARY_CHANGED")
        return 0
    except Exception as error:
        result["failure"] = type(error).__name__ + ": " + str(error)
        return 2
    finally:
        (output / "native.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    sys.exit(main())
