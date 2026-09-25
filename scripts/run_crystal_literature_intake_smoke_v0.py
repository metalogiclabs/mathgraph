#!/usr/bin/env python3
"""First real-source literature-to-Crystal intake smoke test."""

from __future__ import annotations

from itertools import combinations
import json
from pathlib import Path
import subprocess
import sys

from mathgraph.crystal import SemanticObject
from mathgraph.math_claim import MathClaimPayload

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evidence" / "crystal-literature-intake-smoke-v0" / "source_manifest.json"
RESULT = ROOT / "evidence" / "crystal-literature-intake-smoke-v0" / "result.json"
PARENT = "8111fe6abab66c2d3aae622432f1c04614e796f0"


def run(command: list[str], *, input_text: str | None = None) -> str:
    p = subprocess.run(command, cwd=ROOT, input=input_text, text=True, capture_output=True)
    if p.returncode != 0:
        sys.stderr.write(p.stdout)
        sys.stderr.write(p.stderr)
        raise SystemExit(f"command failed: {command}")
    return p.stdout


def verify_tuza_sharpness() -> dict:
    vertices = tuple(range(4))
    edges = tuple(combinations(vertices, 2))
    triangles = tuple(combinations(vertices, 3))

    tri_edges = {
        tri: frozenset(combinations(tri, 2))
        for tri in triangles
    }

    degrees = {
        v: sum(1 for edge in edges if v in edge)
        for v in vertices
    }
    max_degree = max(degrees.values())

    packing = 0
    packing_witness = ()
    for r in range(len(triangles) + 1):
        for chosen in combinations(triangles, r):
            used = set()
            ok = True
            for tri in chosen:
                if used & set(tri_edges[tri]):
                    ok = False
                    break
                used |= set(tri_edges[tri])
            if ok and r > packing:
                packing = r
                packing_witness = chosen

    cover = None
    cover_witness = None
    for r in range(len(edges) + 1):
        for chosen in combinations(edges, r):
            chosen_set = set(chosen)
            if all(chosen_set & set(tri_edges[tri]) for tri in triangles):
                cover = r
                cover_witness = chosen
                break
        if cover is not None:
            break

    assert max_degree == 3
    assert packing == 1
    assert cover == 2
    assert cover == 2 * packing

    return {
        "witness_graph": "K4",
        "vertices": 4,
        "edges": 6,
        "triangles": 4,
        "max_degree": max_degree,
        "nu_triangle_packing": packing,
        "tau_triangle_edge_cover": cover,
        "packing_witness": [list(t) for t in packing_witness],
        "cover_witness": [list(e) for e in cover_witness],
        "verdict": "WARRANTED_WITNESS",
    }


def verify_vixra_energy_equivalence() -> dict:
    query = """(set-logic QF_NRA)
(declare-const sigma Real)
(declare-const t Real)
(assert (> sigma 0))
(assert (< sigma 1))
(assert (not (= t 0)))
(assert (xor
  (= (* t (- 1 (* 2 sigma))) 0)
  (= sigma (/ 1 2))))
(check-sat)
"""
    out = run(["z3", "-in", "-smt2"], input_text=query).strip()
    assert out == "unsat", out
    return {
        "assumptions": ["0 < sigma < 1", "t != 0", "Im(E_rho) = t(1-2*sigma)"],
        "target": "Im(E_rho)=0 iff sigma=1/2",
        "z3_result_for_negated_equivalence": out,
        "verdict": "WARRANTED_CONDITIONAL_ALGEBRA",
        "z3_version": run(["z3", "--version"]).strip(),
    }


def claim_objects(sources: list[dict]) -> tuple[dict, dict]:
    candidate_source = {}
    warranted_formal = {}

    for source in sources:
        cid = source["claim_id"]
        source_obj = MathClaimPayload(
            claim_id=cid + ".source",
            dialect="literature-prose-extraction-v0",
            context=(),
            assumptions=(),
            statement=source["extracted_claim"],
            source_ref=source["source_id"] + "|" + source["source_url"],
        ).semantic_object()
        assert SemanticObject.from_bytes(source_obj.to_bytes()) == source_obj
        candidate_source[cid] = source_obj.id

    arxiv = sources[0]
    arxiv_obj = MathClaimPayload(
        claim_id=arxiv["claim_id"],
        dialect="finite-graph-certificate-v0",
        context=(
            ("G", "FiniteSimpleGraph"),
            ("nu", "triangle-edge-disjoint-packing-number"),
            ("tau", "triangle-edge-cover-number"),
        ),
        assumptions=("maxDegree(G) <= 3",),
        statement="exists G: maxDegree(G)<=3 and tau(G)=2*nu(G)",
        source_ref=arxiv["source_id"] + "|" + arxiv["source_url"],
    ).semantic_object()
    assert SemanticObject.from_bytes(arxiv_obj.to_bytes()) == arxiv_obj
    warranted_formal[arxiv["claim_id"]] = arxiv_obj.id

    vixra = sources[1]
    vixra_obj = MathClaimPayload(
        claim_id=vixra["claim_id"],
        dialect="real-arithmetic-claim-v0",
        context=(("sigma", "Real"), ("t", "Real")),
        assumptions=("0 < sigma < 1", "t != 0", "Im(E_rho)=t*(1-2*sigma)"),
        statement="Im(E_rho)=0 iff sigma=1/2",
        source_ref=vixra["source_id"] + "|" + vixra["source_url"],
    ).semantic_object()
    assert SemanticObject.from_bytes(vixra_obj.to_bytes()) == vixra_obj
    warranted_formal[vixra["claim_id"]] = vixra_obj.id

    return candidate_source, warranted_formal


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    sources = manifest["sources"]
    assert len(sources) == 2

    tuza = verify_tuza_sharpness()
    zeta = verify_vixra_energy_equivalence()
    source_objects, formal_objects = claim_objects(sources)

    evidence = {
        "schema": "mathgraph.crystal-literature-intake-smoke-v0.qualified",
        "status": "QUALIFIED_BOUNDED",
        "parent_crystal_claim_head": PARENT,
        "crystal_waist_changed": False,
        "claim_dialect_code_changed": False,
        "sources": [
            {
                "source_id": source["source_id"],
                "archive": source["archive"],
                "claim_id": source["claim_id"],
                "provenance_strength": source["provenance_strength"],
                "source_object_id": source_objects[source["claim_id"]],
                "formal_object_id": formal_objects[source["claim_id"]],
            }
            for source in sources
        ],
        "verification": {
            "arxiv_tuza_sharpness": tuza,
            "vixra_energy_equivalence": zeta,
        },
        "epistemic_split": {
            "source_claim_extraction": "CANDIDATE_UNTIL_INDEPENDENT_SOURCE_FIDELITY_CHECK",
            "formalized_claim_mathematics": "WARRANTED_ON_DECLARED_BOUNDARY",
            "crystal_admission": "FORMAL_OBJECTS_ONLY; SOURCE_EXTRACTION_OBJECTS_RETAINED_AS_CANDIDATE_PROVENANCE",
        },
        "results": {
            "sources_ingested": 2,
            "archives": 2,
            "atomic_claims_extracted": 2,
            "formalized_claims_decisively_verified": 2,
            "formalized_claims_rejected": 0,
            "formalized_claims_unknown": 0,
            "new_crystal_waist_fields": 0,
            "new_claim_dialect_fields": 0,
        },
        "boundary": (
            "Two manually selected explicit abstract-level claims only. Mathematical verification "
            "is independent and bounded. Source-to-formal extraction fidelity is deliberately not "
            "promoted by the mathematical verifier and remains candidate provenance until a separate "
            "source-fidelity check is qualified. This is an intake smoke test, not evidence that "
            "arbitrary arXiv/viXra prose can be formalized automatically."
        ),
    }
    RESULT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print("CRYSTAL_LITERATURE_INTAKE_SMOKE_V0=QUALIFIED_BOUNDED")
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
