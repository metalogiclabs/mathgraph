from __future__ import annotations

import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_WEIGHTS = {
    "harvest": {
        "certificate": 2.0,
        "obstruction": 0.8,
        "compression": 1.0,
        "projection": 0.6,
        "reuse": 1.6,
        "novelty": 0.4,
        "cost": 1.2,
        "duplicate": 1.0,
        "overfit": 0.8,
        "foreign": 1.0,
    },
    "frontier": {
        "certificate": 0.8,
        "obstruction": 1.8,
        "compression": 1.8,
        "projection": 1.0,
        "reuse": 0.8,
        "novelty": 1.5,
        "cost": 0.8,
        "duplicate": 0.7,
        "overfit": 0.9,
        "foreign": 0.8,
    },
    "architectonic": {
        "certificate": 0.6,
        "obstruction": 1.0,
        "compression": 1.7,
        "projection": 2.0,
        "reuse": 1.5,
        "novelty": 1.2,
        "cost": 0.6,
        "duplicate": 0.8,
        "overfit": 0.8,
        "foreign": 0.7,
    },
    "balanced": {
        "certificate": 1.2,
        "obstruction": 1.2,
        "compression": 1.3,
        "projection": 1.1,
        "reuse": 1.1,
        "novelty": 0.9,
        "cost": 0.9,
        "duplicate": 0.8,
        "overfit": 0.8,
        "foreign": 0.8,
    },
}

CANDIDATES = [
    {
        "candidate_id": "rich",
        "expected_certificate_value": 0.5,
        "expected_obstruction_value": 0.2,
        "expected_residual_compression": 0.3,
        "expected_projection_gain": 0.4,
        "expected_bridge_value": 0.1,
        "expected_reuse": 0.6,
        "expected_constructor_reuse": 0.2,
        "novelty_score": 0.7,
        "verification_cost": 0.25,
        "duplicate_risk": 0.1,
        "overfit_risk": 0.05,
        "foreign_moisture_risk": 0.2,
    },
    {
        "candidate_id": "simple",
        "expected_certificate_value": 1.0,
        "verification_cost": 0.5,
    },
]

EXPECTED_RANKING = {
    "harvest": {
        "scores": [2.68, 1.4],
        "probabilities": [0.8320183851339245, 0.1679816148660755],
    },
    "frontier": {
        "scores": [3.015, 0.4],
        "probabilities": [0.9633410534482792, 0.0366589465517208],
    },
    "architectonic": {
        "scores": [3.6399999999999997, 0.3],
        "probabilities": [0.9848576252587378, 0.01514237474126237],
    },
    "balanced": {
        "scores": [2.7849999999999997, 0.75],
        "probabilities": [0.9271525103848874, 0.07284748961511259],
    },
}


def _protocol_module(name: str):
    return importlib.import_module(f"mathgraph_protocol.{name}")


def test_package_imports_without_mathgraph_or_optional_scientific_modules() -> None:
    code = f"""
import importlib.abc
import json
import sys

sys.path.insert(0, {str(ROOT)!r})

class BlockedImports(importlib.abc.MetaPathFinder):
    blocked = {{"mathgraph", "numpy", "pandas", "matplotlib"}}

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in self.blocked:
            raise ImportError(f"blocked optional dependency: {{fullname}}")
        return None

sys.meta_path.insert(0, BlockedImports())
import mathgraph_protocol
print(json.dumps({{"exports": sorted(mathgraph_protocol.__all__), "mathgraph_loaded": "mathgraph" in sys.modules}}))
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-c", code],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["mathgraph_loaded"] is False
    assert {
        "DuplicateKeyError",
        "NonFiniteNumberError",
        "default_weights",
        "rank_candidates",
        "score_candidate",
        "softmax",
        "strict_json_load",
        "strict_json_loads",
    } <= set(payload["exports"])


def test_strict_json_rejects_duplicate_keys() -> None:
    json_strict = _protocol_module("json_strict")
    with pytest.raises(json_strict.DuplicateKeyError, match="duplicate JSON object key: a"):
        json_strict.strict_json_loads('{"a": 1, "a": 2}')


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e999"])
def test_strict_json_rejects_nonfinite_numbers(token: str) -> None:
    json_strict = _protocol_module("json_strict")
    with pytest.raises(json_strict.NonFiniteNumberError, match="non-finite JSON number"):
        json_strict.strict_json_loads(f'{{"value": {token}}}')


def test_policy_weights_match_existing_scheduler_exactly() -> None:
    ranking = _protocol_module("discovery_ranking")
    assert {mode: ranking.default_weights(mode) for mode in EXPECTED_WEIGHTS} == EXPECTED_WEIGHTS


@pytest.mark.parametrize("mode", ["harvest", "frontier", "architectonic", "balanced"])
def test_scores_and_probabilities_match_existing_scheduler_exactly(mode: str) -> None:
    ranking = _protocol_module("discovery_ranking")
    weights = ranking.default_weights(mode)
    scores = [ranking.score_candidate(candidate, weights) for candidate in CANDIDATES]
    probabilities = ranking.softmax(scores, beta=1.25)
    ranked = ranking.rank_candidates(CANDIDATES, weights=weights, beta=1.25)

    assert scores == EXPECTED_RANKING[mode]["scores"]
    assert probabilities == EXPECTED_RANKING[mode]["probabilities"]
    assert [row.candidate_id for row in ranked] == ["rich", "simple"]
    assert [row.score for row in ranked] == EXPECTED_RANKING[mode]["scores"]
    assert [row.probability for row in ranked] == EXPECTED_RANKING[mode]["probabilities"]


def test_rank_candidates_uses_candidate_id_as_stable_tie_breaker() -> None:
    ranking = _protocol_module("discovery_ranking")
    candidates = [
        {"candidate_id": "tie_b"},
        {"candidate_id": "tie_a"},
        {"candidate_id": "tie_c"},
    ]
    ranked = ranking.rank_candidates(candidates, weights=ranking.default_weights("balanced"), beta=1.0)
    assert [(row.candidate_id, row.score, row.probability) for row in ranked] == [
        ("tie_a", 0.0, 1.0 / 3.0),
        ("tie_b", 0.0, 1.0 / 3.0),
        ("tie_c", 0.0, 1.0 / 3.0),
    ]
