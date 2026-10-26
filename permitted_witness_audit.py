"""Source-native permissions and obstruction audit for the public observation lab.

The UI's finite solver is not a test receipt. This independent native replay
validates its controlled examples against pinned upstream source and the
original declared mutant family. It is NOT a general-program correctness proof.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from upstream_encoding_transfer import (
    ENCODING_PATH, MUTANTS, UPSTREAM_COMMIT, call_native_code, copy_package,
    digest, domain, independent_minimum_bound, minimum_separator, mutate,
    oracle, pinned_source,
)

SCENARIOS = {
    "all_permitted": (1, 2, 3),
    "one_byte_forbidden": (2, 3),
    "only_three_byte": (3,),
    "only_one_byte": (1,),
    "no_probes": (),
}

def permission_audit(checkout: Path) -> dict:
    pins = pinned_source(checkout)
    original = (checkout / ENCODING_PATH).read_bytes()
    all_inputs = domain()
    observations = {}
    with TemporaryDirectory(prefix="mathgraph-observation-permission-") as tmp:
        base = Path(tmp)
        for name in ("reference",) + tuple(sorted(MUTANTS)):
            folder = base / name
            folder.mkdir()
            candidate = original if name == "reference" else mutate(original, name)
            copy_package(checkout, folder, candidate)
            observations[name] = call_native_code(folder, all_inputs)
    if observations["reference"] != [oracle(x) for x in all_inputs]:
        raise AssertionError("PINNED_NATIVE_ORACLE_DISAGREEMENT")

    # Deliberately exclude lengths outside 1,2,3 from this permission
    # grammar. Some longer control inputs actually distinguish some mutants:
    # that is why the permissible-input scope must be stated precisely.
    controls = [v for v in all_inputs if len(v) not in (1,2,3)]
    if len(controls) != 3:
        raise AssertionError("FROZEN_CONTROL_SCOPE_CHANGED")

    scenarios = {}
    for name, lengths in SCENARIOS.items():
        positions = [i for i,v in enumerate(all_inputs) if len(v) in lengths]
        inputs = tuple(all_inputs[i] for i in positions)
        observed = {key: [values[i] for i in positions]
                    for key, values in observations.items()}
        solution = minimum_separator(inputs, observed)
        checked_cost = independent_minimum_bound(solution["cover_records"])
        if solution["status"] == "MINIMUM_BASIS":
            if checked_cost != solution["total_synthetic_cost"]:
                raise AssertionError("INDEPENDENT_MINIMUM_DISAGREEMENT")
        elif solution["status"] == "OBSTRUCTION":
            if checked_cost is not None:
                raise AssertionError("SPURIOUS_OBSTRUCTION")
        else:
            raise AssertionError("UNKNOWN_FINITE_VERDICT")
        scenarios[name] = {
            "permitted_lengths": list(lengths),
            "eligible_inputs": len(inputs),
            "status": solution["status"],
            "tests_hex": solution["tests_hex"],
            "total_synthetic_cost": solution["total_synthetic_cost"],
            "unsplittable": solution["unsplittable"],
            "independent_minimum_cost": checked_cost,
        }

    if (scenarios["all_permitted"]["tests_hex"] != ["00", "f80000"]
        or scenarios["all_permitted"]["total_synthetic_cost"] != 6):
        raise AssertionError("UNRESTRICTED_UI_ORACLE_MISMATCH")
    if (scenarios["one_byte_forbidden"]["tests_hex"] != ["0000", "f80000"]
        or scenarios["one_byte_forbidden"]["total_synthetic_cost"] != 7):
        raise AssertionError("RESTRICTED_UI_ORACLE_MISMATCH")
    if (scenarios["only_three_byte"]["status"] != "OBSTRUCTION"
        or scenarios["only_three_byte"]["unsplittable"] != ["unstripped_padding"]):
        raise AssertionError("DECLARED_OBSTRUCTION_NOT_REPRODUCED")

    return {
        "schema": "mathgraph.permission-observations.native-v1",
        "scope": "bounded three-mutant encoding grammar and exact source-native replay",
        "source": {"repository": "pallets/itsdangerous",
                   "commit": UPSTREAM_COMMIT,
                   "original_encoding_sha256": digest(original),
                   "file_evidence": pins},
        "full_domain_size": len(all_inputs),
        "observation_grammar": "only input lengths 1,2,3 may be selected",
        "excluded_controls_hex": [v.hex() for v in controls],
        "cost": "synthetic 1 + input byte length",
        "scenarios": scenarios,
        "model_inference": "NOT_PERFORMED",
        "source_mutations": "deliberately-injected-isolated-copies",
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--upstream-checkout", type=Path, required=True)
    p.add_argument("--report", type=Path,
                   default=Path("permitted-witness-report.json"))
    args = p.parse_args()
    result = permission_audit(args.upstream_checkout.resolve())
    args.report.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result["scenarios"], indent=2))

if __name__ == "__main__":
    main()
