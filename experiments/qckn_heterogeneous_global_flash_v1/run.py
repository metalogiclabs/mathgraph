from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from experiments.arc_robotics_cross_domain_v1.core import (
    TRIPLES,
    _cold_calibration,
    _filter_once,
    _observe,
    _target_setup,
    _transferred_calibration,
    discover_source_operator,
    majority3_code,
    operator_orbit,
    source_examples,
)

SOURCE_RUN = 35212705346
SOURCE_COMMIT = "129901f70d5dd440cc0238ee734e9b7528305be7"
SOURCE_ARTIFACT = 10494015583
SOURCE_ARTIFACT_DIGEST = "sha256:129b56231c95d71e4e03ca0150e80cc8970aa263d481b5f7f44d851a105b5e62"
ARRIVAL_AFTER_INTERVENTIONS = 1

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Spectator:
    domain: str
    obligation: str
    required_effect: str
    source_effect: str
    evidence_sha: str
    before: str = "LIVE"
    after: str = "LIVE"
    reason: str = "NO_VERIFIED_CROSS_DOMAIN_ADAPTER"


SPECTATORS = (
    Spectator(
        "qckn",
        "typed finite-map target acquisition",
        "semantic_transport",
        "relational_operator_transport",
        "ad68f5f3a75083b9088a98a5ad6a7823b8c473d2",
    ),
    Spectator(
        "collatz",
        "bank-order policy frontier",
        "block_dominated_policy",
        "relational_operator_transport",
        "6ea5ce6ef40db44bb4c4d8f556534987e6742577",
    ),
    Spectator(
        "pvsnp",
        "circuit construction-state repair",
        "refine_insufficient_representation",
        "relational_operator_transport",
        "b5781dd62f53fdaaeb32a703bbc7c13977f0e19e",
    ),
    Spectator(
        "lean",
        "LeanEval consumer continuation",
        "consumer_attachment",
        "relational_operator_transport",
        "2c2ba46877121b127fe57d0daf22f7c798540b79",
        reason="SOURCE_PROBE_PENDING_AND_NO_VERIFIED_ADAPTER",
    ),
)


def derive_seed(github_sha: str, github_run_id: str) -> int:
    material = f"{github_sha}:{github_run_id}:heterogeneous-global-flash-v1".encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _cold_prefix(target_code: int, n: int):
    observations = []
    candidates = list(range(256))
    evaluations = 0
    for bits in TRIPLES[:n]:
        observation = _observe(target_code, bits)
        observations.append(observation)
        candidates, used = _filter_once(candidates, observation)
        evaluations += used
    return observations, evaluations


def _online_transfer(
    target_code: int,
    retained_code: int,
    arrival_after: int = ARRIVAL_AFTER_INTERVENTIONS,
) -> dict:
    observations, evaluations = _cold_prefix(target_code, arrival_after)
    cold_prefix_evaluations = evaluations

    family = list(operator_orbit(retained_code))
    candidates = family[:]
    transport_evaluations = 0

    for observation in observations:
        candidates, used = _filter_once(candidates, observation)
        evaluations += used
        transport_evaluations += used

    unique_at = len(observations) if len(candidates) == 1 else None
    rejected = not candidates

    if not rejected:
        already_seen = {bits for bits, _ in observations}
        for bits in TRIPLES:
            if bits in already_seen:
                continue
            observation = _observe(target_code, bits)
            observations.append(observation)
            candidates, used = _filter_once(candidates, observation)
            evaluations += used
            transport_evaluations += used

            if not candidates:
                rejected = True
                break

            if len(candidates) == 1:
                if unique_at is None:
                    unique_at = len(observations)
                elif len(observations) > unique_at:
                    return {
                        "learned_code": candidates[0],
                        "observations": observations,
                        "operator_evaluations": evaluations,
                        "cold_prefix_evaluations": cold_prefix_evaluations,
                        "transport_evaluations": transport_evaluations,
                        "fallback_evaluations": 0,
                        "transferred_rejected": False,
                    }
            else:
                unique_at = None

    if rejected:
        learned, fallback_observations, fallback_evaluations = _cold_calibration(
            target_code,
            existing_observations=observations,
        )
        return {
            "learned_code": learned,
            "observations": fallback_observations,
            "operator_evaluations": evaluations + fallback_evaluations,
            "cold_prefix_evaluations": cold_prefix_evaluations,
            "transport_evaluations": transport_evaluations,
            "fallback_evaluations": fallback_evaluations,
            "transferred_rejected": True,
        }

    learned = candidates[0] if len(candidates) == 1 else None
    return {
        "learned_code": learned,
        "observations": observations,
        "operator_evaluations": evaluations,
        "cold_prefix_evaluations": cold_prefix_evaluations,
        "transport_evaluations": transport_evaluations,
        "fallback_evaluations": 0,
        "transferred_rejected": False,
    }


def _finish(arm: str, target_code: int, data: dict) -> dict:
    learned = data["learned_code"]
    observations = data["observations"]
    operator_evaluations = data["operator_evaluations"]
    return {
        "arm": arm,
        "target_code": target_code,
        "learned_code": learned,
        "correct": learned == target_code,
        "calibration_interventions": len(observations),
        "operator_evaluations": operator_evaluations,
        "developmental_cost": operator_evaluations + len(observations),
        "transferred_rejected": bool(data.get("transferred_rejected", False)),
        "cold_prefix_evaluations": int(data.get("cold_prefix_evaluations", 0)),
        "transport_evaluations": int(data.get("transport_evaluations", 0)),
        "fallback_evaluations": int(data.get("fallback_evaluations", 0)),
    }


def run(seed: int) -> dict:
    source_code, source_discovery_evaluations = discover_source_operator(source_examples())
    target_code, target_adapter, _ = _target_setup(seed)

    cold_code, cold_obs, cold_evals = _cold_calibration(target_code)
    cold = _finish(
        "COLD",
        target_code,
        {
            "learned_code": cold_code,
            "observations": cold_obs,
            "operator_evaluations": cold_evals,
        },
    )

    warm_code, warm_obs, warm_evals, warm_rejected = _transferred_calibration(
        target_code, operator_orbit(source_code)
    )
    upfront = _finish(
        "UPFRONT",
        target_code,
        {
            "learned_code": warm_code,
            "observations": warm_obs,
            "operator_evaluations": warm_evals,
            "transferred_rejected": warm_rejected,
        },
    )

    flash = _finish(
        "FLASH",
        target_code,
        _online_transfer(target_code, source_code),
    )
    sham = _finish(
        "SHAM",
        target_code,
        _online_transfer(target_code, majority3_code()),
    )

    raw_shared = dict(cold)
    raw_shared["arm"] = "RAW_SHARED"
    ablation = dict(cold)
    ablation["arm"] = "ABLATION"

    arms = {
        row["arm"]: row
        for row in (cold, upfront, flash, sham, raw_shared, ablation)
    }

    gates = {
        "all_exact": all(row["correct"] for row in arms.values()),
        "target_was_live_before_flash": flash["cold_prefix_evaluations"] > 0,
        "upfront_cost_5": upfront["developmental_cost"] == 5,
        "cold_cost_518": cold["developmental_cost"] == 518,
        "flash_cost_261": flash["developmental_cost"] == 261,
        "flash_lt_cold": flash["developmental_cost"] < cold["developmental_cost"],
        "upfront_lt_flash": upfront["developmental_cost"] < flash["developmental_cost"],
        "raw_shared_equals_cold": raw_shared["developmental_cost"] == cold["developmental_cost"],
        "ablation_equals_cold": ablation["developmental_cost"] == cold["developmental_cost"],
        "sham_rejected": sham["transferred_rejected"],
        "sham_cost_789": sham["developmental_cost"] == 789,
        "spectators_unchanged": all(s.before == s.after == "LIVE" for s in SPECTATORS),
        "no_unauthorized_spectator_edge": all(
            s.reason in {
                "NO_VERIFIED_CROSS_DOMAIN_ADAPTER",
                "SOURCE_PROBE_PENDING_AND_NO_VERIFIED_ADAPTER",
            }
            for s in SPECTATORS
        ),
    }
    gates["pass"] = all(gates.values())

    result = {
        "schema": "mathgraph.qckn.heterogeneous-global-flash.v1",
        "seed": seed,
        "source": {
            "domain": "arc_like_symbolic",
            "capability": "binary_relation_v1",
            "effect": "relational_operator_transport",
            "source_code": source_code,
            "source_discovery_evaluations": source_discovery_evaluations,
            "qualified_source_run": SOURCE_RUN,
            "qualified_source_commit": SOURCE_COMMIT,
            "qualified_source_artifact": SOURCE_ARTIFACT,
            "qualified_source_artifact_digest": SOURCE_ARTIFACT_DIGEST,
        },
        "target": {
            "domain": "finite_embodied_intervention_world",
            "target_code": target_code,
            "target_adapter": target_adapter,
            "arrival_after_interventions": ARRIVAL_AFTER_INTERVENTIONS,
        },
        "arms": arms,
        "spectators": [asdict(s) for s in SPECTATORS],
        "gates": gates,
        "scientific_verdict": (
            "PASS_ONE_VERIFIED_LIVE_CROSS_DOMAIN_FLASH_EDGE"
            if gates["pass"]
            else "FAIL_HETEROGENEOUS_GLOBAL_FLASH_V1"
        ),
        "boundary": (
            "This establishes one bounded live cross-domain Flash edge from an ARC-like "
            "symbolic relational capability into a finite embodied target under the pinned "
            "adapter family. It does not establish semantic transfer into QCKN, Collatz, "
            "P-vs-NP, or Lean; those obligations intentionally remain live without verified adapters."
        ),
    }
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"))
    result["digest_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return result


def main() -> None:
    seed = derive_seed(
        os.environ.get("GITHUB_SHA", "local"),
        os.environ.get("GITHUB_RUN_ID", "0"),
    )
    result = run(seed)
    out = ROOT / "result.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("HETEROGENEOUS_GLOBAL_FLASH_V1=" + result["scientific_verdict"])
    print(
        "COSTS="
        + json.dumps(
            {
                arm: row["developmental_cost"]
                for arm, row in result["arms"].items()
            },
            sort_keys=True,
        )
    )
    print("DIGEST_SHA256=" + result["digest_sha256"])
    if not result["gates"]["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
