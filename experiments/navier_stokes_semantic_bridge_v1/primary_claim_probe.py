"""V4 primary-source intake and pinned Lean-declaration diagnostic.

This is a *source-identity/surface* checker, NOT a semantic theorem prover.
It requires SHA256-identified original PDF bytes and git-blob-identified Lean
files, and never produces a truth or argument-fidelity promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

PRIMARY_SHA256 = "0e779481c4da40bd28d1e642e1d8ca57447d129610df28dfa5a11e9af8ae228f"
INVERSE_GIT_BLOB = "c607eb6f2460a3ba55dc2218072cd504bf6253bf"
PRESSURE_GIT_BLOB = "542377decf40306a50ce2170783de99a384b8d41"
PRIMARY_URL = "https://cdn.openai.com/pdf/32d9f210-8b73-45e0-91bc-82a30aef8a9a/navier-stokes.pdf"
UPSTREAM_REF = "openai/NavierStokesAndEuler@f9e8bc5"


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise AssertionError(reason)


def extract_anchor(text: str, pattern: str, *, left: int = 300, right: int = 450) -> str:
    found = list(re.finditer(pattern, text, flags=re.IGNORECASE))
    require(len(found) == 1, f"anchor {pattern!r} occurs {len(found)} times")
    match = found[0]
    return text[max(0, match.start() - left): min(len(text), match.end() + right)]


def run(pdf: Path, inverse: Path, pressure: Path, out: Path) -> dict:
    require(digest(pdf.read_bytes()) == PRIMARY_SHA256, "primary PDF SHA256 mismatch")
    require(pdf.read_bytes()[:5] == b"%PDF-", "source is not a PDF")
    inv_blob = subprocess.check_output(["git", "hash-object", str(inverse)], text=True).strip()
    flux_blob = subprocess.check_output(["git", "hash-object", str(pressure)], text=True).strip()
    require(inv_blob == INVERSE_GIT_BLOB, "pinned inverse declaration blob mismatch")
    require(flux_blob == PRESSURE_GIT_BLOB, "pinned pressure-flux declaration blob mismatch")
    text = subprocess.check_output(["pdftotext", "-layout", str(pdf), "-"], text=True)
    require(len(text) > 200_000, "primary PDF extraction suspiciously short")
    pages = text.split("\f")
    require(len(pages) >= 160, "expected 166-page primary manuscript")
    page_results = {}
    for formula in ("8.19", "10.19"):
        anchor = r"\(\s*" + re.escape(formula) + r"\s*\)"
        matches = [i for i, page in enumerate(pages, start=1) if re.search(anchor, page)]
        require(len(matches) >= 1, f"primary PDF missing equation ({formula})")
        # Match ambiguity remains explicit; do not secretly select based on desired claim.
        page_results[formula] = {
            "page_hits": matches,
            "nearby_text_sha256": [digest(pages[i - 1].encode()) for i in matches],
        }
    # Preserve an independent *textual* corroboration of the source method.
    four_matches = [
        i for i, p in enumerate(pages, 1)
        if re.search(r"four\s+more\s+derivatives", p, flags=re.IGNORECASE)
    ]
    require(bool(four_matches), "primary manuscript does not contain the cited four-more-derivatives text")
    inv_text = inverse.read_text()
    begin = inv_text.find("theorem norm_derivativeWord_inverse_le")
    end = inv_text.find("theorem mixedJet_inverse_bound", begin)
    require(0 <= begin < end, "pinned inverse theorem anchors missing")
    inv_theorem = inv_text[begin:end]
    require(inv_theorem.count("SmoothFourierData.xJet (w.length + 5)") == 2,
            "inverse theorem is not exactly the claimed two five-jet premises")
    require("coefficient_seminorm_bound" in inv_theorem,
            "inverse proof has unexpected route")
    flux_text = pressure.read_text()
    begin = flux_text.find("theorem exists_uniform_actual_pressure_flux_bound")
    end = flux_text.find("end NavierStokesR3.PressureFlux", begin)
    require(0 <= begin < end, "pinned pressure-flux theorem anchors missing")
    flux_theorem = flux_text[begin:end]
    require("dissipationRoot (ComparisonCutoffs.cutoff R) (u - v) t / R" in flux_theorem,
            "pressure flux lacks the source-claimed gradient dependency")
    require("cutoffL6" in flux_theorem, "missing cutoffL6")
    # Limit exposed excerpts to their SHA256 identities, not a copied full manuscript.
    output = {
        "schema": "mathgraph.primary-claim-intake-v4",
        "primary_source": {"url": PRIMARY_URL, "sha256": PRIMARY_SHA256,
                           "pages_extracted": len([p for p in pages if p.strip()]),
                           "formula_anchors": page_results,
                           "four_more_derivatives_pages": four_matches},
        "formal_source": {"ref": UPSTREAM_REF, "inverse_git_blob": inv_blob,
                          "pressure_flux_git_blob": flux_blob,
                          "inverse_jet_order": "w.length + 5",
                          "inverse_order_occurrences": 2,
                          "pressure_flux_has_dissipation_root_over_R": True},
        "result": "VERIFIED_BYTE_IDENTITY_AND_SELECTED_SURFACE_MISMATCH",
        "claim_statement_semantic_equivalence": "UNKNOWN",
        "proof_argument_fidelity": "UNKNOWN",
        "nl_interpretation_independently_approved": False,
        "full_inverse_estimate_proved": False,
        "full_pressure_flux_implication_proved": False,
        "source_paper_mathematical_correctness": "UNKNOWN",
        "can_promote_truth": False,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    return output


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--pdf", type=Path, required=True)
    p.add_argument("--inverse", type=Path, required=True)
    p.add_argument("--pressure", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    data = run(a.pdf, a.inverse, a.pressure, a.out)
    print(json.dumps(data, sort_keys=True))


if __name__ == "__main__":
    main()
