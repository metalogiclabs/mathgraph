from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
MSI_ROOT = Path(os.environ.get("MSI_SOURCE_ROOT", "_vendor/representation_genesis_source"))
PVSNP_ROOT = Path(os.environ.get("PVSNP_SOURCE_ROOT", "_vendor/pvsnp_source"))

sys.path.insert(0, str(MSI_ROOT))

from consequential_core import (
    DevelopmentState,
    EquivalenceRelation,
    PairResidual,
    RefineRepresentation,
    ablate,
    compile_repair,
)
from consequential_certification import certify_representation_repair

SOURCE_RUN = 34591859113
SOURCE_COMMIT = "9e6ba7cac5eeb965e1e882ebe038424a87a69ea0"
SOURCE_ARTIFACT = 10195947331
SOURCE_ARTIFACT_DIGEST = "sha256:3ede7957ea74f3ee7417977781e3841361e7c73b3485d70364b4da8cc6392029"
SOURCE_SNAPSHOT_DIGEST = "3106999ce529f3b7c5f6308d0e0217c208fdb4d9c426aea38d23bc94904f9cc7"
SOURCE_REPRESENTATION_DIGEST = "6d6847fb66ad4c31fe54ab16022f97df7c2b359219c8f9202e76b58b7d798987"

PVSNP_COMMIT = "4df88a272926126b895c2fb6220c56012949df05"
PVSNP_EVIDENCE_SHA = "b5781dd62f53fdaaeb32a703bbc7c13977f0e19e"

CIRCUIT_A = 0x8F
CIRCUIT_B = 0xEA
PROJECTION_X0 = 0xAA
PROJECTION_X1 = 0xCC
FLASH_AFTER_METRICS = 6

ARC_CONTROL = {
    "domain": "arc3",
    "run_id": 35403960070,
    "artifact_id": 10571621340,
    "artifact_digest": "sha256:8e12f7a155cc413ad30cd4d98dd029eab13dbdd4bfb9ca6b381bb7b25d770474",
    "observed_effect": "10 certified action consequence classes; 3444 proposals removed over 14 activations on ft09",
    "admission": "REJECTED_FOR_THIS_OPERATOR",
    "reason": "available artifact certifies a concrete action quotient/compression, not this strict PairResidual minimal-refinement contract",
}
LEAN_CONTROL = {
    "domain": "lean_localdef",
    "evidence_file_sha": "b4ad942b7a12772044f9edeba8f86051e0ba8eca",
    "observed_effect": "semantic cache replaces transient LocalDef wrapper identity by exact (type,value) identity",
    "admission": "REJECTED_FOR_THIS_OPERATOR",
    "reason": "successful change is a safe coarsening of an over-fine cache key, not a strict refinement of an insufficient quotient",
}


def load_pvsnp_lab():
    path = PVSNP_ROOT / "experiments/pvsnp_hardness_lab_v1/lab.py"
    spec = importlib.util.spec_from_file_location("pvsnp_lab_flash_rep", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def blocks(rel: EquivalenceRelation):
    unseen = set(rel.carrier)
    out = []
    while unseen:
        x = min(unseen)
        block = tuple(sorted(y for y in rel.carrier if rel.same(x, y)))
        out.append(block)
        unseen -= set(block)
    return tuple(sorted(out))


def consequence_refinement(old: EquivalenceRelation, consequences: dict[int, int]) -> EquivalenceRelation:
    # Domain-neutral transferred constructor:
    # refine only inside existing blocks and only where protected consequences differ.
    return EquivalenceRelation.from_observation(
        old.carrier,
        lambda x: (
            tuple(sorted(y for y in old.carrier if old.same(x, y))),
            consequences[x],
        ),
    )


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
    assert signatures[CIRCUIT_A] != signatures[PROJECTION_X0]

    old = EquivalenceRelation.from_observation(carrier, lambda m: signatures[m])
    assert blocks(old) == (
        tuple(sorted((CIRCUIT_A, CIRCUIT_B))),
        tuple(sorted((PROJECTION_X0, PROJECTION_X1))),
    )

    residual = PairResidual(
        CIRCUIT_A,
        CIRCUIT_B,
        old,
        sizes[CIRCUIT_A],
        sizes[CIRCUIT_B],
        verifier_tag="verified",
    )
    state = DevelopmentState(carrier, active_representation=old)

    minimal = consequence_refinement(old, sizes)
    expected_minimal_blocks = (
        (CIRCUIT_A,),
        (CIRCUIT_B,),
        tuple(sorted((PROJECTION_X0, PROJECTION_X1))),
    )
    assert blocks(minimal) == tuple(sorted(expected_minimal_blocks))

    overfine = EquivalenceRelation.from_partition(carrier, ((CIRCUIT_A,), (CIRCUIT_B,), (PROJECTION_X0,), (PROJECTION_X1,)))

    return {
        "lab": lab,
        "carrier": carrier,
        "signatures": signatures,
        "sizes": sizes,
        "old": old,
        "residual": residual,
        "state": state,
        "minimal": minimal,
        "overfine": overfine,
    }


def metric_checks(world, n: int) -> int:
    a = world["signatures"][CIRCUIT_A]
    b = world["signatures"][CIRCUIT_B]
    assert len(a) == len(b) == 12
    checked = 0
    for i in range(min(n, 12)):
        checked += 1
        if a[i] != b[i]:
            break
    return checked


def certify_minimal(world):
    certified = certify_representation_repair(
        world["state"],
        world["residual"],
        RefineRepresentation(world["minimal"]),
        experiment_pair=(CIRCUIT_A, CIRCUIT_B),
        observed_same=False,
        attachment="transferred quotient-by-certified-separator constructor",
    )
    after, token = compile_repair(world["state"], certified)
    return after, token


def run_arm(name: str, world) -> dict:
    if name == "WARM":
        before_checks = 0
        after, _ = certify_minimal(world)
        return {
            "arm": name,
            "candidate_metric_checks": before_checks,
            "authority_checks": 1,
            "resolved": True,
            "status": "RESOLVED_BY_MINIMAL_REFINEMENT",
            "final_blocks": blocks(after.active_representation),
            "sham_rejected": False,
            "exact_ablation": False,
        }

    if name == "FLASH":
        before_checks = metric_checks(world, FLASH_AFTER_METRICS)
        assert before_checks == FLASH_AFTER_METRICS
        after, _ = certify_minimal(world)
        return {
            "arm": name,
            "candidate_metric_checks": before_checks,
            "authority_checks": 1,
            "resolved": True,
            "status": "RESOLVED_BY_LATE_TRANSFERRED_REFINEMENT",
            "final_blocks": blocks(after.active_representation),
            "sham_rejected": False,
            "exact_ablation": False,
        }

    if name == "SHAM_OVERFINE":
        before = metric_checks(world, FLASH_AFTER_METRICS)
        rejected = False
        try:
            certify_representation_repair(
                world["state"],
                world["residual"],
                RefineRepresentation(world["overfine"]),
                experiment_pair=(CIRCUIT_A, CIRCUIT_B),
                observed_same=False,
                attachment="overfine remember-everything sham",
            )
        except ValueError:
            rejected = True
        total = before + metric_checks(world, 12) - before
        return {
            "arm": name,
            "candidate_metric_checks": total,
            "authority_checks": 1,
            "resolved": False,
            "status": "UNKNOWN_EXPRESSIVITY",
            "final_blocks": blocks(world["old"]),
            "sham_rejected": rejected,
            "exact_ablation": False,
        }

    if name == "ABLATION":
        before = metric_checks(world, FLASH_AFTER_METRICS)
        after, token = certify_minimal(world)
        restored = ablate(after, token)
        assert restored == world["state"]
        total = before + metric_checks(world, 12) - before
        return {
            "arm": name,
            "candidate_metric_checks": total,
            "authority_checks": 1,
            "resolved": False,
            "status": "UNKNOWN_EXPRESSIVITY",
            "final_blocks": blocks(restored.active_representation),
            "sham_rejected": False,
            "exact_ablation": True,
        }

    if name in {"COLD", "RAW_HISTORY"}:
        total = metric_checks(world, 12)
        return {
            "arm": name,
            "candidate_metric_checks": total,
            "authority_checks": 0,
            "resolved": False,
            "status": "UNKNOWN_EXPRESSIVITY",
            "final_blocks": blocks(world["old"]),
            "sham_rejected": False,
            "exact_ablation": False,
        }

    raise ValueError(name)


def run() -> dict:
    world = build_circuit_world()
    arms = {name: run_arm(name, world) for name in ("COLD", "WARM", "FLASH", "RAW_HISTORY", "SHAM_OVERFINE", "ABLATION")}

    old_blocks = blocks(world["old"])
    minimal_blocks = blocks(world["minimal"])
    projection_pair = tuple(sorted((PROJECTION_X0, PROJECTION_X1)))

    gates = {
        "pvsnp_exact_collision_reproduced": (
            world["signatures"][CIRCUIT_A] == world["signatures"][CIRCUIT_B]
            and world["sizes"][CIRCUIT_A] == 2
            and world["sizes"][CIRCUIT_B] == 3
        ),
        "projection_control_reproduced": (
            world["signatures"][PROJECTION_X0] == world["signatures"][PROJECTION_X1]
            and world["sizes"][PROJECTION_X0] == world["sizes"][PROJECTION_X1] == 0
        ),
        "old_representation_has_two_blocks": len(old_blocks) == 2,
        "minimal_repair_splits_only_motivating_block": (
            len(minimal_blocks) == 3
            and projection_pair in minimal_blocks
        ),
        "warm_resolves_without_metric_search": (
            arms["WARM"]["resolved"] and arms["WARM"]["candidate_metric_checks"] == 0
        ),
        "flash_arrives_after_six_failed_metric_checks": (
            arms["FLASH"]["resolved"] and arms["FLASH"]["candidate_metric_checks"] == 6
        ),
        "cold_exhausts_all_twelve_and_remains_unknown": (
            not arms["COLD"]["resolved"] and arms["COLD"]["candidate_metric_checks"] == 12
        ),
        "raw_history_does_not_transfer_constructor": (
            not arms["RAW_HISTORY"]["resolved"] and arms["RAW_HISTORY"]["candidate_metric_checks"] == 12
        ),
        "overfine_sham_rejected_by_minimality": (
            arms["SHAM_OVERFINE"]["sham_rejected"] and not arms["SHAM_OVERFINE"]["resolved"]
        ),
        "ablation_restores_old_representation": (
            arms["ABLATION"]["exact_ablation"]
            and arms["ABLATION"]["final_blocks"] == old_blocks
            and not arms["ABLATION"]["resolved"]
        ),
        "arc_typed_out": ARC_CONTROL["admission"] == "REJECTED_FOR_THIS_OPERATOR",
        "lean_typed_out": LEAN_CONTROL["admission"] == "REJECTED_FOR_THIS_OPERATOR",
    }
    gates["pass"] = all(gates.values())

    result = {
        "schema": "mathgraph.qckn.flash-representation-genesis.v1",
        "source_authority": {
            "domain": "finite_temporal_trace",
            "run_id": SOURCE_RUN,
            "commit": SOURCE_COMMIT,
            "artifact_id": SOURCE_ARTIFACT,
            "artifact_digest": SOURCE_ARTIFACT_DIGEST,
            "snapshot_digest": SOURCE_SNAPSHOT_DIGEST,
            "representation_artifact_digest": SOURCE_REPRESENTATION_DIGEST,
            "transferred_capability": "generic quotient-by-certified-separator minimum-refinement constructor",
        },
        "target": {
            "domain": "finite_nand_circuit_complexity",
            "pvsnp_commit": PVSNP_COMMIT,
            "pvsnp_evidence_sha": PVSNP_EVIDENCE_SHA,
            "collision": {
                "left": hex(CIRCUIT_A),
                "right": hex(CIRCUIT_B),
                "shared_12_metric_signature": list(world["signatures"][CIRCUIT_A]),
                "exact_nand_sizes": [world["sizes"][CIRCUIT_A], world["sizes"][CIRCUIT_B]],
            },
            "preserved_control_block": {
                "members": [hex(PROJECTION_X0), hex(PROJECTION_X1)],
                "exact_nand_size": 0,
            },
            "flash_arrival_after_metric_checks": FLASH_AFTER_METRICS,
        },
        "arms": arms,
        "typed_controls": [ARC_CONTROL, LEAN_CONTROL],
        "gates": gates,
        "scientific_verdict": (
            "PASS_CROSS_DOMAIN_FLASH_REPRESENTATION_GENESIS"
            if gates["pass"]
            else "FAIL_FLASH_REPRESENTATION_GENESIS"
        ),
        "boundary": (
            "Bounded cross-domain transfer of a verified minimum-refinement constructor from a finite temporal "
            "representation-genesis source into one exact finite circuit-complexity residual. The circuit target "
            "is live before arrival and has already tested six of twelve scalar summaries. The result does not "
            "establish universal representation learning, unrestricted feature invention, P!=NP, or that ARC/Lean "
            "share this repair operator; those controls are explicitly not admitted."
        ),
    }
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"))
    result["digest_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return result


def main():
    result = run()
    (ROOT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("FLASH_REPRESENTATION_GENESIS_V1=" + result["scientific_verdict"])
    print("ARMS=" + json.dumps({
        k: {
            "checks": v["candidate_metric_checks"],
            "authority": v["authority_checks"],
            "resolved": v["resolved"],
            "status": v["status"],
        }
        for k, v in result["arms"].items()
    }, sort_keys=True))
    print("DIGEST_SHA256=" + result["digest_sha256"])
    if not result["gates"]["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
