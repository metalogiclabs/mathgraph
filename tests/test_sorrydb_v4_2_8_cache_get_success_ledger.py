from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/sorrydb_v4_2_8_cache_get_success_ledger.md"


def test_ledger_exists():
    assert DOC.exists()


def test_records_success_verdicts():
    text = DOC.read_text()
    assert "CACHE_GET_VERDICT=CACHE_GET_PASSED" in text
    assert "BASELINE_VERDICT=BASELINE_PASSED" in text
    assert "FINAL_VERDICT=BASELINE_PASSED" in text


def test_records_prior_obstruction():
    text = DOC.read_text()
    assert "OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY" in text
    assert "Mathlib.olean missing" in text


def test_does_not_overclaim_patch_success():
    text = DOC.read_text()
    assert "does not claim proof repair" in text.casefold()
    assert "accepted patches" in text


def test_names_next_frontier():
    text = DOC.read_text()
    assert "controlled SorryDB patch replay" in text
    assert "PATCH_ACCEPTED" in text
    assert "PATCH_REJECTED" in text
