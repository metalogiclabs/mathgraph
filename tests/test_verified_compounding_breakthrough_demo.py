import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
V81_PATH = ROOT / "experiments" / "verified_compounding_breakthrough_v81" / "run.py"
RUNNER_PATH = ROOT / "scripts" / "run_verified_compounding_breakthrough_demo.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v81_protocol_is_frozen_outside_prior_synthetic_grammars():
    v81 = load_module(V81_PATH, "v81_protocol")
    assert v81.FRESH_OPERATION_COUNT == 10
    assert v81.START_HORIZON == 2
    assert v81.MAX_HORIZON == 7
    assert v81.RETAINED_BUDGET == 5
    protocol = v81.build_protocol("developer-sha")
    assert protocol["action_grammar"] == "one_swap_drop_one_add_one_only"
    assert protocol["fresh_operation_count"] == 10
    assert protocol["no_retraining_after_fresh_generation"] is True
    assert v81.sha_doc(protocol) == v81.sha_doc(protocol)


def test_compounding_classifier_requires_equal_endpoint_and_causal_saving():
    v81 = load_module(V81_PATH, "v81_economics")
    signal = v81.classify_compounding(
        comparisons=[
            {
                "endpoint_equal": True,
                "cold_checks": 20,
                "warm_checks": 12,
                "ablation_restores_cost": True,
            },
            {
                "endpoint_equal": True,
                "cold_checks": 15,
                "warm_checks": 15,
                "ablation_restores_cost": False,
            },
        ]
    )
    assert signal["classification"] == "VERIFIED_COMPOUNDING_SIGNAL"
    assert signal["aggregate_warm_checks"] <= signal["aggregate_cold_checks"]

    accumulation = v81.classify_compounding(
        comparisons=[
            {
                "endpoint_equal": True,
                "cold_checks": 10,
                "warm_checks": 10,
                "ablation_restores_cost": False,
            }
        ]
    )
    assert accumulation["classification"] == "ACCUMULATION_ONLY"

    failed = v81.classify_compounding(
        comparisons=[
            {
                "endpoint_equal": False,
                "cold_checks": 10,
                "warm_checks": 1,
                "ablation_restores_cost": True,
            }
        ]
    )
    assert failed["classification"] == "FAIL"


def test_breakthrough_runner_parser_and_required_outputs():
    runner = load_module(RUNNER_PATH, "v81_runner")
    parser = runner.build_parser()
    args = parser.parse_args(["--opened-laws", "laws.txt", "--out-dir", "out", "--quick"])
    assert args.opened_laws == "laws.txt"
    assert args.out_dir == "out"
    assert args.quick is True
    assert set(runner.REQUIRED_OUTPUTS) == {
        "breakthrough_manifest.json",
        "breakthrough_report.md",
        "capability_blocks.jsonl",
        "verified_obstructions.jsonl",
        "development_transitions.jsonl",
        "historical_evidence_validation.json",
        "v81_fresh_result.json",
        "compounding_economics.json",
        "claim_boundary.json",
        "artifact_hashes.json",
    }
