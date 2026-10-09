#!/usr/bin/env python3
"""Audit per-source report integrity for frozen WattBot 2026 pinned URLs.

Only eight official report metadata records; no untrusted URLs, no text leaked.
A transient HTTP failure or byte revision is UNKNOWN until requalification,
never silently overridden to force a Kaggle submission.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import io
import json
import time
import zipfile

from report_loader import download_report, self_test as loader_self_test
from train_probe import load_csv

OFFICIAL_METADATA_SHA256="b54eb64f7747493443465a58822f87bc12655ee8aab9be83b0958222bb3c1ca1"
PREVIOUS_MANIFEST="a1720d14806ff219eaac8e0e8b8a5c8d6e87f596bba1a852505374ab4343b77d"


def audit(official_zip):
    with zipfile.ZipFile(official_zip) as z:
        raw=z.read("metadata.csv")
        if hashlib.sha256(raw).hexdigest()!=OFFICIAL_METADATA_SHA256:
            raise ValueError("Unexpected official metadata snapshot")
        meta=load_csv(z,"metadata.csv")
    report=[d for d in meta if str(d.get("type","")).lower()=="report"]
    if len(report)!=8:
        raise ValueError("Expected exactly eight pinned report records")
    outcomes=[]
    digests=[]
    for i,item in enumerate(report):
        if i:time.sleep(2)
        entry={"ordinal":i,"status":"UNKNOWN"}
        try:
            r=download_report(str(item["id"]),str(item["url"]))
            if not r.get("chunks"):
                raise ValueError("No extracted report text")
            digest=r["sha256"]
            digests.append(digest)
            entry.update(status="OK",format=r["kind"],sha256=digest,
                         chunks=len(r["chunks"]))
        except Exception as error:
            # The upstream downloader has bounded redirects and an explicit
            # approved-host allowlist. A failure remains UNKNOWN.
            if not isinstance(error,(OSError,RuntimeError,ValueError)):
                import requests
                if not isinstance(error,requests.RequestException):
                    raise
            digests.append("UNKNOWN")
            entry["status"]="UNKNOWN"
            entry["failure_type"]=type(error).__name__
            if hasattr(error,"response") and error.response is not None:
                entry["http_status"]=error.response.status_code
        outcomes.append(entry)
    # Match the historical full_reader certificate's literal backslash+n separator.
    manifest=hashlib.sha256("\\n".join(digests).encode()).hexdigest()
    print("WATTBOT_REPORT_PIN_AUDIT="+json.dumps({
        "official_metadata_pin":OFFICIAL_METADATA_SHA256,
        "reference_manifest":PREVIOUS_MANIFEST,
        "observed_manifest":manifest,
        "manifest_matches":manifest==PREVIOUS_MANIFEST,
        "sources":outcomes,
        "status_counts":dict(Counter(e["status"] for e in outcomes)),
        "boundary":"Approved eight metadata URLs only; no bytes, URLs, source text or protected question rows emitted",
    },sort_keys=True),flush=True)


def self_test():
    loader_self_test()
    assert len(PREVIOUS_MANIFEST)==64
    assert len(OFFICIAL_METADATA_SHA256)==64
    assert hashlib.sha256("UNKNOWN\nUNKNOWN".encode()).hexdigest()!=PREVIOUS_MANIFEST
    print("WATTBOT_REPORT_PIN_AUDIT_SELF_TEST=PASS")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip")
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test:self_test()
    elif args.official_zip:audit(args.official_zip)
    else:p.error("Specify --official-zip or --self-test")
