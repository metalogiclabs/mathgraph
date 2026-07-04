from pathlib import Path

DOC = Path("docs/sorrydb_v4_3_1_accepted_patch_replay_ledger.md")


def text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_records_two_patch_acceptances():
    t = text()
    assert t.count("PATCH_ACCEPTED") >= 3
    assert "Accepted replay 1" in t
    assert "Accepted replay 2" in t


def test_records_exact_patch_snippets():
    t = text()
    assert "exact Nat.le_add_right n 1" in t
    assert "exact Nat.succ_le_succ (Nat.le_add_right n 1)" in t


def test_records_baseline_and_restore():
    t = text()
    assert "baseline_verdict=BASELINE_PASSED" in t
    assert "line 97 restored to sorry" in t
    assert "line 99 restored to sorry" in t


def test_records_obstruction_learning():
    t = text()
    assert "OBSTRUCTED_PATCH_TARGET_MISSING" in t
    assert "source file itself became the trust boundary" in t


def test_bounded_claims():
    t = text()
    assert "does not claim" in t
    assert "general proof repair" in t
    assert "upstream submission" in t
