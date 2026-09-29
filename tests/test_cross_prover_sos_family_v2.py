import json
from pathlib import Path

from mathgraph.cross_prover_sos_certificate import (
    discover_binary_quadratic_sos,
    render_lean_sos_proof,
    verify_sos_certificate,
)

MANIFEST=Path("experiments/crystal_cross_prover_sos_family_v2/manifest.json")


def _cases():
    return json.loads(MANIFEST.read_text())["cases"]


def test_true_pvs_family_compiles_to_exact_rational_sos():
    cases={x["id"]:x for x in _cases()}
    amgm=discover_binary_quadratic_sos(cases["real.amgm2@1"]["claim"])
    sos=discover_binary_quadratic_sos(cases["real.sumSquares2@1"]["claim"])
    assert amgm is not None
    assert sos is not None
    assert verify_sos_certificate(cases["real.amgm2@1"]["claim"],amgm)
    assert verify_sos_certificate(cases["real.sumSquares2@1"]["claim"],sos)

    assert amgm.to_dict()=={
        "type":"sum_of_weighted_linear_squares",
        "components":[{
            "type":"weighted_linear_square",
            "x":"1","y":"-1","constant":"0","weight":"1",
        }],
    }
    assert sos.to_dict()=={
        "type":"sum_of_weighted_linear_squares",
        "components":[
            {
                "type":"weighted_linear_square",
                "x":"1","y":"0","constant":"0","weight":"1",
            },
            {
                "type":"weighted_linear_square",
                "x":"0","y":"1","constant":"0","weight":"1",
            },
        ],
    }


def test_false_pvs_control_is_rejected_before_consumer_proof():
    case=next(x for x in _cases() if x["id"]=="real.amgm3.false-control@1")
    assert discover_binary_quadratic_sos(case["claim"]) is None


def test_generated_lean_proofs_are_certificate_only():
    for case in _cases():
        if case["expected"]!="TRUE":
            continue
        cert=discover_binary_quadratic_sos(case["claim"])
        proof=render_lean_sos_proof(cert)
        assert "sq_nonneg" in proof
        assert "nlinarith only" in proof
        assert "linarith?" not in proof


def test_family_promotion_rule_has_both_positive_and_negative_controls():
    cases=_cases()
    assert sum(x["expected"]=="TRUE" for x in cases)==2
    assert sum(x["expected"]=="FALSE" for x in cases)==1
