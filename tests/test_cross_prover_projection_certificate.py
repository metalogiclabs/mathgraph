from mathgraph.cross_prover_projection_certificate import (
    discover_projection_batch,
    render_lean_projection_file,
)


SURFACES=[
("s_sqrt","OPAQUE_OR_NONPOLYNOMIAL","FORALL (x: nnreal, a: real): a = sqrt(x) AND a * a = x AND a > 1 IMPLIES x > 1"),
("s_fun","OPAQUE_OR_NONPOLYNOMIAL","FORALL (x: real, l: list[real]): f(x) > x^2 AND member(x, l) AND length(l) = 3 IMPLIES f(x) > -1"),
("s_disc","QUANTIFIED_PREMISE","FORALL (b: real): FORALL (c: real): (FORALL (z: real): z^2 + b * z + c > 0) IMPLIES b^2 < 4 * c"),
("s_root","EXISTENTIAL_CONSEQUENT","FORALL (x: real): x > 0 IMPLIES EXISTS (y: real): y * y = x"),
("s_alt_goal","EXISTENTIAL_CONSEQUENT","FORALL (a: real): a > 0 IMPLIES (FORALL (z: real): EXISTS (w: real): w * a > z)"),
("s_alt_hyp","QUANTIFIED_PREMISE","FORALL (c: real): (FORALL (z: real): EXISTS (w: real): w > z AND w * c > 1) IMPLIES c > 0"),
("s_posreal","SUBTYPE_RANGE","FORALL (x: posreal): x + 1 > 1"),
("s_sqrtpos","OPAQUE_OR_NONPOLYNOMIAL","FORALL (y: nnreal): sqrt(y) + 1 >= 1"),
("s_skip","OPAQUE_OR_NONPOLYNOMIAL","FORALL (x: real): (FORALL (z: real): g(z) <= 1) AND (x > 0 IMPLIES EXISTS (z: real): z * z = x) AND x > 2 IMPLIES x > 1"),
("s_mix","OPAQUE_OR_NONPOLYNOMIAL","FORALL (x: real, l: list[real]): P(x) AND cons?(l) AND (FORALL (z: real): f(z) >= 0) AND f(x) > x^2 AND x /= 0 IMPLIES f(x) > 0"),
("s_two","EXISTENTIAL_PREMISE","FORALL (a: real): (EXISTS (u, v: real): u * u + v * v = a) IMPLIES a >= 0"),
]


def test_projection_batch_matches_all_eleven():
    routing={"rows":[
        {"theory":"cad_star_ex","formula":name,"normalized_surface":surface,
         "residual_class":cls,"status":"UNKNOWN_UNSUPPORTED_GRAMMAR"}
        for name,cls,surface in SURFACES
    ]}
    d=discover_projection_batch(routing)
    assert d["input_target_count"]==11
    assert d["matched_count"]==11
    assert d["unmatched_count"]==0


def test_projection_file_keeps_opaque_symbols_only_as_assumptions():
    routing={"rows":[{
        "theory":"cad_star_ex","formula":"s_fun",
        "normalized_surface":SURFACES[1][2],
        "residual_class":"OPAQUE_OR_NONPOLYNOMIAL",
        "status":"UNKNOWN_UNSUPPORTED_GRAMMAR"
    }]}
    d=discover_projection_batch(routing)
    lean=render_lean_projection_file(d)
    assert "opaque_function_square_lower_bound" in lean
    assert "sq_nonneg x" in lean
