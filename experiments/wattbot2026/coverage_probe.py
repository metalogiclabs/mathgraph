#!/usr/bin/env python3
"""Train-development-selected 4/8/16-paper follow-up coverage experiment.

Evidence boundary: Kaggle official 2026 train labels; never test labels.
The split is fixed from question IDs before selecting sources. Earlier
exploratory whole-training analyses mean this is NOT an untouched global
competition holdout; this follow-up is EXPLORATORY on an already-seen holdout, not pristine prospective evidence.
Downloads are constrained to up to twenty-four pinned arXiv papers and kept ephemeral.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
import time
from urllib.parse import urlparse
import zipfile
import requests

from pdf_probe import download_one
from train_probe import load_csv, parse_refs, score_metadata
from wattbot import chunks_from_pages, ranked

SALT = "wattbot-2026-source-recall-fixed-split-v1"
ARXIV_HOSTS = {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}


def is_holdout(question_id: str) -> bool:
    digest = hashlib.sha256((SALT + "|" + str(question_id)).encode()).digest()
    return int.from_bytes(digest[:8], "big") % 4 == 0


def source_rank(question: str, chunks: list[dict], k: int) -> set[str]:
    """Baseline PDF-chunk ranking with unique-source deduplication."""
    seen = []
    # Retrieve all possible chunks: limit not needed at this pilot size.
    for chunk in ranked(question, chunks, len(chunks)):
        ref_id = chunk["ref_id"]
        if ref_id not in seen:
            seen.append(ref_id)
        if len(seen) >= k:
            break
    return set(seen)


def evaluate(rows: list[dict], metadata: list[dict],
             all_pdf_chunks: dict[str, list[dict]], selected: list[str]) -> dict:
    docs = {doc_id for doc_id in selected if doc_id in all_pdf_chunks}
    extras = [chunk for doc_id in selected
              for chunk in all_pdf_chunks.get(doc_id, [])]
    # Keep ALL sources represented via metadata, including uncovered papers.
    meta_chunks = [{
        "ref_id": d["id"], "url": d["url"], "page": 0,
        "text": " ".join(str(d.get(k, "") or "")
                         for k in ("title", "citation", "year", "venue"))
    } for d in metadata]
    hybrid = meta_chunks + extras
    results = {}
    with_refs = [(r, set(parse_refs(r.get("ref_id", ""))))
                 for r in rows if parse_refs(r.get("ref_id", ""))]
    all_covered = [(r, expected) for r, expected in with_refs
                   if expected <= docs]
    any_covered = sum(bool(expected & docs) for _, expected in with_refs)
    for k in (1, 3, 8):
        total = len(with_refs)
        base_any = base_all = hybrid_any = hybrid_all = 0
        cond_base_any = cond_hybrid_any = 0
        for row, expected in with_refs:
            q = row["question"]
            baseline = set(score_metadata(q, metadata, top_k=k))
            augmented = source_rank(q, hybrid, k)
            base_any += bool(baseline & expected)
            base_all += expected <= baseline
            hybrid_any += bool(augmented & expected)
            hybrid_all += expected <= augmented
            if expected <= docs:
                cond_base_any += bool(baseline & expected)
                cond_hybrid_any += bool(augmented & expected)
        cond = len(all_covered)
        results[str(k)] = {
            "answerable_holdout_rows": total,
            "metadata_any": round(base_any / total, 4) if total else None,
            "hybrid_any": round(hybrid_any / total, 4) if total else None,
            "metadata_all": round(base_all / total, 4) if total else None,
            "hybrid_all": round(hybrid_all / total, 4) if total else None,
            "conditional_covered_rows": cond,
            "conditional_metadata_any": round(cond_base_any / cond, 4) if cond else None,
            "conditional_hybrid_any": round(cond_hybrid_any / cond, 4) if cond else None,
        }
    return {
        "selected_papers": len(selected),
        "downloaded_valid_papers": len(docs),
        "pdf_chunks": len(extras),
        "answerable_holdout_any_gold_in_pdf_set": any_covered,
        "answerable_holdout_all_gold_in_pdf_set": len(all_covered),
        "scores": results
    }


def run(official_zip: str, max_docs: int = 16) -> None:
    if max_docs != 16:
        raise ValueError("This coverage experiment requires 16 pinned PDFs.")
    with zipfile.ZipFile(official_zip) as z:
        meta = load_csv(z, "metadata.csv")
        train = load_csv(z, "train_QA.csv")
    metadata = {d["id"]: d for d in meta}
    dev = [r for r in train if not is_holdout(r["id"])]
    hold = [r for r in train if is_holdout(r["id"])]
    if not dev or not hold:
        raise ValueError("Fixed split yielded an empty partition")
    # Select downloaded papers USING DEVELOPMENT LABELS ONLY.
    refs = Counter(ref for r in dev for ref in parse_refs(r.get("ref_id", "")))
    source_list = sorted(
        (doc_id for doc_id in refs if doc_id in metadata
         and (urlparse(metadata[doc_id]["url"]).hostname or "").lower() in ARXIV_HOSTS),
        key=lambda doc_id: (-refs[doc_id], doc_id)
    )
    selected = source_list[:max_docs]
    print("COVERAGE16_BOUNDARY=" + json.dumps({
        "salt_sha256": hashlib.sha256(SALT.encode()).hexdigest(),
        "dev_rows": len(dev), "holdout_rows": len(hold),
        "selected_using": "DEV REF_ID LABELS ONLY",
        "selected_count": len(selected),
        "training_rows_inspected_for_source_selection": len(dev),
        "boundary":"Reused previously inspected holdout: exploratory transfer, not untouched new evidence"
    }, sort_keys=True))
    downloaded = {}
    failure_types = Counter()
    digests = []
    with tempfile.TemporaryDirectory(prefix="mathgraph_wattbot_holdout_") as folder:
        for i, doc_id in enumerate(selected):
            if i:
                time.sleep(3.1)
            path = Path(folder) / f"source_{i}.pdf"
            try:
                digest, _ = download_one(metadata[doc_id]["url"], path)
                chunks = chunks_from_pages(doc_id, metadata[doc_id]["url"], path)
                if not chunks:
                    raise ValueError("No extractable PDF text")
                downloaded[doc_id] = chunks
                digests.append(digest)
            except (requests.RequestException, RuntimeError, OSError, ValueError) as exc:
                failure_types[type(exc).__name__] += 1
    print("COVERAGE16_PAPER_ACQUISITION=" + json.dumps({
        "attempted": len(selected),
        "valid_and_text_extractable": len(downloaded),
        "failure_types": dict(failure_types),
        "pdf_checksum_manifest_sha256": hashlib.sha256("\n".join(digests).encode()).hexdigest(),
    }, sort_keys=True))
    for n in (4, 8, 16):
        if n > max_docs:
            continue
        selected_group = selected[:n]
        print("COVERAGE16_RETRIEVAL_"+str(n)+"_PAPERS="+json.dumps(
            evaluate(hold, meta, downloaded, selected_group), sort_keys=True))


def self_test() -> None:
    assert is_holdout("example-id") == is_holdout("example-id")
    assert isinstance(is_holdout("example-id"), bool)
    assert source_rank("123 electricity", [{"ref_id":"a", "page":1, "text":"123 electricity"},
                                           {"ref_id":"a", "page":2, "text":"electricity"},
                                           {"ref_id":"b", "page":1, "text":"123"}], 2) == {"a","b"}
    print("COVERAGE16_SELF_TEST=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--official-zip")
    p.add_argument("--max-docs", type=int, default=16)
    p.add_argument("--self-test", action="store_true")
    a = p.parse_args()
    if a.self_test:
        self_test()
    elif a.official_zip:
        run(a.official_zip, a.max_docs)
    else:
        p.error("Provide --official-zip or --self-test")
