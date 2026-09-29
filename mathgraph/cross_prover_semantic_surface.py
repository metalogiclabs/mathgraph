"""Cross-prover semantic surface compiler for a bounded PVS↔Lean experiment.

The module deliberately separates:
1. source identity/provenance,
2. canonical proposition identity,
3. verifier evidence,
4. consumer-facing semantic capability.

It never treats a matching short name as evidence of semantic identity.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from mathgraph.crystal import SemanticObject, canonical_bytes


def _norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def canonical_claim(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    claim = manifest["canonical_claim"]
    if claim["id"] != "real.amgm2@1":
        raise ValueError("unsupported canonical claim")
    binders = claim["binders"]
    if binders != [
        {"name": "x", "sort": "real"},
        {"name": "y", "sort": "real"},
    ]:
        raise ValueError("unexpected binder surface")
    return claim


def render_pvs_claim(manifest: Mapping[str, Any]) -> str:
    canonical_claim(manifest)
    return (
        "FORALL (x: real): FORALL (y: real): "
        "x^2 + y^2 >= 2 * x * y"
    )


def render_lean_expression(manifest: Mapping[str, Any]) -> str:
    canonical_claim(manifest)
    return "x ^ 2 + y ^ 2 ≥ 2 * x * y"


def render_lean_file(manifest: Mapping[str, Any]) -> str:
    expr = render_lean_expression(manifest)
    return f"""import Mathlib

namespace CrystalCrossProverCAD

theorem amgm2_real (x y : ℝ) : {expr} := by
  nlinarith [sq_nonneg (x - y)]

end CrystalCrossProverCAD
"""


def extract_pvs_formula(source: str, formula_name: str) -> str:
    # The demo formula is one complete lemma statement with two prenex binders.
    pat = re.compile(
        rf"^\s*{re.escape(formula_name)}\s*:\s*LEMMA\s+"
        rf"(FORALL\s*\(x:\s*real\)\s*:\s*FORALL\s*\(y:\s*real\)\s*:\s*"
        rf"x\s*\^\s*2\s*\+\s*y\s*\^\s*2\s*>=\s*2\s*\*\s*x\s*\*\s*y)",
        re.MULTILINE,
    )
    m = pat.search(source)
    if not m:
        raise ValueError(f"formula {formula_name!r} not found on expected surface")
    return _norm_ws(m.group(1))


def verify_pvs_source_surface(
    manifest: Mapping[str, Any], source: str
) -> dict[str, Any]:
    expected = _norm_ws(render_pvs_claim(manifest))
    actual = extract_pvs_formula(source, str(manifest["pvs"]["formula"]))
    if actual != expected:
        raise AssertionError({"expected": expected, "actual": actual})
    return {
        "status": "EXACT_CANONICAL_SURFACE_MATCH",
        "canonical_claim_id": manifest["canonical_claim"]["id"],
        "pvs_formula": actual,
        "surface_sha256": hashlib.sha256(actual.encode("utf-8")).hexdigest(),
    }


@dataclass(frozen=True)
class CrossProverAuthority:
    pvs_replay_ref: str
    lean_replay_ref: str
    source_match_ref: str


def compile_cross_prover_capability(
    manifest: Mapping[str, Any],
    authority: CrossProverAuthority,
) -> SemanticObject:
    claim = canonical_claim(manifest)
    payload = canonical_bytes({
        "canonical_claim": claim,
        "pvs": {
            "repository": manifest["pvs"]["repository"],
            "commit": manifest["pvs"]["commit"],
            "theory": manifest["pvs"]["theory"],
            "formula": manifest["pvs"]["formula"],
            "source_blob_sha": manifest["pvs"]["source_blob_sha"],
            "proof_blob_sha": manifest["pvs"]["proof_blob_sha"],
            "pvs_release": manifest["pvs"]["pvs_release"],
            "nasalib_commit": manifest["pvs"]["nasalib_commit"],
        },
        "lean": manifest["lean"],
        "authority": {
            "pvs_replay_ref": authority.pvs_replay_ref,
            "lean_replay_ref": authority.lean_replay_ref,
            "source_match_ref": authority.source_match_ref,
        },
        "boundary": manifest["trust_boundary"],
    })
    return SemanticObject(
        type_id="cross-prover.verified-proposition@1",
        contract_version=1,
        payload=payload,
        interfaces=(
            "logic.closed-proposition.truth@1",
            "real.polynomial.amgm2@1",
            "provenance.cross-prover@1",
        ),
    )


def load_manifest(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
