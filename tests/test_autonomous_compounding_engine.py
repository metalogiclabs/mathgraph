from mathgraph.autonomous_compounding_engine import AutonomousCompoundingConfig, run_autonomous_compounding


def test_autonomous_tiny_demo_runs(tmp_path):
    summary = run_autonomous_compounding(
        AutonomousCompoundingConfig(out_dir=tmp_path / "run", tiny_demo=True, episodes=1, sample_pairs=20, repair_budget=4, max_n=3)
    )
    assert summary["autonomous_facade"] is True
    assert summary["serious_path_uses_finite_recovery_core"] is True
    assert summary["advisory_boundary_preserved"] is True
    assert summary["all_gates_passed"] is True
    assert summary["true_contamination_count"] == 0
    assert summary["terminal_claims_from_advisory_count"] == 0
    assert summary["failed_search_promoted_true_count"] == 0
    assert summary["repair_final_yield"] >= summary["generic_final_yield"]
    assert summary["repair_final_residuals"] <= summary["generic_final_residuals"]
    assert "lawbook.sqlite" in summary["artifacts"]
