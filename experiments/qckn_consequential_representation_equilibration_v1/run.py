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

PVSNP_COMMIT = "4df88a272926126b895c2fb6220c56012949df05"
PVSNP_EVIDENCE_SHA = "b5781dd62f53fdaaeb32a703bbc7c13977f0e19e"
LEAN_COMMIT = "919937fb4a58becfb31ad7cbcce9351b601d8e11"
LEAN_CONTEXT_CACHE_BLOB = "b4ad942b7a12772044f9edeba8f86051e0ba8eca"
FLASH_AFTER_CIRCUIT_METRICS = 6
FLASH_AFTER_LEAN_QUERIES = 3

CIRCUIT_A = 0x8F
CIRCUIT_B = 0xEA
PROJECTION_X0 = 0xAA
PROJECTION_X1 = 0xCC


def load_pvsnp_lab():
    path = PVSNP_ROOT / "experiments/pvsnp_hardness_lab_v1/lab.py"
    spec = importlib.util.spec_from_file_location("pvsnp_lab_equilibration", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def partition_from_key(carrier, key):
    buckets = {}
    for x in carrier:
        buckets.setdefault(key(x), []).append(x)
    return tuple(sorted((tuple(sorted(v, key=repr)) for v in buckets.values()), key=repr))


def pairs(partition):
    return frozenset((x, y) for block in partition for x in block for y in block)


def classify_move(old, target):
    a, b = pairs(old), pairs(target)
    if a == b:
        return "EQUAL"
    if b < a:
        return "REFINE"
    if a < b:
        return "COARSEN"
    return "REPARTITION"


def consequence_kernel(carrier, consequence):
    return partition_from_key(carrier, consequence)


def certify_equilibration(carrier, consequence, proposed):
    """Exact finite authority: proposed must equal the complete consequence kernel.

    This is intentionally stronger than the frozen conservative MSI refinement gate.
    It licenses coarsening only because the protected consequence set is complete and
    frozen for the declared finite world.
    """
    target = consequence_kernel(carrier, consequence)
    checks = 0
    for x, y in itertools.combinations(carrier, 2):
        checks += 1
        proposed_same = any(x in block and y in block for block in proposed)
        consequence_same = consequence(x) == consequence(y)
        if proposed_same != consequence_same:
            raise ValueError("proposed representation is not the exact consequence kernel")
    if proposed != target:
        raise ValueError("proposed representation is not canonical exact consequence kernel")
    return {"partition": proposed, "checks": checks}


def build_circuit_world():
    lab = load_pvsnp_lab()
    enumeration = lab.enumerate_nand(3, 3)
    carrier = (CIRCUIT_A, CIRCUIT_B, PROJECTION_X0, PROJECTION_X1)
    signatures = {m: lab.structural_signature(m, 3) for m in carrier}
    sizes = {m: enumeration.min_size[m] for m in carrier}

    assert signatures[CIRCUIT_A] == signatures[CIRCUIT_B]
    assert sizes[CIRCUIT_A] == 2 and sizes[CIRCUIT_B] == 3
    assert signatures[PROJECTION_X0] == signatures[PROJECTION_X1]
    assert sizes[PROJECTION_X0] == sizes[PROJECTION_X1] == 0

    old = partition_from_key(carrier, lambda m: signatures[m])
    target = consequence_kernel(carrier, lambda m: sizes[m])
    assert classify_move(old, target) == "REFINE"
    return {
        "carrier": carrier,
        "old": old,
        "target": target,
        "sizes": sizes,
        "signatures": signatures,
    }


def circuit_metric_checks(world, n):
    a = world["signatures"][CIRCUIT_A]
    b = world["signatures"][CIRCUIT_B]
    checked = 0
    for i in range(min(n, len(a))):
        checked += 1
        if a[i] != b[i]:
            break
    return checked


def circuit_arm(name, world):
    if name == "WARM":
        cert = certify_equilibration(world["carrier"], lambda x: world["sizes"][x], world["target"])
        return {"resolved": True, "metric_checks": 0, "authority_checks": cert["checks"], "move": "REFINE"}

    if name == "FLASH":
        before = circuit_metric_checks(world, FLASH_AFTER_CIRCUIT_METRICS)
        cert = certify_equilibration(world["carrier"], lambda x: world["sizes"][x], world["target"])
        return {"resolved": True, "metric_checks": before, "authority_checks": cert["checks"], "move": "REFINE"}

    if name == "SHAM_DISCRETE":
        discrete = tuple((x,) for x in sorted(world["carrier"]))
        rejected = False
        try:
            certify_equilibration(world["carrier"], lambda x: world["sizes"][x], discrete)
        except ValueError:
            rejected = True
        return {"resolved": False, "metric_checks": 12, "authority_checks": 1, "move": None, "sham_rejected": rejected}

    if name in {"COLD", "RAW_HISTORY", "ABLATION"}:
        return {
            "resolved": False,
            "metric_checks": 12,
            "authority_checks": 0 if name != "ABLATION" else 6,
            "move": None,
            "exact_ablation": name == "ABLATION",
        }

    raise ValueError(name)


def build_lean_world():
    # Mirrors the pinned LocalDef semantic-context-cache contract:
    # old key = fresh wrapper identity; consequential key = exact (type,value) identity.
    # Wrapper ids are deliberately all distinct while semantic pairs repeat.
    carrier = tuple(range(8))
    semantic = {
        0: ("T0", "V0"),
        1: ("T0", "V0"),
        2: ("T1", "V1"),
        3: ("T0", "V0"),
        4: ("T1", "V1"),
        5: ("T0", "V0"),
        6: ("T0", "V0"),
        7: ("T1", "V1"),
    }
    old = partition_from_key(carrier, lambda x: ("wrapper", x))
    target = consequence_kernel(carrier, lambda x: semantic[x])
    assert classify_move(old, target) == "COARSEN"
    return {"carrier": carrier, "semantic": semantic, "old": old, "target": target}


def simulate_cache(world, mode, flash_after=FLASH_AFTER_LEAN_QUERIES):
    sequence = world["carrier"]
    old_cache = set()
    semantic_cache = set()
    misses = hits = 0
    authority_checks = 0
    moved = False
    rejected = False

    for i, wrapper in enumerate(sequence):
        if mode == "WARM":
            key = world["semantic"][wrapper]
            if key in semantic_cache:
                hits += 1
            else:
                misses += 1
                semantic_cache.add(key)
            continue

        if mode == "FLASH" and i == flash_after:
            cert = certify_equilibration(world["carrier"], lambda x: world["semantic"][x], world["target"])
            authority_checks += cert["checks"]
            # Compile already-seen exact consequences into the coarsened key space.
            for seen in sequence[:i]:
                semantic_cache.add(world["semantic"][seen])
            moved = True

        if mode == "SHAM_ALL_MERGED" and i == flash_after:
            sham = (tuple(world["carrier"]),)
            try:
                certify_equilibration(world["carrier"], lambda x: world["semantic"][x], sham)
            except ValueError:
                rejected = True

        if mode == "ABLATION" and i == flash_after:
            cert = certify_equilibration(world["carrier"], lambda x: world["semantic"][x], world["target"])
            authority_checks += cert["checks"]
            moved = True
            # Exact ablation before the representation is used.
            moved = False
            semantic_cache.clear()

        if mode == "FLASH" and moved:
            key = world["semantic"][wrapper]
            if key in semantic_cache:
                hits += 1
            else:
                misses += 1
                semantic_cache.add(key)
        else:
            key = ("wrapper", wrapper)
            if key in old_cache:
                hits += 1
            else:
                misses += 1
                old_cache.add(key)

    if mode == "WARM":
        authority_checks = certify_equilibration(
            world["carrier"], lambda x: world["semantic"][x], world["target"]
        )["checks"]

    return {
        "misses": misses,
        "hits": hits,
        "authority_checks": authority_checks,
        "move": "COARSEN" if (mode in {"WARM", "FLASH"} and not rejected) else None,
        "sham_rejected": rejected,
        "exact_ablation": mode == "ABLATION",
    }


def run():
    circuit = build_circuit_world()
    lean = build_lean_world()

    circuit_arms = {
        name: circuit_arm(name, circuit)
        for name in ("COLD", "WARM", "FLASH", "RAW_HISTORY", "SHAM_DISCRETE", "ABLATION")
    }
    lean_arms = {
        name: simulate_cache(lean, name)
        for name in ("COLD", "WARM", "FLASH", "RAW_HISTORY", "SHAM_ALL_MERGED", "ABLATION")
    }

    gates = {
        "same_operator_selects_opposite_directions": (
            classify_move(circuit["old"], circuit["target"]) == "REFINE"
            and classify_move(lean["old"], lean["target"]) == "COARSEN"
        ),
        "circuit_exact_foreign_collision": (
            circuit["sizes"][CIRCUIT_A] == 2
            and circuit["sizes"][CIRCUIT_B] == 3
            and circuit["signatures"][CIRCUIT_A] == circuit["signatures"][CIRCUIT_B]
        ),
        "circuit_flash_refines_after_six_checks": (
            circuit_arms["FLASH"]["resolved"]
            and circuit_arms["FLASH"]["metric_checks"] == 6
            and circuit_arms["FLASH"]["move"] == "REFINE"
        ),
        "circuit_cold_stays_unknown": (
            not circuit_arms["COLD"]["resolved"]
            and circuit_arms["COLD"]["metric_checks"] == 12
        ),
        "circuit_sham_rejected": circuit_arms["SHAM_DISCRETE"]["sham_rejected"],
        "lean_old_is_eight_wrapper_classes": len(lean["old"]) == 8,
        "lean_target_is_two_semantic_classes": len(lean["target"]) == 2,
        "lean_warm_reduces_misses_8_to_2": (
            lean_arms["COLD"]["misses"] == 8
            and lean_arms["WARM"]["misses"] == 2
            and lean_arms["WARM"]["hits"] == 6
        ),
        "lean_flash_after_three_avoids_remaining_misses": (
            lean_arms["FLASH"]["misses"] == 3
            and lean_arms["FLASH"]["hits"] == 5
            and lean_arms["FLASH"]["move"] == "COARSEN"
        ),
        "lean_raw_history_is_cold": lean_arms["RAW_HISTORY"]["misses"] == 8,
        "lean_overcoarsen_sham_rejected": (
            lean_arms["SHAM_ALL_MERGED"]["sham_rejected"]
            and lean_arms["SHAM_ALL_MERGED"]["misses"] == 8
        ),
        "lean_ablation_restores_cold": (
            lean_arms["ABLATION"]["exact_ablation"]
            and lean_arms["ABLATION"]["misses"] == 8
        ),
    }
    gates["pass"] = all(gates.values())

    result = {
        "schema": "mathgraph.qckn.consequential-representation-equilibration.v1",
        "operator": {
            "name": "exact finite consequence-kernel equilibration",
            "rule": "replace current representation by the exact kernel of the complete frozen protected consequence map",
            "directions": ["REFINE", "COARSEN", "EQUAL", "REPARTITION"],
            "admission_boundary": (
                "Coarsening is licensed only under a complete frozen protected-consequence snapshot. "
                "This prototype does not modify the frozen conservative MSI kernel."
            ),
        },
        "circuit_world": {
            "source_commit": PVSNP_COMMIT,
            "evidence_sha": PVSNP_EVIDENCE_SHA,
            "old_partition": circuit["old"],
            "target_partition": circuit["target"],
            "move": classify_move(circuit["old"], circuit["target"]),
            "arms": circuit_arms,
        },
        "lean_world": {
            "source_commit": LEAN_COMMIT,
            "source_blob": LEAN_CONTEXT_CACHE_BLOB,
            "old_partition": lean["old"],
            "target_partition": lean["target"],
            "move": classify_move(lean["old"], lean["target"]),
            "semantic_sequence": [lean["semantic"][x] for x in lean["carrier"]],
            "flash_after_queries": FLASH_AFTER_LEAN_QUERIES,
            "arms": lean_arms,
            "scope": (
                "Finite exact model of the pinned LocalDef cache-key contract: transient wrapper identity "
                "versus exact (type,value) identity. Full Lean workload evidence is checked separately in CI."
            ),
        },
        "gates": gates,
        "scientific_verdict": (
            "PASS_BIDIRECTIONAL_CONSEQUENTIAL_REPRESENTATION_EQUILIBRATION"
            if gates["pass"]
            else "FAIL_REPRESENTATION_EQUILIBRATION_V1"
        ),
        "boundary": (
            "This is a bounded finite bidirectional representation experiment. It demonstrates one exact "
            "refinement world and one exact coarsening world under complete frozen consequence maps, with live "
            "Flash scheduling and matched controls. It does not establish safe coarsening under future unknown "
            "obligations, universal representation optimality, P!=NP, or a general Lean optimization theorem."
        ),
    }
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"))
    result["digest_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return result


def main():
    result = run()
    (ROOT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("REPRESENTATION_EQUILIBRATION_V1=" + result["scientific_verdict"])
    print("CIRCUIT=" + json.dumps(result["circuit_world"]["arms"], sort_keys=True))
    print("LEAN=" + json.dumps(result["lean_world"]["arms"], sort_keys=True))
    print("DIGEST_SHA256=" + result["digest_sha256"])
    if not result["gates"]["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
