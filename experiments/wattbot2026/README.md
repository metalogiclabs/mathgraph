# MathGraph × WattBot 2026 — V1 (candidate)

**Competition:** https://www.kaggle.com/competitions/WattBot2026

**Status:** CANDIDATE. No official 2026 dataset, verified training score, submission, or leaderboard claim is bundled. The PDF-to-page text, lexical retrieval, quote provenance and bounded arithmetic pipeline are implemented and covered by synthetic tests. These do not imply scientific claims are true or semantically entailed.

## Authority and objective

- Official data: `metadata.csv`, `train_QA.csv`, `test_Q.csv`, pinned PDFs and **official** `Score.py`; available to Kaggle participants who accept competition rules.
- Official score: 0.75 answer value + 0.20 citation F1 + 0.05 NA.
- 245 published train / 317 test at kickoff (dynamic; numbers may change).
- All protected test labels remain hidden. Never train on them, leak them or hand-code answers.
- Do **not** silently use the 2025 WattBot dataset. Never pass a proxy scorer as official.
- PDF files are not redistributed by Kaggle. Download once from the **pinned URLs** in the metadata, respecting publisher terms; do not mass crawl arXiv.
- Competition is CC BY-NC 4.0 for the data. Repository contains only code and synthetic tests, not competition documents or submissions.

## Run

```bash
pip install pymupdf pytest
# Place the six official competition files under ./data and pinned PDFs under ./pdfs/{id}.pdf
python wattbot.py ingest --metadata data/metadata.csv --pdf-dir pdfs --out chunks.jsonl
python wattbot.py retrieve --questions data/train_QA.csv --chunks chunks.jsonl --out contexts_train.jsonl --top-k 8
python wattbot.py retrieve --questions data/test_Q.csv --chunks chunks.jsonl --out contexts_test.jsonl --top-k 8
# Model or reviewer must produce one candidate per question using the JSONL contract below.
python wattbot.py assemble --questions data/train_QA.csv --metadata data/metadata.csv --chunks chunks.jsonl --candidates candidate_train.jsonl --out predictions_train.csv
python wattbot.py score --official-scorer data/Score.py --train-ground-truth data/train_QA.csv --train-predictions predictions_train.csv
pytest -q tests/test_wattbot.py
```

The `retrieve` command uses **only** `id` and `question` fields (not gold answers), and writes top-k deterministic BM25 hit texts with PDF page numbers and SHA256. PDF extraction is page-local and cannot read text inside all figures; no automatic figure/OCR capability is claimed. `ingest` fails if even one pinned PDF is missing.

## Candidate contract

A model/reviewer supplies JSONL, one row per question:

```json
{"id":"q1","answer":"about 119 household-years","answer_value":"119.26","ref_ids":["paper1","paper2"],"evidence":[{"ref_id":"paper1","page":1,"quote":"1,287 MWh"},{"ref_id":"paper2","page":3,"quote":"35,000 US households used 377,685 MWh"}],"derivation":{"expression":"energy / (total / homes)","inputs":{"energy":{"value":"1287","evidence_index":0},"total":{"value":"377685","evidence_index":1},"homes":{"value":"35000","evidence_index":1}}},"explanation":"Source-specific arithmetic."}
```

The sample uses synthetic document IDs and values solely to show syntax. For unanswerable/unknown rows, use `"answer_value":"is_blank"`, empty `ref_ids` and `evidence`, and a nonempty explanation. Note an `is_blank` submission is a **choice**, not a proof of unanswerability.

`assemble` checks: every ID exactly once, exact citation/evidence source sets, quote text located within the declared page of a pinned PDF, source URLs from metadata, and optional arithmetic with exact rational values grounded in the cited quotes (numeric output tolerance 0.1%). It rejects partial output rather than filling missing rows with guesses. It **does not** verify semantic implication, units, sampling methodology, independent physical measurement or figure-only evidence. Do not promote an assembled CSV to a verified scientific result.

## First decisive experiment after downloading official data

1. Freeze one exact official-data snapshot and record checksums (all six files, PDF corpus and commit).
2. Split training data into development and untouched holdout by question ID, stratifying evidence-type flags; inspect only development answers while tuning.
3. Evaluate retriever **gold citation recall@1/3/8** on holdout, then complete assembled predictions scored by **the official Score.py**. Compare abstention and math/cross-paper buckets separately.
4. Only then add an answer generator or dense reranker if retrieval recall or value accuracy provides a measurable residual. Ablate arithmetic/provenance checks rather than assuming they improve leaderboard scores.

**Current highest-leverage residual:** official 2026 data not yet accessible in this run; there is no real-score claim. Kaggle account owner must join competition / accept rules and provide the six files, or make them available in an authorized workspace.