from mathgraph.cross_prover_constructor_selector import (
    WARRANTED_SCHEMAS,
    select_constructor_schema,
)


CASES = {
    "ex_quad": (
        "EXISTS (x: real): FORALL (y: real): y^2 + x * y + 1 > 0",
        "explicit_witness",
    ),
    "ex_disc2": (
        "FORALL (x: real): FORALL (y: real): x^2 + y^2 <= 1 IMPLIES x + y <= 2",
        "quadratic_implication",
    ),
    "ex_quartic": (
        "FORALL (x: real): FORALL (y: real): x^4 + y^4 + 1 > x * y",
        "sum_of_squares",
    ),
    "ex_ell": (
        "FORALL (x: real): EXISTS (y: real): x^2 + x * y + y^2 >= 3 AND y > x",
        "explicit_witness",
    ),
    "ex_two": (
        "FORALL (x: real): EXISTS (y: real): y^2 = x^2 + 1 AND y > 0 AND y^2 - x^2 <= 1",
        "algebraic_root_witness",
    ),
}


def test_heldout2_structural_selection_matches_supplied_assignments():
    for _name,(surface,want) in CASES.items():
        out=select_constructor_schema(surface)
        assert out["status"]=="CANDIDATE_CONSTRUCTOR_SELECTION",out
        assert out["schema"]==want,out


def test_constructor_ablation_is_fail_closed():
    for _name,(surface,want) in CASES.items():
        available=sorted(set(WARRANTED_SCHEMAS)-{want})
        out=select_constructor_schema(surface,available_schemas=available)
        assert out["status"]=="UNKNOWN_MISSING_CONSTRUCTOR",out
        assert out["schema"]==want,out


def test_renaming_does_not_change_selection():
    a=select_constructor_schema(
        "FORALL (x: real): EXISTS (y: real): y^2 = x^2 + 1 AND y > 0"
    )
    b=select_constructor_schema(
        "FORALL (foo: real): EXISTS (bar: real): bar^2 = foo^2 + 1 AND bar > 0"
    )
    assert a["schema"]==b["schema"]=="algebraic_root_witness"


def test_qe_shapes_select_preexisting_classes_without_new_rules():
    e11=select_constructor_schema(
        "NOT (EXISTS (x: real): x^2 + 1 = 0)"
    )
    p9=select_constructor_schema(
        "FORALL (x: real): x^2 + 1 > 0"
    )
    assert e11["schema"]=="quantifier_witness_duality"
    assert p9["schema"]=="sum_of_squares"


def test_prover_internal_surface_stays_unknown():
    out=select_constructor_schema(
        "select(qdec(3, P1), (: 1 :))"
    )
    assert out["status"]=="UNKNOWN_OUTSIDE_OBJECT_LEVEL_BOUNDARY"
