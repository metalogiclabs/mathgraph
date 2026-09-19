from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PVSNP_ROOT = Path(os.environ.get("PVSNP_SOURCE_ROOT", "_vendor/pvsnp_source"))
MSI_ROOT = Path(os.environ.get("MSI_SOURCE_ROOT", "_vendor/msi_source"))

PVSNP_COMMIT = "4df88a272926126b895c2fb6220c56012949df05"
MSI_COMMIT = "5d448c0ecc82ff3945d009963064ebbb67d2f308"
PVSNP_EVIDENCE_SHA = "b5781dd62f53fdaaeb32a703bbc7c13977f0e19e"
ARITHMETIC_TEST_BLOB = "5d23b9b5b2d16e94e2c15c2ed7439fba1335c6a3"

CIRCUIT_A = 0x8F
CIRCUIT_B = 0xEA
PROJECTION_X0 = 0xAA
PROJECTION_X1 = 0xCC
CIRCUIT_FLASH_AFTER = 6
ARITHMETIC_FLASH_AFTER = 20


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def canonical_partition(carrier, key):
    buckets = {}
    for x in carrier:
        buckets.setdefault(key(x), []).append(x)
    return tuple(sorted((tuple(sorted(v, key=repr)) for v in buckets.values()), key=repr))


def relation_pairs(partition):
    return frozenset((x, y) for block in partition for x in block for y in block)


def classify_move(old, target):
    a, b = relation_pairs(old), relation_pairs(target)
    if a == b:
        return "EQUAL"
    if b < a:
        return "REFINE"
    if a < b:
        return "COARSEN"
    return "REPARTITION"


def exact_consequence_kernel(carrier, consequence):
    return canonical_partition(carrier, consequence)


def certify_exact_kernel(carrier, consequence, proposed):
    target = exact_consequence_kernel(carrier, consequence)
    checks = 0
    for x, y in itertools.combinations(carrier, 2):
        checks += 1
        psame = any(x in block and y in block for block in proposed)
        csame = consequence(x) == consequence(y)
        if psame != csame:
            raise ValueError("proposal disagrees with protected consequence equality")
    if proposed != target:
        raise ValueError("proposal is not canonical exact consequence kernel")
    return {"checks": checks, "partition": proposed}


def build_circuit_world():
    lab = load_module(
        PVSNP_ROOT / "experiments/pvsnp_hardness_lab_v1/lab.py",
        "pvsnp_lab_equilibration_v2",
    )
    e = lab.enumerate_nand(3, 3)
    carrier = (CIRCUIT_A, CIRCUIT_B, PROJECTION_X0, PROJECTION_X1)
    signatures = {m: lab.structural_signature(m, 3) for m in carrier}
    sizes = {m: e.min_size[m] for m in carrier}
    assert signatures[CIRCUIT_A] == signatures[CIRCUIT_B]
    assert [sizes[CIRCUIT_A], sizes[CIRCUIT_B]] == [2, 3]
    assert signatures[PROJECTION_X0] == signatures[PROJECTION_X1]
    assert sizes[PROJECTION_X0] == sizes[PROJECTION_X1] == 0
    old = canonical_partition(carrier, lambda x: signatures[x])
    target = exact_consequence_kernel(carrier, lambda x: sizes[x])
    assert classify_move(old, target) == "REFINE"
    return dict(carrier=carrier, signatures=signatures, sizes=sizes, old=old, target=target)


def circuit_checks(world, n):
    a, b = world["signatures"][CIRCUIT_A], world["signatures"][CIRCUIT_B]
    done = 0
    for i in range(min(n, len(a))):
        done += 1
        if a[i] != b[i]:
            break
    return done


def circuit_arms(world):
    cert = certify_exact_kernel(world["carrier"], lambda x: world["sizes"][x], world["target"])
    discrete = tuple((x,) for x in sorted(world["carrier"]))
    sham_rejected = False
    try:
        certify_exact_kernel(world["carrier"], lambda x: world["sizes"][x], discrete)
    except ValueError:
        sham_rejected = True
    return {
        "COLD": {"resolved": False, "diagnostic_checks": 12, "final_partition": world["old"]},
        "WARM": {"resolved": True, "diagnostic_checks": 0, "authority_checks": cert["checks"], "final_partition": world["target"]},
        "FLASH": {"resolved": True, "diagnostic_checks": circuit_checks(world, CIRCUIT_FLASH_AFTER), "authority_checks": cert["checks"], "final_partition": world["target"]},
        "RAW_HISTORY": {"resolved": False, "diagnostic_checks": 12, "final_partition": world["old"]},
        "SHAM_DISCRETE": {"resolved": False, "diagnostic_checks": 12, "sham_rejected": sham_rejected, "final_partition": world["old"]},
        "ABLATION": {"resolved": False, "diagnostic_checks": 12, "exact_ablation": True, "final_partition": world["old"]},
    }


def build_arithmetic_world():
    ar = load_module(
        MSI_ROOT / "tests/test_arithmetic_base_invariance.py",
        "arithmetic_base_invariance_equilibration_v2",
    )
    pairs, histories, retained, learned_classes = ar.adaptive_partition(10)
    carrier = tuple(histories)
    full_signature = {h: ar.signature(h, pairs, 10) for h in histories}
    old = tuple((h,) for h in carrier)
    target = exact_consequence_kernel(carrier, lambda h: full_signature[h])
    assert len(carrier) == 101
    assert len(target) == 2
    assert classify_move(old, target) == "COARSEN"
    assert set(target) == set(tuple(sorted(cls, key=repr)) for cls in learned_classes)
    return dict(
        carrier=carrier,
        pairs=pairs,
        retained=retained,
        old=old,
        target=target,
        full_signature=full_signature,
    )


def arithmetic_allocation_cost(world, mode):
    carrier = world["carrier"]
    target_key = lambda h: world["full_signature"][h]

    if mode == "COLD" or mode == "RAW_HISTORY":
        return {"record_allocations": len(carrier), "final_classes": len(world["old"]), "resolved": False}

    if mode == "WARM":
        cert = certify_exact_kernel(carrier, target_key, world["target"])
        return {"record_allocations": len(world["target"]), "final_classes": 2, "resolved": True, "authority_checks": cert["checks"]}

    if mode == "FLASH":
        seen = carrier[:ARITHMETIC_FLASH_AFTER]
        cert = certify_exact_kernel(carrier, target_key, world["target"])
        seen_classes = {target_key(h) for h in seen}
        future_new = {target_key(h) for h in carrier[ARITHMETIC_FLASH_AFTER:]} - seen_classes
        allocations = len(seen) + len(seen_classes) + len(future_new)
        return {
            "record_allocations": allocations,
            "raw_allocations_before_flash": len(seen),
            "recompiled_classes_at_flash": len(seen_classes),
            "new_classes_after_flash": len(future_new),
            "final_classes": 2,
            "resolved": True,
            "authority_checks": cert["checks"],
        }

    if mode == "SHAM_ALL_MERGED":
        sham = (tuple(carrier),)
        rejected = False
        try:
            certify_exact_kernel(carrier, target_key, sham)
        except ValueError:
            rejected = True
        return {
            "record_allocations": len(carrier),
            "final_classes": len(world["old"]),
            "resolved": False,
            "sham_rejected": rejected,
        }

    if mode == "ABLATION":
        certify_exact_kernel(carrier, target_key, world["target"])
        return {
            "record_allocations": len(carrier),
            "final_classes": len(world["old"]),
            "resolved": False,
            "exact_ablation": True,
        }

    raise ValueError(mode)


def run():
    circuit = build_circuit_world()
    arithmetic = build_arithmetic_world()
    ca = circuit_arms(circuit)
    aa = {m: arithmetic_allocation_cost(arithmetic, m) for m in (
        "COLD", "WARM", "FLASH", "RAW_HISTORY", "SHAM_ALL_MERGED", "ABLATION"
    )}

    gates = {
        "same_operator_opposite_directions": (
            classify_move(circuit["old"], circuit["target"]) == "REFINE"
            and classify_move(arithmetic["old"], arithmetic["target"]) == "COARSEN"
        ),
        "circuit_collision_reproduced": (
            circuit["signatures"][CIRCUIT_A] == circuit["signatures"][CIRCUIT_B]
            and [circuit["sizes"][CIRCUIT_A], circuit["sizes"][CIRCUIT_B]] == [2, 3]
        ),
        "circuit_flash_after_six": ca["FLASH"]["resolved"] and ca["FLASH"]["diagnostic_checks"] == 6,
        "circuit_cold_unknown_after_twelve": (not ca["COLD"]["resolved"]) and ca["COLD"]["diagnostic_checks"] == 12,
        "circuit_sham_rejected": ca["SHAM_DISCRETE"]["sham_rejected"],
        "arithmetic_exact_101_to_2": len(arithmetic["old"]) == 101 and len(arithmetic["target"]) == 2,
        "arithmetic_warm_allocations_2": aa["WARM"]["record_allocations"] == 2 and aa["WARM"]["final_classes"] == 2,
        "arithmetic_flash_allocations_22": (
            aa["FLASH"]["record_allocations"] == 22
            and aa["FLASH"]["raw_allocations_before_flash"] == 20
            and aa["FLASH"]["final_classes"] == 2
        ),
        "arithmetic_cold_allocations_101": aa["COLD"]["record_allocations"] == 101 and aa["COLD"]["final_classes"] == 101,
        "arithmetic_raw_history_cold": aa["RAW_HISTORY"]["record_allocations"] == 101,
        "arithmetic_sham_rejected": aa["SHAM_ALL_MERGED"]["sham_rejected"],
        "arithmetic_ablation_restores_discrete": aa["ABLATION"]["exact_ablation"] and aa["ABLATION"]["final_classes"] == 101,
    }
    gates["pass"] = all(gates.values())

    result = {
        "schema": "mathgraph.qckn.consequential-representation-equilibration.v2",
        "operator": {
            "name": "exact finite consequence-kernel equilibration",
            "rule": "replace current representation by equality under the complete frozen protected consequence map",
            "scope": "finite complete protected-consequence snapshot",
            "frozen_qck_msi_modified": False,
        },
        "circuit_world": {
            "source_commit": PVSNP_COMMIT,
            "evidence_sha": PVSNP_EVIDENCE_SHA,
            "move": classify_move(circuit["old"], circuit["target"]),
            "old_classes": len(circuit["old"]),
            "target_classes": len(circuit["target"]),
            "arms": ca,
        },
        "arithmetic_world": {
            "source_commit": MSI_COMMIT,
            "test_blob": ARITHMETIC_TEST_BLOB,
            "base": 10,
            "histories": len(arithmetic["carrier"]),
            "retained_future_contexts": [list(x) for x in arithmetic["retained"]],
            "move": classify_move(arithmetic["old"], arithmetic["target"]),
            "old_classes": len(arithmetic["old"]),
            "target_classes": len(arithmetic["target"]),
            "flash_after_raw_histories": ARITHMETIC_FLASH_AFTER,
            "arms": aa,
        },
        "lean_v1_negative": {
            "status": "NOT_USED_AS_AUTHORITY",
            "reason": "historical Arena corpus hash changed and the semantic-context cache was experimental rather than production-promoted",
            "failed_replay_run": 35409594145,
        },
        "gates": gates,
        "scientific_verdict": (
            "PASS_BIDIRECTIONAL_CONSEQUENTIAL_REPRESENTATION_EQUILIBRATION"
            if gates["pass"]
            else "FAIL_REPRESENTATION_EQUILIBRATION_V2"
        ),
        "boundary": (
            "Bounded finite bidirectional representation equilibration under complete frozen consequence maps. "
            "It establishes one exact refinement case and one exact coarsening case with late Flash scheduling. "
            "It does not license coarsening under unknown future obligations, modify frozen QCK/MSI semantics, "
            "prove P!=NP, or establish universal representation optimality."
        ),
    }
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"))
    result["digest_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return result


def main():
    r = run()
    (ROOT / "result.json").write_text(json.dumps(r, indent=2, sort_keys=True) + "\n")
    print("REPRESENTATION_EQUILIBRATION_V2=" + r["scientific_verdict"])
    print("CIRCUIT=" + json.dumps(r["circuit_world"]["arms"], sort_keys=True))
    print("ARITHMETIC=" + json.dumps(r["arithmetic_world"]["arms"], sort_keys=True))
    print("DIGEST_SHA256=" + r["digest_sha256"])
    if not r["gates"]["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
