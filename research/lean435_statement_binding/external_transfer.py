#!/usr/bin/env python3
"""Source-derived formal claim identity transfer to an independent Lean repository.

One target *file*, no selected theorem name, statement text, or handwritten
source-to-claim mapping in this harness. All source authority is pinned before
the Lean proof is generated. Native checker observations decide the status.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
WORK = HERE / "external_mathlib"
EVIDENCE = HERE / "external_evidence"
WORK.mkdir(exist_ok=True)
EVIDENCE.mkdir(exist_ok=True)

SOURCE_REPO = "leanprover-community/mathlib4"
SOURCE_REVISION = "56a005855ea17e0b0958f73ec801ae140b0a1679"
SOURCE_MODULE = "Mathlib.Logic.Function.Defs"
SOURCE_RELATIVE_PATH = "Mathlib/Logic/Function/Defs.lean"
SOURCE_BLOB = "565ae3df6b95fa084d60818ab13fab2e80874f3f"
LEAN_VERSION = "4.35.0"
STEPS = []

def sha256(raw):
    return hashlib.sha256(raw).hexdigest()

def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\\0" + raw).hexdigest()

def run(label, argv, expected=0, diagnostic=None, cwd=WORK, timeout=850):
    t = time.monotonic()
    try:
        p = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True, errors="replace",
                           check=False, timeout=timeout)
        code, output = p.returncode, p.stdout
    except subprocess.TimeoutExpired as err:
        code, output = 124, str(err)
    data = ("$ " + " ".join(argv) + "\\n" + output).encode("utf-8")
    (EVIDENCE / (label + ".log")).write_bytes(data)
    item = {"label": label, "argv": argv, "code": code,
            "expected_code": expected, "diagnostic": diagnostic,
            "diagnostic_present": (diagnostic in output if diagnostic else None),
            "sha256": sha256(data), "elapsed_seconds": round(time.monotonic() - t, 3)}
    STEPS.append(item)
    print("STEP", json.dumps(item, sort_keys=True), flush=True)
    if code != expected:
        raise RuntimeError(f"{label}: expected exit {expected}, got {code}")
    if diagnostic is not None and diagnostic not in output:
        raise RuntimeError(f"{label}: missing expected diagnostic {diagnostic}")
    return output

def make_environment():
    (WORK / "lean-toolchain").write_text(
        "leanprover/lean4:v4.35.0\\n", encoding="utf-8")
    (WORK / "lakefile.toml").write_text(
        'name = "mathgraph_external_mathlib_binding"\\n'
        'version = "0.1.0"\\n'
        '[[require]]\\n'
        'name = "mathlib"\\n'
        'git = "https://github.com/leanprover-community/mathlib4.git"\\n'
        f'rev = "{SOURCE_REVISION}"\\n', encoding="utf-8")

def discover_first_source_theorem(raw):
    """A file-scoped syntactic selector, never a configured theorem mapping."""
    ns = []
    for line in raw.decode("utf-8").splitlines():
        m = re.match(r"^namespace\\s+([A-Za-z_][A-Za-z_0-9.]*)\\s*$", line)
        if m:
            ns.extend(m.group(1).split("."))
            continue
        m = re.match(r"^end(?:\\s+([A-Za-z_][A-Za-z_0-9.]*))?\\s*$", line)
        if m and ns:
            ns.pop()
            continue
        m = re.match(r"^\\s*(?:theorem|lemma)\\s+([A-Za-z_][A-Za-z_0-9']*)\\b", line)
        if m:
            leaf = m.group(1)
            if not ns:
                raise RuntimeError("UNSCOPED_FIRST_THEOREM_NEEDS_EXPLICIT_LEXICAL_SUPPORT")
            return ".".join(ns + [leaf]), leaf
    raise RuntimeError("NO_SUPPORTED_SOURCE_THEOREM")

def generate_lean(name):
    # All occurrences of 'name' below are generated from pinned source bytes.
    honest = f"""import Lean
import {SOURCE_MODULE}

open Lean Elab Command

run_cmd do
  let originName : Lean.Name := ``{name}
  let some (.thmInfo source) := (← getEnv).find? originName
    | throwError "SOURCE_THEOREM_NOT_FOUND"
  let levels := source.levelParams.map Lean.Level.param
  addDecl <| Lean.Declaration.thmDecl {{
    name := `MathGraphImported.checked
    levelParams := source.levelParams
    type := source.type
    value := Lean.mkConst originName levels
  }}
  let some candidate := (← getEnv).find? `MathGraphImported.checked
    | throwError "NEW_CANDIDATE_NOT_FOUND"
  let same ← liftTermElabM <| Lean.Meta.isDefEq source.type candidate.type
  unless same do
    throwError "SOURCE_STATEMENT_MISMATCH"
  logInfo "SOURCE_STATEMENT_MATCH"
"""
    forged = f"""import Lean
import {SOURCE_MODULE}

theorem MathGraphImported.checked : True := True.intro

open Lean Elab Command

run_cmd do
  let originName : Lean.Name := ``{name}
  let some (.thmInfo source) := (← getEnv).find? originName
    | throwError "SOURCE_THEOREM_NOT_FOUND"
  let some candidate := (← getEnv).find? `MathGraphImported.checked
    | throwError "NEW_CANDIDATE_NOT_FOUND"
  let same ← liftTermElabM <| Lean.Meta.isDefEq source.type candidate.type
  unless same do
    throwError "SOURCE_STATEMENT_MISMATCH"
  logInfo "SOURCE_STATEMENT_MATCH"
"""
    harmless = f"""import {SOURCE_MODULE}

theorem MathGraphImported.checked : True := True.intro
"""
    (WORK / "SourceHonest.lean").write_text(honest, encoding="utf-8")
    (WORK / "SourceForged.lean").write_text(forged, encoding="utf-8")
    (WORK / "ForgeryCompiles.lean").write_text(harmless, encoding="utf-8")

def main():
    evidence = {"schema": "mathgraph.native-mathlib-source-identity-transfer.v1",
                "status": "UNKNOWN", "error": None, "steps": STEPS,
                "source": {"repository": SOURCE_REPO,
                           "expected_commit": SOURCE_REVISION,
                           "module": SOURCE_MODULE,
                           "file": SOURCE_RELATIVE_PATH,
                           "expected_git_blob": SOURCE_BLOB},
                "selection": None,
                "experiment_scope": "one newly selected native Mathlib source theorem; reuse only",
                "exclusions": [
                    "novel theorem", "new proof discovery", "English fidelity",
                    "arbitrary Lean grammar", "all Mathlib", "independent checker consortium",
                    "automatic cross-repo production admission", "generic source mapping proof"
                ]}
    try:
        run("version", ["lean", "--version"], diagnostic=LEAN_VERSION)
        make_environment()
        run("lake_update", ["lake", "update"], timeout=550)
        mathlib_path = WORK / ".lake" / "packages" / "mathlib"
        sha = run("source_commit", ["git", "rev-parse", "HEAD"],
                  cwd=mathlib_path).strip().splitlines()[-1]
        if sha != SOURCE_REVISION:
            raise RuntimeError("SOURCE_COMMIT_MISMATCH")
        toolchain = (mathlib_path / "lean-toolchain").read_text().strip()
        if toolchain != "leanprover/lean4:v4.35.0":
            raise RuntimeError("SOURCE_TOOLCHAIN_MISMATCH")
        original = (mathlib_path / SOURCE_RELATIVE_PATH).read_bytes()
        if git_blob(original) != SOURCE_BLOB:
            raise RuntimeError("SOURCE_GIT_BLOB_MISMATCH")
        if git_blob(original + b"\\n") == SOURCE_BLOB:
            raise RuntimeError("MUTATION_NOT_DETECTED")
        source_name, leaf = discover_first_source_theorem(original)
        evidence["selection"] = {"discovered_name": source_name,
                                  "source_sha256": sha256(original),
                                  "selection_rule": "first syntactically scoped theorem/lemma",
                                  "source_bytes_modified": False,
                                  "mutated_git_blob": git_blob(original + b"\\n")}
        print("SELECTED_SOURCE", source_name, flush=True)
        generate_lean(source_name)
        run("mathlib_module_cache",
            ["lake", "exe", "cache", "get", SOURCE_MODULE], timeout=800)
        run("native_module_build", ["lake", "build", SOURCE_MODULE], timeout=600)
        run("honest_source_proof",
            ["lake", "env", "lean", "SourceHonest.lean"],
            diagnostic="SOURCE_STATEMENT_MATCH", timeout=180)
        run("valid_but_unbound_proof",
            ["lake", "env", "lean", "ForgeryCompiles.lean"], timeout=180)
        run("forged_source_binding",
            ["lake", "env", "lean", "SourceForged.lean"],
            expected=1, diagnostic="SOURCE_STATEMENT_MISMATCH", timeout=180)
        evidence["status"] = "WARRANTED_BOUNDED_NATIVE_EXTERNAL_SOURCE_BINDING"
    except Exception as error:
        evidence["error"] = str(error)
    finally:
        evidence["source_under_test"] = os.environ.get("GITHUB_HEAD_SHA",
                                                      os.environ.get("GITHUB_SHA", "LOCAL"))
        (EVIDENCE / "report.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\\n",
            encoding="utf-8")
        print("FINAL", json.dumps({"status": evidence["status"],
                                   "error": evidence["error"],
                                   "selection": evidence["selection"]}), flush=True)
    return int(evidence["status"] !=
               "WARRANTED_BOUNDED_NATIVE_EXTERNAL_SOURCE_BINDING")

if __name__ == "__main__":
    sys.exit(main())
