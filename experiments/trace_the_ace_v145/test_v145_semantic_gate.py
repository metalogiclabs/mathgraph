import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("v145_gate", ROOT / "run_v145_semantic_gate.py")
GATE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(GATE)


def test_exact_score_parser():
    got = GATE.parse_scores("0.7, 0.8, 0.1, 0.0, 0.2, 0, 0.9")
    assert np.allclose(got, [.7, .8, .1, 0, .2, 0, .9])


def test_parser_rejects_missing_fields():
    assert GATE.parse_scores("0.7, 0.8") is None


def test_prompt_is_bounded_and_target_conditioned():
    prompt = GATE.prompt_for("add fractions", "x" * 8000)
    assert "TARGET OBJECTIVE: add fractions" in prompt
    assert "middle omitted" in prompt
    assert len(prompt) < 7000
