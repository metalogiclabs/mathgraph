from mathgraph.cross_prover_proof_instantiator import (
    instantiate_consumer,
    pvs_surface_to_lean,
    render_generated_consumers,
)


G1="EXISTS (x: real): x^2 - 1 = 0 AND x > 0"
G2="NOT (EXISTS (x: real): x^2 + 1 = 0 AND x > 0)"


def test_translation_of_bounded_real_surface():
    assert pvs_surface_to_lean(G1)=="∃ x : ℝ, x^2 - 1 = 0 ∧ x > 0"
    assert pvs_surface_to_lean(G2)=="¬ (∃ x : ℝ, x^2 + 1 = 0 ∧ x > 0)"


def test_explicit_witness_is_found_without_theorem_name_route():
    out=instantiate_consumer("renamed_positive_root",G1)
    assert out["status"]=="CANDIDATE_GENERATED_CONSUMER"
    assert out["schema"]=="explicit_witness"
    assert out["synthesis"]["witness"]==1
    assert "norm_num" in out["lean_proof"]


def test_negated_existential_generates_square_contradiction():
    out=instantiate_consumer("renamed_no_positive_root",G2)
    assert out["status"]=="CANDIDATE_GENERATED_CONSUMER"
    assert out["schema"]=="quantifier_witness_duality"
    assert "sq_nonneg x" in out["lean_proof"]


def test_missing_small_integer_witness_fails_closed():
    out=instantiate_consumer(
        "irrational_witness",
        "EXISTS (x: real): x^2 = 2 AND x > 0",
    )
    assert out["status"]=="UNKNOWN_NO_SMALL_INTEGER_WITNESS"


def test_internal_surface_fails_before_proof_generation():
    out=instantiate_consumer(
        "internal",
        "select(qdec(3, P1), (: 1 :))",
    )
    assert out["status"]=="UNKNOWN_NO_CONSTRUCTOR_SELECTION"


def test_renderer_emits_only_generated_consumers():
    rows=[
        instantiate_consumer("g1",G1),
        instantiate_consumer("g2",G2),
        instantiate_consumer("bad","EXISTS (x: real): x^2 = 2 AND x > 0"),
    ]
    lean=render_generated_consumers(rows)
    assert "auto_g1" in lean
    assert "auto_g2" in lean
    assert "auto_bad" not in lean
