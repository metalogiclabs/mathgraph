import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from mathgraph.autonomous_compounding_engine import AutonomousCompoundingConfig, run_autonomous_compounding


def test_native_v2_tiny_demo_passes_gates_and_writes_artifacts(tmp_path):
    out_dir = tmp_path / "native"
    summary = run_autonomous_compounding(
        AutonomousCompoundingConfig(
            out_dir=out_dir,
            tiny_demo=True,
            finite_core_mode="native_v2",
            episodes=3,
            sample_pairs=80,
            repair_budget=20,
            max_n=3,
            seed=20260524,
            write_report=True,
        )
    )

    assert summary["autonomous_facade"] is True
    assert summary["finite_core_mode"] == "native_v2"
    assert summary["serious_path_uses_finite_recovery_core"] is True
    assert summary["all_gates_passed"] is True
    assert summary["repair_final_yield"] >= summary["generic_final_yield"]
    assert summary["repair_final_residuals"] <= summary["generic_final_residuals"]
    assert summary["lawbook_reuse_yield"] >= summary["repair_final_yield"]
    assert summary["true_contamination_count"] == 0
    assert summary["terminal_claims_from_advisory_count"] == 0
    assert summary["failed_search_promoted_true_count"] == 0

    required = [
        "autonomous_compounding_summary.json",
        "episode_metrics.csv",
        "gate_results.csv",
        "pair_features.csv",
        "true_pair_features.csv",
        "constructor_manifest.csv",
        "constructor_family_recommendations.csv",
        "pair_recovery_matrix_summary.csv",
        "generic_route.csv",
        "residual_repair_route.csv",
        "lawbook_reuse_route.csv",
        "compact_atlas_route.csv",
        "obstruction_atlas.csv",
        "residual_queue_after.csv",
        "terminal_form_audit.csv",
        "lawbook.sqlite",
        "autonomous_compounding_report.md",
    ]
    for name in required:
        path = Path(summary["artifacts"][name])
        assert path.exists(), name

    with sqlite3.connect(summary["artifacts"]["lawbook.sqlite"]) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"run_summaries", "episode_metrics", "residual_obstructions", "terminal_audit"}.issubset(tables)


def test_native_v2_cli_emits_json_summary(tmp_path):
    out_dir = tmp_path / "cli-native"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_autonomous_compounding_engine.py",
            "--out-dir",
            str(out_dir),
            "--tiny-demo",
            "--finite-core-mode",
            "native_v2",
            "--episodes",
            "3",
            "--sample-pairs",
            "80",
            "--repair-budget",
            "20",
            "--max-n",
            "3",
            "--seed",
            "20260524",
            "--write-report",
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    summary = json.loads(result.stdout)
    assert summary["finite_core_mode"] == "native_v2"
    assert summary["all_gates_passed"] is True
    assert summary["true_contamination_count"] == 0
    assert Path(summary["artifacts"]["lawbook.sqlite"]).exists()
