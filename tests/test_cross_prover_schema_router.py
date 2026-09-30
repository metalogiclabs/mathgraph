from mathgraph.cross_prover_schema_router import (
    alpha_normalize_surface,
    route_surface,
)


def test_alpha_normalization_ignores_binder_names_and_paired_binders():
    a=alpha_normalize_surface(
        "FORALL (alpha, beta: real): EXISTS (gamma: real): "
        "gamma > alpha AND gamma > beta"
    )
    b=alpha_normalize_surface(
        "FORALL (x: real): FORALL (y: real): EXISTS (z: real): "
        "z > x AND z > y"
    )
    assert a==b


def test_routes_all_eight_heldout_residual_shapes_without_theorem_names():
    rows={
        "t_between":(
            "(FORALL (a: real): FORALL (b: real): EXISTS (c: real): "
            "c > a AND c < b) IMPLIES FALSE",
            "NEW_EXACT_SCHEMA","adversarial_quantifier_refutation@1",(),
        ),
        "t_sqrt":(
            "(EXISTS (a: real): FORALL (b: real): EXISTS (c: real): "
            "c * c = b - a) IMPLIES FALSE",
            "NEW_EXACT_SCHEMA","adversarial_quantifier_refutation@1",(),
        ),
        "t_shift":(
            "FORALL (a: real): EXISTS (b: real): FORALL (c: real): "
            "c * c + b > a",
            "DERIVED_CONSEQUENCE","square_shift_specialization@1",
            ("real.square_shift_dominates@1",),
        ),
        "t_sos":(
            "FORALL (a: real): FORALL (b: real): FORALL (c: real): "
            "a^2 + b^2 + c^2 >= 2 * a * b",
            "DERIVED_CONSEQUENCE","amgm_square_extension@1",
            ("real.amgm2@1",),
        ),
        "t_sphere":(
            "FORALL (a: real): FORALL (b: real): EXISTS (c: real): "
            "a^2 + b^2 + c^2 = 1 OR a^2 + b^2 > 1",
            "DERIVED_CONSEQUENCE","root_circle_composition@1",
            ("real.sum_squares_has_root@1","real.circle_or_outside@1"),
        ),
        "e4_above":(
            "FORALL (a: real): FORALL (b: real): FORALL (c: real): "
            "EXISTS (d: real): d > a AND d > b AND d > c",
            "DERIVED_CONSEQUENCE","finite_upper_bound_fold@1",
            ("real.common_upper_bound2@1",),
        ),
        "e4_between":(
            "(FORALL (a: real): FORALL (b: real): FORALL (c: real): "
            "EXISTS (d: real): d > a AND d > b AND d < c) IMPLIES FALSE",
            "NEW_EXACT_SCHEMA","adversarial_quantifier_refutation@1",(),
        ),
        "e4_sum":(
            "FORALL (a: real): EXISTS (b: real): FORALL (c: real): "
            "EXISTS (d: real): d > a + b + c",
            "DERIVED_CONSEQUENCE","nested_unbounded_above@1",
            ("real.unbounded_above@1",),
        ),
    }
    for name,(surface,kind,schema,deps) in rows.items():
        route=route_surface(surface)
        assert route is not None,name
        assert route.route_kind==kind,(name,route)
        assert route.schema_id==schema,(name,route)
        assert route.dependencies==deps,(name,route)


def test_upper_bound_fold_generalizes_arity():
    route=route_surface(
        "FORALL (a: real): FORALL (b: real): FORALL (c: real): "
        "FORALL (d: real): EXISTS (w: real): "
        "w > a AND w > b AND w > c AND w > d"
    )
    assert route is not None
    assert route.schema_id=="finite_upper_bound_fold@1"
    assert route.dependencies==("real.common_upper_bound2@1",)


def test_rejects_unrelated_false_controls_and_unseen_shapes():
    controls=[
        "FORALL (x: real): EXISTS (y: real): x * y = 1",
        "FORALL (x: real): FORALL (y: real): x^2 + y^2 >= 3 * x * y",
        "EXISTS (x: real): x^3 = 2",
    ]
    assert all(route_surface(x) is None for x in controls)
