import json
import subprocess
import sys
from pathlib import Path

from mathgraph.autonomous_compounding_engine import AutonomousCompoundingConfig, run_autonomous_compounding


def test_autonomous_summary_has_stable_safety_keys(tmp_path):
    summary = run_autonomous_compounding(
        AutonomousCompoundingConfig(
            out_dir=tmp_path / "stable",
            tiny_demo=True,
            episodes=2,
            sample_pairs=40,
            repair_budget=8,
            max_n=3,
            seed=20260524,
        )
    )

    for key in [
        "autonomous_facade",
        "serious_path_uses_finite_recovery_core",
        "terminal_contract",
        "terminal_audit",
        "advisory_boundary_preserved",
        "all_gates_passed",
        "true_contamination_count",
        "terminal_claims_from_advisory_count",
        "failed_search_promoted_true_count",
        "generic_final_yield",
        "repair_final_yield",
        "generic_final_residuals",
        "repair_final_residuals",
        "repair_gain_over_generic",
        "source_mode",
        "real_corpus_used",
        "artifacts",
    ]:
        assert key in summary
    assert summary["failed_search_promoted_true_count"] == 0
    assert summary["failed_search_promoted_true"] == 0


def test_autonomous_cli_prints_json_summary(tmp_path):
    out_dir = tmp_path / "cli"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_autonomous_compounding_engine.py",
            "--out-dir",
            str(out_dir),
            "--tiny-demo",
            "--episodes",
            "1",
            "--sample-pairs",
            "20",
            "--repair-budget",
            "4",
            "--max-n",
            "3",
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    summary = json.loads(result.stdout)
    assert summary["autonomous_facade"] is True
    assert summary["all_gates_passed"] is True
    assert summary["true_contamination_count"] == 0
