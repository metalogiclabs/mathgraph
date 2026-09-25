#!/usr/bin/env python3
"""Bounded source->formal extraction adapters for the literature smoke sources."""

from __future__ import annotations

from html import unescape
import json
from pathlib import Path
import re

from mathgraph.crystal import SemanticObject, content_id
from mathgraph.math_claim import MathClaimPayload, VerifiedClaimRelation

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "evidence" / "crystal-literature-source-fidelity-v1"
MANIFEST = ROOT / "evidence" / "crystal-literature-intake-smoke-v0" / "source_manifest.json"
OUTDIR = ROOT / "evidence" / "crystal-literature-extraction-adapter-v2"
RESULT = OUTDIR / "result.json"
PARENT = "3de9e2528ee6370c9227fdfb3c49f9c2ae09bd65"

EXPECTED_TUZA_FORMAL_ID = "semantic:50e4ea0b8808bc95ead224bed6baee804e259f9e43d72c44bffe3e3259515df1"
EXPECTED_VIXRA_FORMAL_ID = "semantic:d1bc4def7962e5998a9a6d66a5c41e6fa3b13963922d60342db6bf0808176b70"

def textify(data: bytes) -> str:
    text=data.decode("utf-8",errors="replace")
    text=re.sub(r"<script\b[^>]*>.*?</script>"," ",text,flags=re.I|re.S)
    text=re.sub(r"<style\b[^>]*>.*?</style>"," ",text,flags=re.I|re.S)
    text=re.sub(r"<[^>]+>"," ",text)
    text=unescape(text)
    return " ".join(text.split())

def source_object(source: dict) -> SemanticObject:
    return MathClaimPayload(
        claim_id=source["claim_id"] + ".source",
        dialect="literature-prose-extraction-v0",
        context=(),
        assumptions=(),
        statement=source["extracted_claim"],
        source_ref=source["source_id"] + "|" + source["source_url"],
    ).semantic_object()

def parse_tuza(source: dict, text: str) -> SemanticObject:
    lower=text.lower()
    required=[
        "tuza's conjecture for graphs of maximum degree at most seven",
        "pairwise edge-disjoint triangles",
        "triangle-free",
        "maximum degree three",
    ]
    missing=[x for x in required if x not in lower]
    sharp_match=re.search(r"constant\\s+\\$?2\\$?\\s+is\\s+sharp", lower)
    if missing or sharp_match is None:
        raise ValueError(
            "tuza extraction contract not satisfied: "
            + repr(missing + ([] if sharp_match is not None else ["constant $2$ is sharp"]))
        )
    obj=MathClaimPayload(
        claim_id=source["claim_id"],
        dialect="finite-graph-certificate-v0",
        context=(
            ("G", "FiniteSimpleGraph"),
            ("nu", "triangle-edge-disjoint-packing-number"),
            ("tau", "triangle-edge-cover-number"),
        ),
        assumptions=("maxDegree(G) <= 3",),
        statement="exists G: maxDegree(G)<=3 and tau(G)=2*nu(G)",
        source_ref=source["source_id"] + "|" + source["source_url"],
    ).semantic_object()
    if obj.id != EXPECTED_TUZA_FORMAL_ID:
        raise AssertionError("Tuza adapter did not reconstruct parent formal object")
    return obj

def parse_vixra(source: dict, text: str) -> SemanticObject:
    lower=text.lower()
    compact=re.sub(r"\s+","",lower)
    required=[
        "quantum energy levels and riemann zeros",
        "imaginary part of the energy",
        "real precisely on the critical line",
    ]
    missing=[x for x in required if x not in lower]
    if missing or "t(1-2" not in compact:
        raise ValueError("viXra extraction contract not satisfied")
    obj=MathClaimPayload(
        claim_id=source["claim_id"],
        dialect="real-arithmetic-claim-v0",
        context=(("sigma", "Real"), ("t", "Real")),
        assumptions=("0 < sigma < 1", "t != 0", "Im(E_rho)=t*(1-2*sigma)"),
        statement="Im(E_rho)=0 iff sigma=1/2",
        source_ref=source["source_id"] + "|" + source["source_url"],
    ).semantic_object()
    if obj.id != EXPECTED_VIXRA_FORMAL_ID:
        raise AssertionError("viXra adapter did not reconstruct parent formal object")
    return obj

def assert_rejected(fn, source: dict, text: str, label: str) -> None:
    try:
        fn(source,text)
    except ValueError:
        return
    raise AssertionError(f"negative extraction probe unexpectedly accepted: {label}")

def main() -> None:
    manifest=json.loads(MANIFEST.read_text())
    sources={s["source_id"]:s for s in manifest["sources"]}
    arxiv=sources["arxiv:2608.06538v1"]
    vixra=sources["vixra:2609.0064"]

    arxiv_text=textify((SRC_DIR/"arxiv-2608.06538v1.snapshot").read_bytes())
    vixra_text=textify((SRC_DIR/"vixra-2609.0064.snapshot").read_bytes())

    arxiv_formal=parse_tuza(arxiv,arxiv_text)
    vixra_formal=parse_vixra(vixra,vixra_text)
    arxiv_source=source_object(arxiv)
    vixra_source=source_object(vixra)

    # Exact semantic perturbation falsifiers: the adapter must fail closed.
    tuza_bound_perturbed, tuza_bound_replacements = re.subn(
        r"constant\\s+\\$?2\\$?\\s+is\\s+sharp",
        "constant 3 is sharp",
        arxiv_text,
        flags=re.I,
        count=1,
    )
    assert tuza_bound_replacements == 1
    assert_rejected(
        parse_tuza, arxiv, tuza_bound_perturbed, "tuza-bound-2-to-3"
    )
    assert_rejected(
        parse_tuza, arxiv,
        re.sub(r"maximum degree three","maximum degree two",arxiv_text,flags=re.I,count=1),
        "tuza-degree-3-to-2",
    )
    assert_rejected(
        parse_vixra, vixra,
        vixra_text.replace("t(1-2","t(1-3",1),
        "vixra-energy-coefficient-2-to-3",
    )
    assert_rejected(
        parse_vixra, vixra,
        re.sub(r"real precisely on the critical line","real possibly on the critical line",vixra_text,flags=re.I,count=1),
        "vixra-precise-to-possible",
    )

    evidence_ref="hosted:crystal-literature-extraction-adapter-v2"
    arxiv_relation=VerifiedClaimRelation(
        arxiv_source.id, arxiv_formal.id, "equivalent", (evidence_ref,)
    )
    vixra_relation=VerifiedClaimRelation(
        vixra_source.id, vixra_formal.id, "equivalent", (evidence_ref,)
    )

    contracts=[
        {
            "id":content_id({
                "source_id":arxiv["source_id"],
                "template":"tuza-sharpness-v0",
                "glossary":["tau=triangle edge cover","nu=edge-disjoint triangle packing","sharp bound=attained equality"],
            },prefix="extraction-adapter"),
            "source_id":arxiv["source_id"],
            "source_object_id":arxiv_source.id,
            "formal_object_id":arxiv_formal.id,
            "relation_id":arxiv_relation.id,
            "assumptions":["standard graph-theory meaning of sharpness"],
            "negative_probes":["2→3 bound","degree three→two"],
            "status":"WARRANTED_BOUNDED",
        },
        {
            "id":content_id({
                "source_id":vixra["source_id"],
                "template":"zeta-energy-critical-line-v0",
                "glossary":["Riemann critical line=Re(s)=1/2"],
            },prefix="extraction-adapter"),
            "source_id":vixra["source_id"],
            "source_object_id":vixra_source.id,
            "formal_object_id":vixra_formal.id,
            "relation_id":vixra_relation.id,
            "assumptions":["Riemann critical line means sigma=1/2"],
            "negative_probes":["coefficient 2→3","precisely→possibly"],
            "status":"WARRANTED_BOUNDED_CONDITIONAL_ON_GLOSSARY",
        },
    ]

    evidence={
        "schema":"mathgraph.crystal-literature-extraction-adapter-v2.qualified",
        "status":"QUALIFIED_BOUNDED",
        "parent_source_fidelity_head":PARENT,
        "contracts":contracts,
        "results":{
            "sources":2,
            "exact_parent_formal_ids_reconstructed":2,
            "source_to_formal_relations_qualified":2,
            "semantic_perturbation_falsifiers_rejected":4,
            "new_crystal_waist_fields":0,
            "new_claim_dialect_fields":0,
        },
        "epistemic_result":{
            "source_snapshots":"WARRANTED_BY_PARENT",
            "source_to_formal_adapter":"WARRANTED_ON_TWO_EXPLICIT_TEMPLATES",
            "formalized_mathematics":"WARRANTED_BY_INTAKE_PARENT",
            "generic_prose_extraction":"UNKNOWN",
        },
        "boundary":"Two explicit source templates only. This qualifies exact source-to-formal adapters, including declared glossary assumptions and perturbation falsifiers. It does not warrant generic natural-language theorem extraction or semantic equivalence for arbitrary prose.",
    }
    OUTDIR.mkdir(parents=True,exist_ok=True)
    RESULT.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    print("CRYSTAL_LITERATURE_EXTRACTION_ADAPTER_V2=QUALIFIED_BOUNDED")
    print(json.dumps(evidence,sort_keys=True))

if __name__=="__main__":
    main()
