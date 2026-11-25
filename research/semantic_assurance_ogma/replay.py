"""Exact historical C artifacts -> fresh bounded native evidence -> existing resolver.

This is an isolated research adapter. It does not change production code, enter
claims in the terminal-form kernel, or confer requirement/deployment authority.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from itertools import product
import json
from pathlib import Path
import platform
import re
import struct
import subprocess
import sys
import time
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from mathgraph_check.warrant_resolution import (  # noqa: E402
    Claim, QualifiedRelation, Receipt, Route, resolve_graph,
)

HERE = Path(__file__).resolve().parent
WARRANTED = "WARRANTED_BOUNDED"
UNKNOWN = "UNKNOWN"
REJECTED = "REJECTED_TRANSFER"
CLAIM = "finite_native_callbacks"


def load_protocol():
    payload = (HERE / "protocol.json").read_bytes()
    if sha256(payload).hexdigest() != (HERE / "protocol.sha256").read_text().strip():
        raise ValueError("PROTOCOL_CHANGED")
    return json.loads(payload)


def check_source(payload, p):
    if sha256(payload).hexdigest() != p["source_sha256"]:
        raise ValueError("SOURCE_IDENTITY")
    records = [r for r in json.loads(payload)["requirements"]
               if r["reqid"] == p["requirement_id"]]
    if len(records) != 1:
        raise ValueError("SOURCE_REQUIREMENT_ROSTER")
    r = records[0]
    # Restricted, explicit source language, independently of generated C/HS.
    parsed = re.fullmatch(r"The vehicle shall always satisfy (\w+) >= (\d+\.\d+)",
                          r["fulltext"])
    if (not parsed or parsed.groups() != ("kias", "0.0")
            or r["fulltext"] != p["fulltext"]
            or r["semantics"]["CoCoSpecCode"] != p["source_formula"]
            or r["semantics"]["timing"] != "always"):
        raise ValueError("UNSUPPORTED_SOURCE_MEANING")
    return r


def check_archive(payload, variant, p, source_record):
    v = p["variants"][variant]
    if sha256(payload).hexdigest() != v["archive_sha256"]:
        raise ValueError("ARCHIVE_IDENTITY")
    with ZipFile(BytesIO(payload)) as z:
        if z.testzip() is not None:
            raise ValueError("ARCHIVE_CRC")
        full = z.read("method/method-full-project.json")
        assigned = z.read("derived/047-assigned-control.json")
        original = json.loads(z.read("derived/047-original.json"))
        if (sha256(full).hexdigest() != p["method_export_sha256"]
                or sha256(assigned).hexdigest() != p["assigned_control_sha256"]):
            raise ValueError("DERIVED_INPUT_IDENTITY")
        requirement = original["vehicleSpec"]["Requirements"]
        if (len(requirement) != 1 or requirement[0]["name"] != source_record["reqid"]
                or requirement[0]["fretish"] != source_record["fulltext"]
                or requirement[0]["CoCoSpecCode"] != p["source_formula"]):
            raise ValueError("SOURCE_EXPORT_CORRESPONDENCE")
        expected = deepcopy(original)
        for record in expected["vehicleSpec"]["Internal_variables"]:
            if record["assignmentCopilot"] != "":
                raise ValueError("ORIGINAL_ASSIGNMENT_SCOPE")
            record["assignmentCopilot"] = record["assignmentLustre"]
        if expected != json.loads(assigned):
            raise ValueError("UNAUTHORIZED_DERIVATION")
        files = {n: z.read(v["prefix"] + n)
                 for n in ("monitor.c", "monitor.h", "monitor_types.h", "Copilot.hs")}
        if sha256(files["monitor.c"]).hexdigest() != v["monitor_sha256"]:
            raise ValueError("MONITOR_IDENTITY")
    return files


def traces(p):
    return [list(xs) for n in p["domain"]["lengths"]
            for xs in product(p["domain"]["tokens"], repeat=n)]


def expected_counts(xs):
    # Recurrence oracle, not extracted from monitor.c or Copilot.hs.
    holds = True
    total = 0
    counts = []
    for token in xs:
        holds = holds and float.fromhex(token) >= 0.0
        total += not holds
        counts.append(total)
    return counts


def prefix_matches(table):
    """Independent prefix formulation, checked once during shared qualification."""
    return all(row["callbacks"] == [sum(
        any(float.fromhex(x) < 0.0 for x in row["trace"][:j])
        for j in range(1, i + 1)) for i in range(1, len(row["trace"]) + 1)]
        for row in table)


def input_bits(xs):
    return [struct.pack(">f", float.fromhex(x)).hex() for x in xs]


def run_native(executable, xs):
    result = subprocess.run([str(executable), *xs], check=True,
                            capture_output=True, text=True, timeout=5)
    rows = [line.split() for line in result.stdout.splitlines()]
    if len(rows) != len(xs) or any(len(row) != 2 for row in rows):
        raise ValueError("NATIVE_OUTPUT_SHAPE")
    bits = [row[0] for row in rows]
    counts = [int(row[1]) for row in rows]
    if bits != input_bits(xs):
        raise ValueError("NATIVE_INPUT_ENCODING")
    return {"trace": xs, "bits": bits, "callbacks": counts}


def verify_table(table, executable, p, counter=None):
    """Reexecute every certificate row; a self-hash cannot qualify a table."""
    roster = traces(p)
    if len(table) != len(roster) or [r.get("trace") for r in table] != roster:
        return False
    for row, xs in zip(table, roster):
        if counter is not None:
            counter["verification_native_processes"] += 1
        if row != run_native(executable, xs):
            return False
    return True


def graph_decisions(facts, p, withdrawn=frozenset(), *, source_ok=True,
                    domain=None, claim=CLAIM):
    if (claim != CLAIM or (domain is not None and domain != p["domain"])):
        return {name: UNKNOWN for name in facts}, {}
    source_scope = p["source_sha256"]
    claims = [Claim("source", "documentary", source_scope)]
    receipts = [Receipt("source", "documentary", source_scope)]
    routes = [Route("source", ("source",))] if source_ok else []
    relations = []
    for name, fact in facts.items():
        scope = sha256(json.dumps([p["domain"], p["variants"][name]["monitor_sha256"],
                                   p["source_sha256"]], sort_keys=True).encode()).hexdigest()
        for suffix in ("native", "match", "mismatch", "deployment"):
            claims.append(Claim(f"{name}:{suffix}", "formal", scope))
        for suffix in ("monitor", "native", "verifier"):
            receipts.append(Receipt(f"{name}:{suffix}", "formal", scope))
        if not fact["qualified"]:
            continue
        routes.append(Route(f"{name}:native", tuple(f"{name}:{s}"
                                                  for s in ("monitor", "native", "verifier"))))
        dest = f"{name}:" + ("match" if fact["matches"] else "mismatch")
        relation_id = f"bridge:{dest}"
        route = Route(dest, ("source", f"{name}:monitor", f"{name}:native"),
                      ("source",), relation_id)
        routes.append(route)
        relations.append(QualifiedRelation(relation_id, "documentary", source_scope,
                         "formal", scope, f"{name}:verifier", (f"{name}:native",), route))
    result = resolve_graph(claims, routes, receipts, relations=relations, withdrawn=withdrawn)
    decisions = {n: WARRANTED if result.states[f"{n}:match"] == WARRANTED else
                 REJECTED if result.states[f"{n}:mismatch"] == WARRANTED else UNKNOWN
                 for n in facts}
    return decisions, dict(result.states)


def ledger_decisions(facts, tables, p, withdrawn=frozenset(), *, source_ok=True,
                     domain=None, claim=CLAIM):
    """Direct equally informed rule over qualified facts; no graph calls.

    Prefix and recurrence oracles are independently checked during shared
    acquisition. Both decision arms may reuse the resulting qualified fact.
    """
    decisions = {}
    for name, fact in facts.items():
        dependencies = {"source", *(f"{name}:{s}" for s in ("monitor", "native", "verifier"))}
        if (not source_ok or not fact["qualified"] or dependencies & withdrawn
                or claim != CLAIM or (domain is not None and domain != p["domain"])):
            decisions[name] = UNKNOWN
            continue
        decisions[name] = WARRANTED if fact["matches"] else REJECTED
    return decisions


def checked_error(fn):
    try:
        fn()
    except (ValueError, KeyError, TypeError):
        return True
    return False


def run(inputs, out):
    p = load_protocol()
    out.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    source = (inputs / "LPC_full_reqts_and_vars.json").read_bytes()
    record = check_source(source, p)
    trace_roster = traces(p)
    facts, tables, executables, metrics = {}, {}, {}, {}
    budget = {"source_files_read": 1, "native_archives_read": 2, "native_compilations": 2,
              "capture_native_processes": 0, "verification_native_processes": 0}
    for name, v in p["variants"].items():
        files = check_archive((inputs / v["archive"]).read_bytes(), name, p, record)
        directory = out / name
        directory.mkdir(exist_ok=True)
        for filename, payload in files.items():
            (directory / filename).write_bytes(payload)
        executable = (directory / "native-replay").resolve()
        subprocess.run(["gcc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-pedantic",
                        "-I", str(directory), str(HERE / "native_reader.c"),
                        str(directory / "monitor.c"), "-o", str(executable)], check=True)
        executables[name] = executable
        table = [run_native(executable, xs) for xs in trace_roster]
        budget["capture_native_processes"] += len(trace_roster)
        if not verify_table(table, executable, p, budget):
            raise ValueError("CERTIFICATE_REPLAY_FAILED")
        bad = [row for row in table if row["callbacks"] != expected_counts(row["trace"])]
        if prefix_matches(table) != (not bad):
            raise ValueError("INDEPENDENT_ORACLE_DISAGREEMENT")
        tables[name] = table
        facts[name] = {"qualified": True, "matches": not bad}
        metrics[name] = {
            "traces": len(table), "sample_steps": sum(map(len, trace_roster)),
            "mismatching_traces": len(bad),
            "mismatching_steps": sum(sum(a != b for a, b in zip(row["callbacks"],
                                       expected_counts(row["trace"]))) for row in table),
            "first_counterexample": ({**bad[0], "expected": expected_counts(bad[0]["trace"])}
                                     if bad else None),
            "monitor_sha256": sha256(files["monitor.c"]).hexdigest(),
            "executable_sha256": sha256(executable.read_bytes()).hexdigest(),
        }
        (directory / "certificate.json").write_text(json.dumps(table, separators=(",", ":")) + "\n")
    acquisition_seconds = time.perf_counter() - start
    controls_start = time.perf_counter()
    control_budget = {"verification_native_processes": 0}
    controls = []

    def compare(label, expected, *, f=None, **options):
        admitted = facts if f is None else f
        graph, states = graph_decisions(admitted, p, **options)
        ledger = ledger_decisions(admitted, tables, p, **options)
        if graph != expected or ledger != expected:
            raise AssertionError((label, graph, ledger, expected))
        if states:
            assert states["unpatched:deployment"] == states["patched:deployment"] == UNKNOWN
        controls.append({"control": label, "gate": graph, "ledger": ledger, "passed": True})
        return states

    baseline = {"unpatched": REJECTED, "patched": WARRANTED}
    states = compare("baseline", baseline)
    assert states["unpatched:native"] == states["patched:native"] == WARRANTED
    compare("source_withdrawal", dict.fromkeys(facts, UNKNOWN), withdrawn=frozenset({"source"}))
    for name in ("patched", "unpatched"):
        expected = {**baseline, name: UNKNOWN}
        compare(f"{name}_monitor_withdrawal", expected, withdrawn=frozenset({f"{name}:monitor"}))
    for suffix, label in [("verifier", "patched_verifier_withdrawal"),
                          ("native", "patched_native_evidence_withdrawal")]:
        compare(label, {**baseline, "patched": UNKNOWN}, withdrawn=frozenset({f"patched:{suffix}"}))
    compare("reinstatement", baseline)
    assert checked_error(lambda: check_source(source + b"\n", p))
    compare("source_substitution", dict.fromkeys(facts, UNKNOWN), source_ok=False)
    # Replace only the C member in a copy, leaving all other historical members.
    patched_payload = (inputs / p["variants"]["patched"]["archive"]).read_bytes()
    unpatched_payload = (inputs / p["variants"]["unpatched"]["archive"]).read_bytes()
    tampered = BytesIO()
    with ZipFile(BytesIO(unpatched_payload)) as z:
        wrong_c = z.read(p["variants"]["unpatched"]["prefix"] + "monitor.c")
    with ZipFile(BytesIO(patched_payload)) as original, ZipFile(tampered, "w") as altered:
        for info in original.infolist():
            altered.writestr(info, wrong_c if info.filename == "native/monitor.c"
                             else original.read(info.filename))
    for label, bad_payload in [("archive_substitution", b"not the original artifact"),
                               ("monitor_substitution", tampered.getvalue())]:
        assert checked_error(lambda: check_archive(bad_payload, "patched", p, record))
        rejected = deepcopy(facts)
        rejected["patched"]["qualified"] = False
        compare(label, {**baseline, "patched": UNKNOWN}, f=rejected)
    for label in ("certificate_corruption", "certificate_row_withdrawal", "certificate_duplicate_row"):
        table = deepcopy(tables["patched"])
        if label == "certificate_corruption":
            table[0]["callbacks"][0] += 1
        elif label == "certificate_row_withdrawal":
            table.pop()
        else:
            table[-1] = deepcopy(table[0])
        assert not verify_table(table, executables["patched"], p, control_budget)
        rejected = deepcopy(facts)
        rejected["patched"]["qualified"] = False
        compare(label, {**baseline, "patched": UNKNOWN}, f=rejected)
    changed = deepcopy(p["domain"])
    changed["lengths"].append(5)
    compare("changed_domain", dict.fromkeys(facts, UNKNOWN), domain=changed)
    compare("changed_claim", dict.fromkeys(facts, UNKNOWN), claim="all_real_inputs")
    changed = deepcopy(p["domain"])
    changed["tokens"].append("nan")
    compare("nonfinite_input", dict.fromkeys(facts, UNKNOWN), domain=changed)
    compare("deployment_claim", dict.fromkeys(facts, UNKNOWN), claim="deployment_authorized")
    assert [c["control"] for c in controls[1:]] == p["controls"]
    controls_seconds = time.perf_counter() - controls_start
    # Only post-acquisition decision time: common acquisition is explicit.
    decision_seconds = {}
    for arm in ("gate", "ledger"):
        t = time.perf_counter()
        if arm == "gate":
            graph_decisions(facts, p)
        else:
            ledger_decisions(facts, tables, p)
        decision_seconds[arm] = time.perf_counter() - t
    report = {
        "status": "WARRANTED_BOUNDED_NATIVE_ADAPTER",
        "protocol_sha256": (HERE / "protocol.sha256").read_text().strip(),
        "requirement": {"id": record["reqid"], "fulltext": record["fulltext"],
                        "source_sha256": p["source_sha256"]},
        "baseline": baseline, "native": metrics, "controls": controls,
        "cost": {"shared_acquisition": budget, "shared_acquisition_seconds": acquisition_seconds,
                 "integrity_controls": control_budget, "integrity_controls_seconds": controls_seconds,
                 "post_acquisition_decision_seconds": decision_seconds,
                 "human_and_discovery_cost": "NOT_MEASURED"},
        "comparison": "TIE on all preregistered decisions; no architectural/economic superiority established",
        "qualification": "Fresh GCC compilation/reexecution of exact historically generated C; no fresh Haskell/Copilot regeneration; no Lean proof of this adapter",
        "scope": p["positive_boundary"], "source_caveat": p["source_caveat"],
        "host": {"platform": platform.platform(), "python": sys.version,
                 "gcc": subprocess.run(["gcc", "--version"], capture_output=True, text=True,
                                        check=True).stdout.splitlines()[0]},
    }
    (out / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("controls", "host")}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.inputs.resolve(), args.out.resolve())
