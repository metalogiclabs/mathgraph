#!/usr/bin/env python3
"""WattBot: finite eight-report acquisition and extraction authority probe.

Eight explicit URLs from the official metadata only, not public search/crawl.
Validate HTTPS and bounded redirect hosts; check MIME/PDF/HTML readability;
retain no source text. Labels used only for aggregate train report coverage.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urljoin,urlparse
import zipfile

import fitz
import requests

ALLOWED_HOSTS={
    "cms.waterusedata.glc.org","eia.gov","www.eia.gov",
    "eta-publications.lbl.gov","greatlakes.org","www.greatlakes.org",
    "iea.blob.core.windows.net","sustainability.aboutamazon.com",
    "wispolicyforum.org","www.wispolicyforum.org","www.gao.gov","gao.gov"
}
MAX_BYTES=20*1024*1024
MAX_REDIRECTS=4

class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.chunks=[]
        self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in {"script","style","noscript","svg"}:self.skip+=1
    def handle_endtag(self,tag):
        if tag in {"script","style","noscript","svg"}:self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip:self.chunks.append(data)

def validate_url(url):
    p=urlparse(url)
    if p.scheme!="https" or (p.hostname or "").lower() not in ALLOWED_HOSTS:
        raise ValueError("disallowed_scheme_or_source_host")
    if p.username or p.password or p.port:
        raise ValueError("untrusted_url_auth_or_port")
    return p.hostname

def load_one(url):
    session=requests.Session()
    current=url
    try:
        for hop in range(MAX_REDIRECTS+1):
            validate_url(current)
            with session.get(current,timeout=(7,25),allow_redirects=False,stream=True,
                             headers={"User-Agent":"MathGraph-WattBot2026-exact-8-report-research/0.1"}) as r:
                if r.status_code in (301,302,303,307,308):
                    nxt=r.headers.get("Location")
                    if not nxt:
                        raise RuntimeError("redirect_without_location")
                    current=urljoin(current,nxt)
                    continue
                r.raise_for_status()
                buf=bytearray()
                for part in r.iter_content(chunk_size=32768):
                    buf+=part
                    if len(buf)>MAX_BYTES:
                        raise RuntimeError("source_size_cap")
                binary=bytes(buf)
                mime=str(r.headers.get("Content-Type","")).lower()
                if binary.startswith(b"%PDF") or "application/pdf" in mime:
                    with fitz.open(stream=binary,filetype="pdf") as f:
                        pages=len(f)
                        chars=sum(len(p.get_text()) for p in f)
                    if pages<1 or chars<20:
                        raise RuntimeError("pdf_not_text_extractable")
                    kind="pdf"
                elif "text/html" in mime or re.search(br"(?i)<(?:!doctype\s+html|html)",binary[:500]):
                    reader=TextOnly()
                    reader.feed(binary.decode("utf-8",errors="replace"))
                    text=" ".join(" ".join(reader.chunks).split())
                    pages=1
                    chars=len(text)
                    if chars<20:
                        raise RuntimeError("html_no_extractable_body")
                    kind="html"
                else:
                    raise RuntimeError("unsupported_document_format")
                return {"type":kind,"bytes":len(binary),"pages":pages,
                        "chars":chars,"sha256":hashlib.sha256(binary).hexdigest()}
        raise RuntimeError("redirect_limit")
    finally:
        session.close()

def parse_refs(raw):
    import ast
    raw=str(raw or "").strip()
    if raw.lower() in ("","is_blank","nan"):return []
    try:
        v=ast.literal_eval(raw)
    except (ValueError,SyntaxError,TypeError):
        v=[raw]
    return [str(a) for a in v] if isinstance(v,(tuple,list,set)) else [str(v)]

def run(archive):
    with zipfile.ZipFile(archive) as z:
        def load(name):
            return list(csv.DictReader(io.StringIO(z.read(name).decode("utf-8-sig"))))
        meta=load("metadata.csv")
        train=load("train_QA.csv")
    reports=[row for row in meta if row.get("type","").strip().lower()=="report"]
    if len(reports)!=8:
        raise RuntimeError("Official eight-report authority changed: require re-audit")
    known=set(r["id"] for r in reports)
    refsets=[set(parse_refs(r.get("ref_id",""))) for r in train]
    quoted=sum(bool(x&known) for x in refsets)
    outcomes=[]
    errors=Counter()
    digests=[]
    for i,r in enumerate(reports):
        if i:time.sleep(2)
        try:
            validate_url(r["url"])
            result=load_one(r["url"])
            outcomes.append({"type":result["type"],"bytes":result["bytes"],
                             "pages":result["pages"],"chars":result["chars"]})
            digests.append(result["sha256"])
        except (requests.RequestException,ValueError,RuntimeError,fitz.FileDataError) as exc:
            errors[type(exc).__name__+":"+(str(exc)[:48] if isinstance(exc,(ValueError,RuntimeError)) else "")]+=1
            digests.append("UNKNOWN")
    print("WATTBOT_PINNED_REPORT_AUDIT="+json.dumps({
        "attempted":len(reports),"valid":len(outcomes),
        "formats":dict(Counter(o["type"] for o in outcomes)),
        "total_extracted_chars":sum(o["chars"] for o in outcomes),
        "total_pages":sum(o["pages"] for o in outcomes),
        "errors":dict(errors),
        "train_question_rows_citing_any_report":quoted,
        "manifest_sha256":hashlib.sha256("\n".join(digests).encode()).hexdigest(),
        "scope":"eight official pinned URLs only; HTTP status and format tests do not prove accuracy",
    },sort_keys=True),flush=True)

def self_test():
    assert validate_url("https://www.gao.gov/some-report")=="www.gao.gov"
    try:
        validate_url("http://127.0.0.1/internal")
        raise AssertionError("unexpected unsafe URL accepted")
    except ValueError:
        pass
    doc=TextOnly()
    doc.feed("<html><style>hide</style><body>Valid report <b>12 MWh</b></body></html>")
    assert "12 MWh" in " ".join(doc.chunks)
    assert "hide" not in " ".join(doc.chunks)
    print("WATTBOT_REPORT_SELF_TEST=PASS")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip")
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:self_test()
    elif a.official_zip:run(a.official_zip)
    else:p.error("Supply --official-zip or --self-test")
