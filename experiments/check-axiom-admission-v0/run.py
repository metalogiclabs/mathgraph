#!/usr/bin/env python3
"""Bounded Lean axiom-admission experiment. Not yet a catalogue profile.

Runs Lean on exact frozen source fixtures and inspects Lean's #print axioms
output for a named declaration. This is an experimental evidence boundary:
Lean's own reporting is trusted; independent kernel replay is NOT claimed.
"""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

CASES = {
    "benign": ("theorem target : True := True.intro\n", set()),
    "declared": ("axiom permitted : True\ntheorem target : True := permitted\n", {"permitted"}),
    "private": ("private axiom hidden : False\ntheorem target : False := hidden\n", None),
    "repaired": ("theorem target : True := True.intro\n", set()),
    "withdrawn": ("private axiom hidden : False\ntheorem target : False := hidden\n", None),
}
AXIOM_LINE = re.compile(r"^target\s+depends on axioms:\s*\[(.*)\]\s*$")
NO_AXIOMS = re.compile(r"^target\s+does not depend on any axioms\s*$")


def inspect(stdout):
    lines = [line.strip() for line in stdout.splitlines()]
    if any(NO_AXIOMS.fullmatch(line) for line in lines):
        return set()
    matches = [AXIOM_LINE.fullmatch(line) for line in lines]
    matches = [m for m in matches if m]
    if len(matches) != 1:
        raise ValueError("AXIOM_OUTPUT_UNRECOGNIZED")
    raw = matches[0].group(1).strip()
    names = [x.strip() for x in raw.split(",")] if raw else []
    if not names or any(not re.fullmatch(r"[\w.']+", n) for n in names):
        raise ValueError("AXIOM_OUTPUT_MALFORMED")
    return set(names)


def run_case(lean, name, timeout):
    source, allowed = CASES[name]
    text = source + "#print axioms target\n"
    with tempfile.TemporaryDirectory(prefix="mathgraph-axiom-") as tmp:
        path = Path(tmp) / "Witness.lean"
        path.write_text(text)
        try:
            p = subprocess.run([lean, str(path)], capture_output=True, text=True,
                               timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as e:
            return {"case": name, "status": "UNKNOWN", "reason": type(e).__name__,
                    "source_sha256": hashlib.sha256(text.encode()).hexdigest()}
    result = {"case": name, "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
              "exit_code": p.returncode, "stdout_sha256": hashlib.sha256(p.stdout.encode()).hexdigest(),
              "stderr_sha256": hashlib.sha256(p.stderr.encode()).hexdigest()}
    if p.returncode != 0:
        return {**result, "status": "UNKNOWN", "reason": "LEAN_EXECUTION_FAILED"}
    try:
        actual = inspect(p.stdout)
    except ValueError as e:
        return {**result, "status": "UNKNOWN", "reason": str(e)}
    result["observed_axioms"] = sorted(actual)
    result["stdout"] = p.stdout
    result["stderr"] = p.stderr
    # Private Lean declarations receive mangled internal names. No substring
    # or guessed name is accepted as a proof of absence.
    if allowed is None:
        result["status"] = "OBSERVED_MISMATCH" if actual else "UNKNOWN"
        result["reason"] = "UNAUTHORIZED_AXIOM_DEPENDENCY" if actual else "PRIVATE_AXIOM_NOT_OBSERVED"
    else:
        result["status"] = "OBSERVED_AGREEMENT" if actual == allowed else "OBSERVED_MISMATCH"
        result["reason"] = None if actual == allowed else "DECLARED_AXIOM_SET_DISAGREES"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lean", default="lean")
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 600:
        parser.error("timeout must be between 1 and 600 seconds")
    out = Path(args.out)
    if out.exists():
        parser.error("output path must not exist")
    out.mkdir(parents=True)
    try:
        tool = subprocess.run([args.lean, "--version"], capture_output=True, text=True,
                              timeout=args.timeout, check=False)
        toolchain = {"exit_code": tool.returncode, "stdout": tool.stdout, "stderr": tool.stderr}
    except (OSError, subprocess.TimeoutExpired) as e:
        toolchain = {"error": type(e).__name__}
    rows = [run_case(args.lean, name, args.timeout) for name in CASES]
    expected = {"benign": "OBSERVED_AGREEMENT", "declared": "OBSERVED_AGREEMENT",
                "private": "OBSERVED_MISMATCH", "repaired": "OBSERVED_AGREEMENT",
                "withdrawn": "OBSERVED_MISMATCH"}
    complete = toolchain.get("exit_code") == 0 and "4.35.0" in toolchain.get("stdout", "") and all(r["status"] == expected[r["case"]] for r in rows)
    result = {"schema": "mathgraph.axiom-admission-experiment.v0",
              "status": "CANDIDATE_CONTROL_PASS" if complete else "UNKNOWN_OR_CONTROL_FAILURE",
              "boundary": "Lean #print axioms on five fixed standalone fixtures; not independent kernel checking",
              "toolchain": toolchain, "cases": rows}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "out": str(out)}))
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
