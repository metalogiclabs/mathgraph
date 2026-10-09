"""Tests use synthetic fixtures; never mistake these for competition performance."""
import csv
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wattbot as w


def fixture(tmp_path):
    metadata = tmp_path / "metadata.csv"
    questions = tmp_path / "test_Q.csv"
    chunks = tmp_path / "chunks.jsonl"
    candidates = tmp_path / "candidates.jsonl"
    with metadata.open("w", newline="") as f:
        writer = csv.DictWriter(f, ["id", "url", "title"])
        writer.writeheader()
        writer.writerow(dict(id="paper1", url="https://example.org/v1.pdf", title="Energy"))
        writer.writerow(dict(id="paper2", url="https://example.org/v2.pdf", title="Households"))
    with questions.open("w", newline="") as f:
        writer = csv.DictWriter(f, ["id", "question", "answer_unit"])
        writer.writeheader()
        writer.writerow(dict(id="q1", question="How many household years?", answer_unit="years"))
        writer.writerow(dict(id="q2", question="Elephant weight?", answer_unit="kg"))
    w.write_jsonl(chunks, [
        dict(ref_id="paper1", url="https://example.org/v1.pdf", page=1,
             text="Model training uses 1,287 MWh of electricity."),
        dict(ref_id="paper2", url="https://example.org/v2.pdf", page=3,
             text="35,000 US households used 377,685 MWh per year."),
    ])
    good = dict(id="q1", answer="about 119 years", answer_value="119.26",
                ref_ids=["paper1", "paper2"],
                evidence=[dict(ref_id="paper1", page=1, quote="1,287 MWh"),
                          dict(ref_id="paper2", page=3, quote="35,000 US households used 377,685 MWh")],
                derivation={"expression": "energy / (total / homes)", "inputs": {
                    "energy": dict(value="1287", evidence_index=0),
                    "total": dict(value="377685", evidence_index=1),
                    "homes": dict(value="35000", evidence_index=1)}},
                explanation="Cited arithmetic, synthetic fixture")
    blank = dict(id="q2", answer_value="is_blank", ref_ids=[], evidence=[],
                 explanation="Explicit abstention because there is no source")
    w.write_jsonl(candidates, [good, blank])
    return metadata, questions, chunks, candidates, good, blank


def test_valid_derived_and_blank(tmp_path):
    m, q, c, preds, _, _ = fixture(tmp_path)
    out = tmp_path / "submission.csv"
    w.assemble(str(q), str(m), str(c), str(preds), str(out))
    result = w.read_csv(out)
    assert len(result) == 2
    assert result[0]["answer_value"] == "119.26"
    assert "paper1" in result[0]["ref_id"] and "paper2" in result[0]["ref_id"]
    assert result[1]["answer_value"] == result[1]["ref_id"] == "is_blank"


def test_reject_forged_quote(tmp_path):
    m, q, c, preds, good, blank = fixture(tmp_path)
    good["evidence"][0]["quote"] = "Training uses 9,999 MWh"
    w.write_jsonl(preds, [good, blank])
    with pytest.raises(ValueError, match="not anchored"):
        w.assemble(str(q), str(m), str(c), str(preds), str(tmp_path / "out.csv"))


def test_reject_unsupported_citation(tmp_path):
    m, q, c, preds, good, blank = fixture(tmp_path)
    good["ref_ids"] = ["paper1"]
    w.write_jsonl(preds, [good, blank])
    with pytest.raises(ValueError, match="Citation set"):
        w.assemble(str(q), str(m), str(c), str(preds), str(tmp_path / "out.csv"))


def test_reject_wrong_derived_value(tmp_path):
    m, q, c, preds, good, blank = fixture(tmp_path)
    good["answer_value"] = "200"
    w.write_jsonl(preds, [good, blank])
    with pytest.raises(ValueError, match="Arithmetic mismatch"):
        w.assemble(str(q), str(m), str(c), str(preds), str(tmp_path / "out.csv"))


def test_reject_unanchored_arithmetic_input(tmp_path):
    m, q, c, preds, good, blank = fixture(tmp_path)
    good["derivation"]["inputs"]["energy"]["value"] = "1300"
    w.write_jsonl(preds, [good, blank])
    with pytest.raises(ValueError, match="not visible"):
        w.assemble(str(q), str(m), str(c), str(preds), str(tmp_path / "out.csv"))


def test_reject_evidence_on_blank(tmp_path):
    m, q, c, preds, good, blank = fixture(tmp_path)
    blank["ref_ids"] = ["paper1"]
    w.write_jsonl(preds, [good, blank])
    with pytest.raises(ValueError, match="must have no evidence"):
        w.assemble(str(q), str(m), str(c), str(preds), str(tmp_path / "out.csv"))


def test_reject_missing_candidate(tmp_path):
    m, q, c, preds, good, blank = fixture(tmp_path)
    w.write_jsonl(preds, [good])
    with pytest.raises(ValueError, match="exactly one"):
        w.assemble(str(q), str(m), str(c), str(preds), str(tmp_path / "out.csv"))


def test_retrieve_deterministically(tmp_path):
    m, q, chunks, preds, good, blank = fixture(tmp_path)
    hits = w.ranked("How much electricity did training consume?", w.jsonl(chunks))
    assert hits and hits[0]["ref_id"] == "paper1"
    assert hits == w.ranked("How much electricity did training consume?", w.jsonl(chunks))


def test_arithmetic_grammar_rejects_unsafe():
    from fractions import Fraction
    with pytest.raises(ValueError, match="Unsupported"):
        w.calculate("__import__('os').system('echo bad')", {})
    assert w.calculate("1287 / (377685 / 35000)", {}) > Fraction(119)


def test_pdf_ingestion(tmp_path):
    fitz = pytest.importorskip("fitz")
    file = tmp_path / "paper1.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Measured 1287 MWh in 2026.")
    doc.save(file)
    doc.close()
    chunks = w.chunks_from_pages("paper1", "https://example.org/v1.pdf", file)
    assert chunks[0]["page"] == 1
    assert "1287 MWh" in chunks[0]["text"]
    assert len(chunks[0]["pdf_sha256"]) == 64
