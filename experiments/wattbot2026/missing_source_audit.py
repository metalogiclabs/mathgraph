#!/usr/bin/env python3
"""WattBot exact official-source obstruction audit; no source replacement.

Run the unchanged V4/V5b frozen source acquisition and wrap only its two
read operations to identify *which* official metadata sources fail and why.
Then make bounded non-replacing availability probes against arxiv's own
version-preserving PDF endpoint. Never use an alternate source as scientific
evidence or change the pinned corpus without independent full requalification.

No model calls, no Kaggle submission, no TEST answer/citation labels accessed,
no copyrighted source PDF bytes or derived passages exported as artifacts.
"""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
import tempfile
from urllib.parse import urlparse
import requests

import submit_full_reader as reader
from pdf_probe import pinned_pdf_url

ARXIV_MANIFEST="4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9"
REPORT_MANIFEST="a1720d14806ff219eaac8e0e8b8a5c8d6e87f596bba1a852505374ab4343b77d"


def obstruction_status(exc):
    response=getattr(exc,"response",None)
    code=getattr(response,"status_code",None)
    return {
        "exception":type(exc).__name__,
        "http_status":(int(code) if code is not None else None),
        "message_category":str(exc)[:180].split("?")[0],
    }


def probe_arxiv_same_version(url):
    # Only arxiv-owned endpoint preserving the exact version in metadata.
    # This is a diagnostic, NOT a substitute for the pinned source manifest.
    endpoint=pinned_pdf_url(url)
    parsed=urlparse(endpoint)
    if parsed.scheme!="https" or parsed.hostname!="arxiv.org":
        raise RuntimeError("Unexpected non-arXiv official source in probe")
    try:
        response=requests.get(endpoint,timeout=(8,25),stream=True,
            headers={"Accept":"application/pdf"})
        code=response.status_code
        content_type=response.headers.get("Content-Type","").split(";")[0]
        head=next(response.iter_content(chunk_size=2048),b"")
        response.close()
        return {
            "canonical_host":parsed.hostname,
            "canonical_path":parsed.path,
            "http_status":code,
            "content_type":content_type,
            "starts_with_pdf_magic":head.startswith(b"%PDF"),
        }
    except (requests.RequestException,OSError,RuntimeError) as exc:
        return {"canonical_host":parsed.hostname,
                "canonical_path":parsed.path,
                "exception":type(exc).__name__}


def run(archive):
    train,sources,test=reader.pinned_data(archive)
    if len(sources)!=122 or len(test)!=317:
        raise RuntimeError("Official pinned source or question-side scope changed")
    docs=sources.to_dict("records")
    url_refs={}
    for row in docs:
        url=str(row["url"])
        url_refs.setdefault(url,[]).append(str(row["id"]))
    failed=[]
    counts=Counter()
    original_pdf=reader.cached_download
    original_report=reader.download_report

    def instrument_pdf(url,destination,cache_root):
        try:
            return original_pdf(url,destination,cache_root)
        except (requests.RequestException,OSError,RuntimeError,ValueError) as exc:
            record={"source_kind":"arxiv_pdf",
                    "source_ids":url_refs.get(str(url),[]),
                    "official_url":str(url),
                    "failure":obstruction_status(exc)}
            failed.append(record)
            counts["arxiv_failed"]+=1
            return_exception=exc
            raise return_exception

    def instrument_report(ref,url):
        try:
            return original_report(ref,url)
        except (requests.RequestException,OSError,RuntimeError,ValueError) as exc:
            failed.append({"source_kind":"official_report",
                           "source_ids":[str(ref)],
                           "official_url":str(url),
                           "failure":obstruction_status(exc)})
            counts["report_failed"]+=1
            raise

    try:
        reader.cached_download=instrument_pdf
        reader.download_report=instrument_report
        with tempfile.TemporaryDirectory(prefix="wattbot_source_obstruction_") as root:
            docmap,index,manifest=reader.corpus(train,sources,Path(root))
    finally:
        reader.cached_download=original_pdf
        reader.download_report=original_report

    if (manifest["arxiv_sha256"]!=ARXIV_MANIFEST or
        manifest["reports_sha256"]!=REPORT_MANIFEST or
        manifest["source_page_chunks"]!=4810):
        raise RuntimeError("Frozen baseline manifest drifted, abort source audit")
    if counts["arxiv_failed"]!=2 or counts["report_failed"]!=1:
        raise RuntimeError("Failure pattern changed; existing benchmark needs requalification")
    diagnostics=[]
    for row in failed:
        if row["source_kind"]=="arxiv_pdf":
            diagnostics.append({
                "source_ids":row["source_ids"],
                "official_url":row["official_url"],
                "original_failure":row["failure"],
                "same_version_arxiv_endpoint":probe_arxiv_same_version(
                    row["official_url"]),
            })
        else:
            diagnostics.append({
                "source_ids":row["source_ids"],
                "official_url":row["official_url"],
                "original_failure":row["failure"],
                "fallback":"Not attempted; official report licensing/host authority preserved",
            })
    summary={
        "status":"BOUNDED_DIAGNOSTIC_ONLY",
        "official_source_registry_rows":len(sources),
        "official_question_side_rows":len(test),
        "baseline_arxiv_attempted":manifest["arxiv_attempted"],
        "baseline_report_attempted":manifest["reports_attempted"],
        "usable_page_chunks":manifest["source_page_chunks"],
        "baseline_sha256_arxiv":manifest["arxiv_sha256"],
        "baseline_sha256_reports":manifest["reports_sha256"],
        "failure_counts":dict(counts),
        "missing_source_diagnostics":diagnostics,
        "protected_test_answer_or_citation_labels_accessed":0,
        "model_requests":0,
        "kaggle_submissions":0,
        "boundary":"Only official public metadata/source URLs and error types. "
            "A probe of a version-preserving URL does not qualify different "
            "source bytes as interchangeable; all old corpus manifests stay "
            "the authority until a separately tested release is sealed.",
    }
    print("WATTBOT_MISSING_SOURCE_BOUNDARY="+json.dumps(
        summary,sort_keys=True),flush=True)


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip",required=True)
    a=p.parse_args()
    run(a.official_zip)
