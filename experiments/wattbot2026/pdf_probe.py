#!/usr/bin/env python3
"""Bounded pinned-source PDF acquisition pilot; no mass download or file publication.

Choose a few top-cited training references; log only aggregate availability,
content checksums and corpus-coverage diagnostics (no row/source text).
"""
from __future__ import annotations
from collections import Counter
import argparse
import hashlib
import io
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
import zipfile

import fitz
import requests

from train_probe import load_csv, parse_refs, score_metadata
from wattbot import chunks_from_pages, ranked

ARXIV = "arxiv.org"
USER_AGENT = "MathGraph-WattBot2026-Research/0.1 (noncommercial evaluation; limited requests)"
MAX_BYTES = 18 * 1024 * 1024


def pinned_pdf_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Source must be HTTPS")
    host = (parsed.hostname or "").lower()
    if host not in {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}:
        raise ValueError("Only arXiv is supported by the bounded pilot")
    path = parsed.path
    if path.startswith("/abs/"):
        paper_id = path[len("/abs/"):]
    elif path.startswith("/pdf/"):
        paper_id = path[len("/pdf/"):]
    else:
        raise ValueError("Not a recognized arXiv abs/pdf URL")
    paper_id = re.sub(r"\.pdf$", "", paper_id)
    # arxiv identifiers can be newer 2601.01234 or legacy quant-ph/0001001.
    if not re.fullmatch(r"(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?", paper_id):
        raise ValueError("Unrecognized arXiv paper identifier")
    return "https://arxiv.org/pdf/" + paper_id


def download_one(url: str, destination: Path) -> tuple[str, str]:
    pdf_url = pinned_pdf_url(url)
    # All redirects checked for HTTPS and an arxiv.org host, not third parties.
    session = requests.Session()
    try:
        response = session.get(pdf_url, headers={"User-Agent": USER_AGENT,
                               "Accept": "application/pdf"}, timeout=(8, 30),
                               stream=True, allow_redirects=True)
        response.raise_for_status()
        for history in list(response.history) + [response]:
            p = urlparse(history.url)
            if p.scheme != "https" or (p.hostname or "").lower() not in {
                    "arxiv.org", "www.arxiv.org", "export.arxiv.org"}:
                raise ValueError("Non-pinned redirect host")
        data = bytearray()
        for chunk in response.iter_content(chunk_size=65536):
            data += chunk
            if len(data) > MAX_BYTES:
                raise ValueError("PDF size cap exceeded")
        if not data.startswith(b"%PDF"):
            raise ValueError("Response is not PDF data")
        # Parseability is upstream of any retrieval claim.
        with fitz.open(stream=bytes(data), filetype="pdf") as doc:
            pages = len(doc)
            chars = sum(len(p.get_text()) for p in doc)
        destination.write_bytes(data)
        return hashlib.sha256(data).hexdigest(), f"pages={pages};text_chars={chars}"
    finally:
        session.close()


def pilot(zip_path: str, max_docs: int) -> None:
    if max_docs < 1 or max_docs > 8:
        raise ValueError("Pilot capped at 1..8 documents; no mass crawl")
    from tempfile import TemporaryDirectory
    with zipfile.ZipFile(zip_path) as z:
        meta = load_csv(z, "metadata.csv")
        train = load_csv(z, "train_QA.csv")
    docs = {str(m["id"]): m for m in meta}
    # Training labels used only for source prioritization, never as retrieval text.
    refs = [parse_refs(row.get("ref_id", "")) for row in train]
    counts = Counter(ref for row_refs in refs for ref in row_refs)
    candidates = [(c, d) for d, c in counts.items() if d in docs
                  and (urlparse(docs[d]["url"]).hostname or "").lower() in
                    {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}]
    candidates.sort(key=lambda x: (-x[0], x[1]))
    selected = [doc_id for _, doc_id in candidates[:max_docs]]
    print("PILOT_SELECTION=" + json.dumps({"max_docs":max_docs,
        "eligible_cited_sources":len(candidates), "targeted_train_references":
        sum(counts[x] for x in selected), "targeted_distinct_sources":len(selected)}))
    successful = []
    failures = Counter()
    sha = []
    pdf_chunks = []
    with TemporaryDirectory(prefix="wattbot_pdf_probe_") as folder:
        for i, doc_id in enumerate(selected):
            if i:
                time.sleep(2)
            try:
                path = Path(folder)/f"{i}.pdf"
                digest, summary = download_one(docs[doc_id]["url"],path)
                successful.append(doc_id)
                pdf_chunks.extend(chunks_from_pages(doc_id,docs[doc_id]['url'],path))
                sha.append({"sha256":digest,"size_bytes":path.stat().st_size,
                            "info":summary})
            except (requests.RequestException, ValueError, RuntimeError, OSError) as e:
                failures[type(e).__name__ + ":" + str(e)[:55]] += 1
        observed = set(successful)
        # Measure *coverage* of the 245 known-training cited sources, not
        # conditional retrieval accuracy on a truncated corpus.
        with_some = sum(bool(set(rr)&observed) for rr in refs)
        with_all = sum(bool(rr) and set(rr)<=observed for rr in refs)
        pages = sum(int(x["info"].split(";")[0].split("=")[1]) for x in sha)
        chars = sum(int(x["info"].split(";")[1].split("=")[1]) for x in sha)
        print("BOUNDED_PDF_PILOT="+json.dumps({
            "attempted":len(selected), "downloaded_valid_pdfs":len(successful),
            "failures":dict(failures), "aggregate_bytes":sum(x["size_bytes"] for x in sha),
            "aggregate_pages":pages,"aggregate_extracted_characters":chars,
            "training_questions_with_any_downloaded_gold_source":with_some,
            "training_questions_with_all_gold_sources_downloaded":with_all,
            "training_questions_total":len(train)},sort_keys=True))

        # Matched comparison on rows whose ALL gold refs are in the four-paper
        # pilot. The denominator is conditional and selection was train-driven,
        # so these figures are NOT overall corpus retrieval scores.
        matched = [(row, refs[i]) for i, row in enumerate(train)
                   if refs[i] and set(refs[i]) <= observed]
        pseudo_meta = [
            {"ref_id": d["id"], "url": d["url"], "page": 0,
             "text": " ".join(str(d.get(k,"") or "") for k in
                              ("title","citation","year","venue"))}
            for d in meta
        ]
        # Hybrid has metadata coverage for ALL 122 sources, unlike the
        # PDF-only truncated index; the 4 PDF texts supplement metadata.
        hybrid = pseudo_meta + pdf_chunks
        metrics = {}
        for k in (1,3,8):
            base_hit = hybrid_hit = base_complete = hybrid_complete = 0
            for question, correct in matched:
                expected = set(correct)
                base = set(score_metadata(question["question"],meta,k))
                hits = ranked(question["question"],hybrid,min(len(hybrid),200))
                # Collapse multiple page chunks to unique source references.
                seen = []
                for hit in hits:
                    if hit["ref_id"] not in seen:
                        seen.append(hit["ref_id"])
                    if len(seen) >= k:
                        break
                got = set(seen)
                base_hit += bool(base & expected)
                hybrid_hit += bool(got & expected)
                base_complete += expected <= base
                hybrid_complete += expected <= got
            n = len(matched)
            metrics[str(k)] = {
                "matched_questions":n,
                "metadata_any":round(base_hit/n,4) if n else None,
                "hybrid_any":round(hybrid_hit/n,4) if n else None,
                "metadata_all":round(base_complete/n,4) if n else None,
                "hybrid_all":round(hybrid_complete/n,4) if n else None,
            }
        print("FOUR_PDF_HYBRID_MATCHED_DIAGNOSTIC="+json.dumps({
            "selection_basis":"four most cited arXiv sources in training labels",
            "metadata_source_count":len(meta),
            "real_pdf_chunk_count":len(pdf_chunks),
            "scores_by_source_rank":metrics,
            "warning":"Train-selected conditional diagnostic, NOT global recall or official score",
        },sort_keys=True))


def self_test():
    assert pinned_pdf_url("https://arxiv.org/abs/2601.01234") == "https://arxiv.org/pdf/2601.01234"
    assert pinned_pdf_url("https://arxiv.org/pdf/2510.12345v2") == "https://arxiv.org/pdf/2510.12345v2"
    try:
        pinned_pdf_url("http://127.0.0.1/private")
        raise AssertionError("private URL permitted")
    except ValueError:
        pass
    print("PILOT_SELF_TEST=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--official-zip")
    p.add_argument("--max-docs", type=int, default=4)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        self_test()
    elif args.official_zip:
        pilot(args.official_zip,args.max_docs)
    else:
        p.error("Specify --official-zip or --self-test")
