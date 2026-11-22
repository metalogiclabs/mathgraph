"""Run the existing artifact assessor locally and preserve precise run identity.

The imported assessor is unchanged source from MathGraph PR 282. Its original
result label describes its historical CI location; this wrapper replaces that
label with this actual local execution context. No owner authority is inferred.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def assess(method: Path, out: Path, monitor: Path) -> dict:
    spec = importlib.util.spec_from_file_location("original_assessor", method / "qualify_native.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    result = module.validate_report(out, monitor)
    result["independent_replay"] = "LOCAL_SEPARATE_PROCESS_AFTER_NATIVE_REBUILD"
    result["execution_boundary"] = "Same agent and machine; separate process and direct oracle, not an independent institution"
    cases = (("challenger.bin", "BINARY_CHANGED"),
             ("challenger.c2po", "SPEC_CHANGED"),
             ("challenger.map", "MAP_CHANGED"),
             ("simultaneous.csv", "TRACE_DATA_CHANGED"),
             ("native-result.json", "EVIDENCE_ATTEMPTS_AUTHORITY_PROMOTION"))
    mutations = []
    for name, expected in cases:
        with tempfile.TemporaryDirectory(prefix="rocket-evidence-control-") as temp:
            working = Path(temp) / "artifact"
            shutil.copytree(out, working)
            target = working / name
            if name == "native-result.json":
                document = json.loads(target.read_text())
                document["owner_approved"] = True
                target.write_text(json.dumps(document))
            elif name == "simultaneous.csv":
                target.write_text(target.read_text().replace("1,1\n", "1,0\n", 1))
            else:
                target.write_bytes(target.read_bytes() + b"changed")
            try:
                module.validate_report(working, monitor)
            except ValueError as error:
                actual = str(error)
                if actual != expected:
                    raise AssertionError((name, actual, expected))
            else:
                raise AssertionError("MUTATED_EVIDENCE_ADMITTED: " + name)
            mutations.append({"target": name, "expected_refusal": expected, "observed_refusal": actual})
    result["actual_artifact_mutations"] = mutations

    # An additional causal control: requiring a later COAST observation does not
    # forbid COAST at the trigger tick as well. This was not in the historical
    # four-scenario qualification. Report it separately as 16 new native values.
    rows = [(1, 1), (0, 1)] + [(0, 0)] * 6
    csv = "# BOOST, COAST\n" + "".join(f"{b},{c}\n" for b, c in rows)
    (out / "overlap_and_later.csv").write_text(csv)
    extra = []
    for variant, lower in (("source", 0), ("challenger", 1)):
        process = subprocess.run([str(monitor), str(out / (variant + ".bin"))],
                                 input=csv, text=True, capture_output=True, check=True, timeout=45)
        (out / ("overlap_and_later." + variant + ".stdout")).write_text(process.stdout)
        (out / ("overlap_and_later." + variant + ".stderr")).write_text(process.stderr)
        decoded = {}
        next_tick = 0
        for line in process.stdout.splitlines():
            import re
            match = re.fullmatch(r"0:([0-9]+),([TF])", line)
            if match is None:
                raise AssertionError("INVALID_ADDITIONAL_VERDICT: " + line)
            end = int(match[1])
            if not next_tick <= end < 8:
                raise AssertionError("INVALID_ADDITIONAL_HORIZON")
            decoded.update({t: match[2] == "T" for t in range(next_tick, end + 1)})
            next_tick = end + 1
        expected = {t: not bool(rows[t][0]) or any(c for b, c in rows[t + lower:min(t + 8, 8)])
                    for t in range(8)}
        if decoded != expected:
            raise AssertionError((variant, decoded, expected))
        extra.append({"variant": variant, "native": [decoded[t] for t in range(8)],
                      "expected": [expected[t] for t in range(8)]})
    if [row["native"][0] for row in extra] != [True, True]:
        raise AssertionError("OVERLAP_CONTROL_NOT_OBSERVED")
    result["additional_overlap_control"] = {
        "status": "WARRANTED_BOUNDED_FRESH_NATIVE",
        "positions": 16,
        "trace": [{"BOOST": b, "COAST": c} for b, c in rows],
        "observations": extra,
        "conclusion": "The constructed [1,7] response requires later COAST but does not prohibit simultaneous BOOST and COAST.",
        "historical_64_positions": "Separate; do not count this as a historical fifth scenario."
    }
    (out / "local-requalification.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--monitor", type=Path, required=True)
    args = parser.parse_args()
    result = assess(args.method.resolve(), args.out.resolve(), args.monitor.resolve())
    print(json.dumps({"replayed_positions": result["positions"],
                      "artifact_mutations_refused": len(result["actual_artifact_mutations"]),
                      "additional_overlap_positions": result["additional_overlap_control"]["positions"],
                      "operational_intent": result["intent_status"]}, sort_keys=True))
