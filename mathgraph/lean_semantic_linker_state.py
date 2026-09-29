"""Compile a warranted origin-first corpus-linker state into Crystal memory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from mathgraph.crystal import SemanticObject, canonical_bytes


INTERFACES = (
    "lean.corpus-linker.routing-state@1",
    "lean.corpus-linker.actionable-residual@1",
    "lean.corpus-linker.origin-law@1",
)


def compile_linker_state(authority: Mapping[str, Any]) -> SemanticObject:
    if authority.get("status") != "WARRANTED_BOUNDED_ROUTING_STATE":
        raise ValueError("linker state requires warranted routing authority")

    combined = dict(authority["combined_state"])
    if combined["candidate_count"] != (
        combined["qualified_reusable_count"]
        + combined["discharged_non_bridge_count"]
        + combined["rejected_false_candidate_count"]
        + combined["unknown_actionable_count"]
    ):
        raise ValueError("non-partitioning linker state")
    if combined["unknown_actionable_count"] != 0:
        raise ValueError("v1 zero-residual linker capability requires empty actionable residual")

    payload = canonical_bytes({
        "scope": authority["scope"],
        "authority": authority["authority"],
        "combined_state": combined,
        "equivalence_partition": authority["equivalence_partition"],
        "directional_partition": authority["directional_partition"],
        "systems_law": authority["systems_law"],
        "trust_boundary": authority["trust_boundary"],
        "next_residual": "expand corpus boundary; current bounded bridge residual is empty",
    })
    return SemanticObject(
        "lean.origin-first-semantic-linker-state@1",
        1,
        payload,
        INTERFACES,
    )


def compile_authority_file(path: str | Path, out_path: str | Path | None = None) -> dict[str, Any]:
    authority=json.loads(Path(path).read_text(encoding="utf-8"))
    obj=compile_linker_state(authority)
    result={
        "schema":"mathgraph.compiled-origin-first-linker-state.v1",
        "status":"REUSABLE",
        "semantic_object_id":obj.id,
        "type_id":obj.type_id,
        "interface_ids":list(obj.interfaces),
        "candidate_count":authority["combined_state"]["candidate_count"],
        "qualified_reusable_count":authority["combined_state"]["qualified_reusable_count"],
        "discharged_non_bridge_count":authority["combined_state"]["discharged_non_bridge_count"],
        "rejected_false_candidate_count":authority["combined_state"]["rejected_false_candidate_count"],
        "unknown_actionable_count":authority["combined_state"]["unknown_actionable_count"],
        "next_residual":"expand corpus boundary",
    }
    if out_path is not None:
        Path(out_path).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return result
