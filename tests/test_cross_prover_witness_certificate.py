import json

from mathgraph.cross_prover_witness_certificate import (
    discover_witness_batch,
    render_lean_witness_file,
    compile_witness_bundle,
)


def test_witness_batch_closes_all_13_routed_surfaces():
    surfaces=[
        ("d_cubic","FORALL (c: real): EXISTS (x: real): x^3 - 3 * x + c = 0"),
        ("d_meet","EXISTS (x: real): EXISTS (y: real): x^2 + y^2 = 1 AND y = x^2"),
        ("d_inverse","FORALL (x: real): EXISTS (y: real): x * y = 1"),
        ("d_between","FORALL (x: real): FORALL (y: real): EXISTS (z: real): x < y IMPLIES (x < z AND z < y)"),
        ("d_cone","FORALL (x: real): FORALL (y: real): EXISTS (z: real): z^2 = x^2 + y^2"),
        ("d_square","FORALL (x: real): FORALL (y: real): EXISTS (z: real): FORALL (w: real): w^2 + z > x + y"),
        ("t_sqrt2","EXISTS (x: real): x^2 = 2"),
        ("ex_above","FORALL (x: real): EXISTS (y: real): y > x"),
        ("ex_zero","EXISTS (x: real): FORALL (y: real): x * y = 0"),
        ("ex_circle","FORALL (x: real): EXISTS (y: real): x^2 + y^2 = 1 OR x^2 > 1"),
        ("ex_circle2","EXISTS (x: real): FORALL (y: real): x^2 + y^2 > 1"),
        ("ex_line","FORALL (x: real): EXISTS (y: real): x + 2 * y = 1 AND y * y >= 0"),
        ("ex_three","FORALL (x: real): FORALL (y: real): EXISTS (z: real): z > x AND z > y"),
    ]
    routing={"rows":[
        {"theory":"demo" if name.startswith(("d_","t_")) else "examples",
         "formula":name,"normalized_surface":surface,
         "residual_class":"EXISTENTIAL_WITNESS","status":"UNKNOWN_UNSUPPORTED_GRAMMAR"}
        for name,surface in surfaces
    ]}
    d=discover_witness_batch(routing)
    assert d["input_witness_residual_count"]==13
    assert d["matched_count"]==13
    assert d["qualify_true_count"]==12
    assert d["reject_false_count"]==1
    assert d["unmatched_count"]==0
    reject=[x for x in d["matched"] if x["disposition"]=="REJECT_FALSE"]
    assert reject[0]["pvs_authority_formula"]=="d_no_inverse"


def test_witness_lean_file_contains_ivt_radicals_and_counterexample():
    routing={"rows":[{
        "theory":"demo","formula":"d_cubic",
        "normalized_surface":"FORALL (c: real): EXISTS (x: real): x^3 - 3 * x + c = 0",
        "residual_class":"EXISTENTIAL_WITNESS","status":"UNKNOWN_UNSUPPORTED_GRAMMAR"
    },{
        "theory":"demo","formula":"d_inverse",
        "normalized_surface":"FORALL (x: real): EXISTS (y: real): x * y = 1",
        "residual_class":"EXISTENTIAL_WITNESS","status":"UNKNOWN_UNSUPPORTED_GRAMMAR"
    }]}
    d=discover_witness_batch(routing)
    lean=render_lean_witness_file(d)
    assert "intermediate_value_Icc" in lean
    assert "not_all_reals_have_inverse" in lean


def test_witness_bundle_requires_zero_unmatched():
    routing={"rows":[{
        "theory":"x","formula":"mystery",
        "normalized_surface":"EXISTS (x: real): x^5 = 7",
        "residual_class":"EXISTENTIAL_WITNESS","status":"UNKNOWN_UNSUPPORTED_GRAMMAR"
    }]}
    d=discover_witness_batch(routing)
    try:
        compile_witness_bundle(d,evidence_refs=["run:test"])
    except ValueError:
        pass
    else:
        raise AssertionError("unmatched witness residual must fail closed")
