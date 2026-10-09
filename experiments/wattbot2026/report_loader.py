#!/usr/bin/env python3
"""Exactly pinned WattBot 2026 report PDF/HTML loader.

No arbitrary URLs or recursive crawling. Every request originates from one of
the eight metadata-supplied report URLs, with HTTPS and bounded redirects to
an explicit authorized host allowlist. Returns page-local chunks with source
byte hashes; never caches to Git or emits copyrighted text.
"""
from __future__ import annotations
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import re
import tempfile
from urllib.parse import urljoin,urlparse

import fitz
import requests
from wattbot import chunks_from_pages

ALLOWED={
  "cms.waterusedata.glc.org","eia.gov","www.eia.gov",
  "eta-publications.lbl.gov","greatlakes.org","www.greatlakes.org",
  "iea.blob.core.windows.net","sustainability.aboutamazon.com",
  "wispolicyforum.org","www.wispolicyforum.org",
  "www.gao.gov","gao.gov"}
LIMIT=20*1024*1024

class HTMLBody(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text=[]
        self.skip=0
    def handle_starttag(self,name,attrs):
        if name in ("script","style","noscript","svg"):
            self.skip+=1
    def handle_endtag(self,name):
        if name in ("script","style","noscript","svg"):
            self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip:self.text.append(data)

def allowed(url):
    p=urlparse(url)
    if p.scheme!="https" or (p.hostname or "").lower() not in ALLOWED:
        raise ValueError("unapproved report source")
    if p.username or p.password or p.port not in (None,443):
        raise ValueError("report URL has unexpected authority")
    return p.hostname

def download_report(id_,url):
    allowed(url)
    current=url
    session=requests.Session()
    try:
        for redirect in range(5):
            allowed(current)
            with session.get(current,allow_redirects=False,stream=True,
                             timeout=(8,26),headers={
                  "User-Agent":"MathGraph-WattBot2026-pinned-report-reader/0.1"}) as r:
                if r.status_code in (301,302,303,307,308):
                    dest=r.headers.get("Location")
                    if not dest:raise RuntimeError("missing redirect location")
                    current=urljoin(current,dest)
                    continue
                r.raise_for_status()
                data=bytearray()
                for buf in r.iter_content(chunk_size=32768):
                    data+=buf
                    if len(data)>LIMIT:
                        raise RuntimeError("report source exceeded finite size cap")
                raw=bytes(data)
                digest=hashlib.sha256(raw).hexdigest()
                mime=str(r.headers.get("Content-Type","")).casefold()
                if raw.startswith(b"%PDF") or "application/pdf" in mime:
                    with tempfile.TemporaryDirectory(prefix="report_page_") as folder:
                        file=Path(folder)/"report.pdf"
                        file.write_bytes(raw)
                        chunks=chunks_from_pages(id_,url,file)
                    if not chunks:
                        raise RuntimeError("PDF has no readable text pages")
                    return {"kind":"pdf","sha256":digest,"chunks":chunks}
                if "text/html" in mime or re.search(br"(?i)<(?:html|!doctype\s+html)",raw[:600]):
                    parser=HTMLBody()
                    parser.feed(raw.decode("utf-8",errors="replace"))
                    body=" ".join(" ".join(parser.text).split())
                    if len(body)<20:
                        raise RuntimeError("HTML report has no extractable body")
                    chunks=[]
                    pos=0
                    size=2400
                    overlap=320
                    while pos<len(body):
                        end=min(len(body),pos+size)
                        if end<len(body):
                            space=body.rfind(" ",pos+size//2,end)
                            if space>pos:end=space
                        value=body[pos:end].strip()
                        if value:
                            chunks.append({"ref_id":id_,"url":url,"page":1,
                                "text":value,"source_sha256":digest})
                        if end==len(body):break
                        pos=max(pos+1,end-overlap)
                    return {"kind":"html","sha256":digest,"chunks":chunks}
                raise RuntimeError("unsupported report response format")
        raise RuntimeError("report redirect count exceeded")
    finally:
        session.close()

def self_test():
    assert allowed("https://www.gao.gov:443/pubs/test.pdf")=="www.gao.gov"
    try:
        allowed("http://127.0.0.1/private")
        raise AssertionError("SSRF guard failed")
    except ValueError:pass
    p=HTMLBody()
    p.feed("<html><script>secret</script><body>Real report <b>42 MWh</b></body></html>")
    assert "42 MWh" in " ".join(p.text)
    assert "secret" not in " ".join(p.text)
    print("WATTBOT_REPORT_LOADER_SELF_TEST=PASS")

if __name__=="__main__":self_test()
