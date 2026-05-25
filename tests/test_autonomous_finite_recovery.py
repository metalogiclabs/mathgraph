import numpy as np

from mathgraph.autonomous_finite_recovery import (
    FiniteRecoveryConfig,
    build_finite_recovery_core,
    evaluate_false_pairs,
    greedy_route,
    pair_recovery_matrix,
    residual_marginal_repair,
)


TOY_EQUATIONS = [
    "(x * y) = (y * x)",
    "(x * y) = x",
    "(x * y) = y",
    "x = x",
]


def test_finite_recovery_core_builds_constructor_manifest_and_cache():
    result = build_finite_recovery_core(TOY_EQUATIONS, FiniteRecoveryConfig(max_n=3, constructor_limit=20))

    assert result.constructor_count > 0
    assert result.equation_count == len(TOY_EQUATIONS)
    assert result.sat_cache.shape == (result.constructor_count, len(TOY_EQUATIONS))
    assert {"constructor_idx", "cid", "family", "n", "advisory_only", "can_promote_truth"}.issubset(
        result.constructor_manifest.columns
    )
    assert result.constructor_manifest["advisory_only"].all()
    assert not result.constructor_manifest["can_promote_truth"].any()


def test_recovery_counts_only_source_holds_and_target_violated():
    result = build_finite_recovery_core(TOY_EQUATIONS, FiniteRecoveryConfig(max_n=3, constructor_limit=20))
    pairs = [(0, 1), (0, 2)]
    matrix = pair_recovery_matrix(pairs, result.sat_cache)
    rows = evaluate_false_pairs(pairs, result.sat_cache, result.constructors)

    assert matrix.shape == (len(pairs), result.constructor_count)
    for pair_idx, (source, target) in enumerate(pairs):
        for constructor_idx in np.flatnonzero(matrix[pair_idx]):
            assert bool(result.sat_cache[constructor_idx, source])
            assert not bool(result.sat_cache[constructor_idx, target])
    assert {"pair_idx", "eq1_id", "eq2_id", "recovered", "best_constructor_idx"}.issubset(rows.columns)


def test_greedy_and_residual_repair_are_monotone():
    result = build_finite_recovery_core(TOY_EQUATIONS, FiniteRecoveryConfig(max_n=3, constructor_limit=20))
    matrix = pair_recovery_matrix([(0, 1), (0, 2), (1, 2)], result.sat_cache)
    _, generic_mask, _ = greedy_route(matrix, result.constructor_manifest, budget=2, seed=7)
    _, repair_mask, repair_route = residual_marginal_repair(matrix, generic_mask, result.constructor_manifest, budget=3, seed=7)

    assert int(repair_mask.sum()) >= int(generic_mask.sum())
    assert repair_route.empty or repair_route["advisory_only"].all()
    assert repair_route.empty or not repair_route["can_promote_truth"].any()
