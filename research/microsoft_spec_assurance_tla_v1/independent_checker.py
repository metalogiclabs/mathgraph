#!/usr/bin/env python3
"""Fail-closed, source-pinned adjudication of a *finite* TLA+ safety claim.

Deliberately separate from the native TLC producer. A green model check is not
proof of any property absent from the checked model configuration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

SOURCE_PIN = "53955cf52c9cbe417b2bde68ab72edf2b9096cfc"
TLC_SHA256 = "78f7e2c6bf9a8b65eda665a23e94431255587e0b43a834a4e2af1723562d9b4a"
SOURCE_FILES = {
    "README.md": "b2e9bf1e40eac6f6b46be646367f69df3f5a70de78d7ea36ea69b7b56da5fbb6",
    "LamportMutex.tla": "dfa726da541fb0515ad482c3b5ca82c81b6f54df6626c3b9edfcebedc2a9c05a",
    "MCLamportMutex.tla": "2ebf6f863f504f76cfcb4a3bc8228aae1c5a896e7f2f8d046f8ab763656ccca8",
    "MCLamportMutex.cfg": "b91d46fb0a2f3af22fa65147c4c971d5cb9e42d141f63ad9035aa30cad51d118",
    "manifest.json": "5329850a96e8264cf4d785fb08be7d98ca56707fce1e94deb80194f442c8fb5e",
}


class Withdrawn(Exception):
    pass


class Rejected(Exception):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def required(path: Path) -> bytes:
    if not path.is_file():
        raise Withdrawn(f"MISSING:{path.parent.name}/{path.name}")
    return path.read_bytes()


def insist(condition: bool, reason: str) -> None:
    if not condition:
        raise Rejected(reason)


def expected_variants(source: Path) -> dict[str, tuple[str, str, str]]:
    text = required(source / "LamportMutex.tla").decode("utf-8")
    cfg = required(source / "MCLamportMutex.cfg").decode("utf-8")
    wrapper = required(source / "MCLamportMutex.tla").decode("utf-8")
    guards = "  /\\ \\A q \\in Proc \\ {p} : beats(p,q)\n"
    insist(text.count(guards) == 1, "MUTATION_TARGET_NOT_UNIQUE")
    mutant = text.replace(guards, "  /\\ TRUE\n")
    small = cfg.replace("N = 3", "N = 2").replace(
        "MaxNat = 7", "MaxNat = 4").replace("maxClock = 6", "maxClock = 3")
    insist(small != cfg, "FINITE_BOUND_CONTROL_MISSING")
    weak = small.replace("INVARIANTS TypeOK BoundedNetwork Mutex",
                         "INVARIANTS TypeOK BoundedNetwork")
    insist(weak != small, "MUTANT_WEAK_GATE_NOT_REMOVED")
    return {
        "author": (text, wrapper, cfg),
        "mutant_checked": (mutant, wrapper, small),
        "mutant_weakened": (mutant, wrapper, weak),
    }


def verify_native(folder: Path, model: str, wrapper: str, cfg: str,
                  *, expect: str) -> dict[str, object]:
    files = {
        "LamportMutex.tla": model.encode(),
        "MCLamportMutex.tla": wrapper.encode(),
        "MCLamportMutex.cfg": cfg.encode(),
    }
    observed = {}
    for name, content in files.items():
        raw = required(folder / name)
        insist(raw == content, f"{folder.name}:CASE_BYTES_MISMATCH:{name}")
        observed[name] = sha(raw)
    log_raw = required(folder / "tlc.log")
    exit_raw = required(folder / "tlc.exit")
    log = log_raw.decode("utf-8", errors="replace")
    observed["tlc.log"] = sha(log_raw)
    observed["tlc.exit"] = sha(exit_raw)
    insist(re.fullmatch(r"[0-9]+\n?", exit_raw.decode()) is not None,
           f"{folder.name}:BAD_EXIT_STATUS")
    rc = int(exit_raw.decode().strip())
    insist("TLC2 Version " in log and "Parsing file " in log,
           f"{folder.name}:NATIVE_INVOCATION_NOT_ESTABLISHED")
    if expect == "success":
        insist(rc == 0 and "Model checking completed. No error has been found." in log,
               f"{folder.name}:NATIVE_SUCCESS_MISSING")
        insist(" states generated, " in log and " distinct states found, " in log,
               f"{folder.name}:NO_STATE_ENUMERATION")
        insist("Error:" not in log, f"{folder.name}:UNEXPECTED_ERROR")
    else:
        insist(rc != 0, f"{folder.name}:FALSE_NEGATIVE_VERIFIER_EXIT")
        insist("Error: Invariant Mutex is violated." in log,
               f"{folder.name}:NO_MUTEX_COUNTEREXAMPLE")
        insist("State 1:" in log and "State 2:" in log,
               f"{folder.name}:NO_NATIVE_COUNTEREXAMPLE_TRACE")
        insist("/\\ crit = {1, 2}" in log or "/\\ crit = {2, 1}" in log,
               f"{folder.name}:NO_SIMULTANEOUS_CRITICAL_SECTION_WITNESS")
    return {"exit": rc, "bytes_sha256": observed}


def assess(source: Path, results: Path, source_revision: str,
           tool_sha256: str) -> dict[str, object]:
    if source_revision != SOURCE_PIN:
        return {"authority": "WITHDRAWN", "reason": "SOURCE_REVISION_DRIFT",
                "expected": SOURCE_PIN, "observed": source_revision}
    if tool_sha256 != TLC_SHA256:
        return {"authority": "REJECTED_EVIDENCE", "reason": "TOOL_BINARY_DRIFT"}
    try:
        for name, expected_digest in SOURCE_FILES.items():
            insist(sha(required(source / name)) == expected_digest,
                   f"AUTHOR_SOURCE_BYTES_CHANGED:{name}")
        source_text = required(source / "LamportMutex.tla").decode()
        source_readme = required(source / "README.md").decode()
        insist("The main safety property of mutual exclusion." in source_text
               and "Mutex == \\A p,q \\in crit : p = q" in source_text
               and "mutual exclusion" in source_readme.lower(),
               "SOURCE_CLAIM_NOT_BOUND")
        variants = expected_variants(source)
        native = {}
        for name, (model, wrapper, cfg) in variants.items():
            insist(("Mutex" in cfg.split("INVARIANTS", 1)[1].splitlines()[0])
                   == (name != "mutant_weakened"),
                   f"{name}:INVARIANT_CLAIM_WRONG_GATE")
            native[name] = verify_native(
                results / name, model, wrapper, cfg,
                expect="violation" if name == "mutant_checked" else "success")
        return {
            "protocol": "MATHGRAPH_SOURCE_BOUND_SPEC_ASSURANCE_TLA_V1",
            "authority": "WARRANTED_BOUNDED_AUTHOR_MODEL",
            "source": f"tlaplus/Examples@{SOURCE_PIN}",
            "source_bytes_sha256": SOURCE_FILES,
            "tool_sha256": TLC_SHA256,
            "author_scope": "FINITE_TLC_MODEL_INCLUDES_MUTEX",
            "mutant_checked": "FINITE_COUNTERMODEL",
            "mutant_weakened": "REJECTED_MISSING_MUTEX_GATE",
            "general_proof": False,
            "native": native,
            "limitations": [
                "Mutant is local and deliberately introduced, not an original upstream bug.",
                "Green TLC cannot authorize a property not selected as an invariant.",
                "Finite TLC enumeration is not a universal TLAPS proof or implementation refinement.",
                "A source-aware conventional checker can detect the same omission.",
                "This does not test Microsoft internal FoSSE agents or establish adoption.",
            ],
        }
    except Withdrawn as exc:
        return {"authority": "WITHDRAWN", "reason": str(exc)}
    except (Rejected, UnicodeError) as exc:
        return {"authority": "REJECTED_EVIDENCE", "reason": str(exc)}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path,
                   help="Pinned upstream specifications/lamport_mutex directory")
    p.add_argument("--results", required=True, type=Path)
    p.add_argument("--tool-jar", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    rev = subprocess.check_output(["git", "-C", str(args.source), "rev-parse", "HEAD"],
                                  text=True).strip()
    result = assess(args.source, args.results, rev, sha(required(args.tool_jar)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["authority"], result.get("reason", ""))
    if result["authority"] != "WARRANTED_BOUNDED_AUTHOR_MODEL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
