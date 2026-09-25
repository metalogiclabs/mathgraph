#!/usr/bin/env python3
"""Source-fidelity qualification for the first real literature intake."""

from __future__ import annotations

import hashlib
from html import unescape
import json
from pathlib import Path
import re
import urllib.request

from mathgraph.math_claim import MathClaimPayload

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evidence" / "crystal-literature-intake-smoke-v0" / "source_manifest.json"
OUTDIR = ROOT / "evidence" / "crystal-literature-source-fidelity-v1"
RESULT = OUTDIR / "result.json"
PARENT = "3eb314d50cefb25b187d33e3c80aa4f298e97e98"

def fetch(url: str) -> tuple[str, bytes]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MathGraph-Crystal-source-fidelity-v1/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.geturl(), r.read()

def fetch_first(urls: list[str]) -> tuple[str, bytes, list[str]]:
    errors=[]
    for url in urls:
        try:
            final,data=fetch(url)
            return final,data,errors
        except Exception as exc:
            errors.append(f"{url}: {type(exc).__name__}: {exc}")
    raise RuntimeError("all source fetches failed: " + " | ".join(errors))

def textify(data: bytes) -> str:
    text=data.decode("utf-8",errors="replace")
    text=re.sub(r"<script\b[^>]*>.*?</script>"," ",text,flags=re.I|re.S)
    text=re.sub(r"<style\b[^>]*>.*?</style>"," ",text,flags=re.I|re.S)
    text=re.sub(r"<[^>]+>"," ",text)
    text=unescape(text)
    return " ".join(text.split())

def require_markers(text: str, markers: list[str]) -> list[str]:
    lower=text.lower()
    missing=[m for m in markers if m.lower() not in lower]
    if missing:
        raise AssertionError(f"source markers missing: {missing}")
    return markers

def source_object_id(source: dict) -> str:
    return MathClaimPayload(
        claim_id=source["claim_id"] + ".source",
        dialect="literature-prose-extraction-v0",
        context=(),
        assumptions=(),
        statement=source["extracted_claim"],
        source_ref=source["source_id"] + "|" + source["source_url"],
    ).semantic_object().id

def main() -> None:
    manifest=json.loads(MANIFEST.read_text())
    sources={s["source_id"]:s for s in manifest["sources"]}
    OUTDIR.mkdir(parents=True,exist_ok=True)

    arxiv=sources["arxiv:2608.06538v1"]
    arxiv_url, arxiv_bytes, arxiv_errors = fetch_first([
        "https://arxiv.org/abs/2608.06538v1",
        "https://export.arxiv.org/api/query?id_list=2608.06538",
    ])
    arxiv_text=textify(arxiv_bytes)
    arxiv_markers=require_markers(arxiv_text,[
        "Tuza's conjecture for graphs of maximum degree at most seven",
        "constant",
        "sharp",
        "maximum degree",
        "three",
    ])
    (OUTDIR/"arxiv-2608.06538v1.snapshot").write_bytes(arxiv_bytes)

    vixra=sources["vixra:2609.0064"]
    vixra_url, vixra_bytes, vixra_errors = fetch_first([
        "https://vixra.org/mathph/",
        "https://www.rxiv.org/mathph/",
    ])
    vixra_text=textify(vixra_bytes)
    compact=re.sub(r"\s+","",vixra_text.lower())
    vixra_markers=require_markers(vixra_text,[
        "2609.0064",
        "Quantum Energy Levels and Riemann Zeros",
        "imaginary part of the energy",
        "critical line",
    ])
    if "t(1-2" not in compact:
        raise AssertionError("viXra source is missing the advertised t(1-2σ) formula prefix")
    (OUTDIR/"vixra-2609.0064.snapshot").write_bytes(vixra_bytes)

    evidence={
        "schema":"mathgraph.crystal-literature-source-fidelity-v1.qualified",
        "status":"QUALIFIED_BOUNDED",
        "parent_literature_intake_head":PARENT,
        "source_checks":[
            {
                "source_id":arxiv["source_id"],
                "requested_url":"https://arxiv.org/abs/2608.06538v1",
                "resolved_url":arxiv_url,
                "snapshot_sha256":hashlib.sha256(arxiv_bytes).hexdigest(),
                "snapshot_bytes":len(arxiv_bytes),
                "markers":arxiv_markers,
                "fallback_errors":arxiv_errors,
                "source_object_id":source_object_id(arxiv),
                "verdict":"WARRANTED_EXPLICIT_SOURCE_MATCH",
            },
            {
                "source_id":vixra["source_id"],
                "requested_url":"https://vixra.org/mathph/",
                "resolved_url":vixra_url,
                "snapshot_sha256":hashlib.sha256(vixra_bytes).hexdigest(),
                "snapshot_bytes":len(vixra_bytes),
                "markers":vixra_markers + ["t(1-2...)"],
                "fallback_errors":vixra_errors,
                "source_object_id":source_object_id(vixra),
                "verdict":"WARRANTED_EXPLICIT_SOURCE_MATCH",
            },
        ],
        "epistemic_result":{
            "source_presence_and_claim_markers":"WARRANTED_ON_FETCHED_SNAPSHOTS",
            "formalized_mathematics":"WARRANTED_BY_PARENT_INTAKE_SMOKE",
            "source_to_formal_semantic_equivalence":"CANDIDATE_INTERPRETATION",
        },
        "boundary":"This qualifies source identity/snapshot hashes and explicit claim-marker presence for the two smoke-test sources. It does not by itself prove that a prose-to-formal semantic translation is extensionally exact; that remains a separate extraction-adapter obligation.",
    }
    RESULT.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    print("CRYSTAL_LITERATURE_SOURCE_FIDELITY_V1=QUALIFIED_BOUNDED")
    print(json.dumps(evidence,sort_keys=True))

if __name__=="__main__":
    main()
