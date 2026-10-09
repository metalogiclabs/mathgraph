#!/usr/bin/env python3
"""Evidence-anchored numeric answer pilot, TRAIN holdout only.

Train-development source selection; heldout answers are never used to generate
predictions. PDF provenance + literal arithmetic are checked, not semantic
entailment. The official pinned Score.py decides aggregate prediction quality.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
import re
import requests
from pathlib import Path
import tempfile
import time
from urllib.parse import urlparse
import zipfile

import pandas as pd

from holdout_probe import is_holdout, ARXIV_HOSTS
from pdf_probe import download_one
from score_ablation import blank_submission, load_score
from train_probe import load_csv, parse_refs
from wattbot import (NUM_RE, as_fraction, chunks_from_pages, norm, ranked,
                     tokens, verify_candidate)

STOP = set("a an the is was what how much many in of for from to by on and or are were which estimated report their its according as at during with using does did this that per about than total compared difference percent percentage".split())
# The original regex above is deliberately replaced below: % is nonword.
UNIT_RE = re.compile(r"^\s*(%|percent(?:age)?|MWh|GWh|TWh|kWh|kg|Mt|MW|GW|liters?|gallons?|years?|hours?|tonnes?|tons?|gCO2e|kgCO2e|tCO2e|CO2e)(?=\W|$)", re.I)


def numeric_candidates(question, ranked_chunks):
    q = set(tokens(question)) - STOP
    wants_year = "year" in q or "date" in q
    candidates = []
    for idx, chunk in enumerate(ranked_chunks):
        if chunk.get("page", 0) < 1:
            continue
        body = chunk["text"]
        for match in NUM_RE.finditer(body):
            raw = match.group().replace(",", "")
            try:
                value = as_fraction(raw)
            except ValueError:
                continue
            if value.denominator > 10_000_000:
                continue
            if 1900 <= value <= 2100 and not wants_year:
                continue
            if value < 0:
                continue
            left = max(0, match.start() - 110)
            right = min(len(body), match.end() + 125)
            quote = body[left:right].strip()
            nearby = set(tokens(quote)) - STOP
            overlap = len(q & nearby)
            if overlap < 2:
                continue
            suffix = body[match.end():match.end()+32]
            unit_match = UNIT_RE.match(suffix)
            unit = unit_match.group(1) if unit_match else "is_blank"
            priority = 4 * overlap + float(chunk.get("score", 0)) / 20 - 0.12*idx
            if unit != "is_blank" and any(t in question.casefold() for t in ("unit","energy","power","emission","water","percent","rate")):
                priority += 0.5
            candidates.append((priority, chunk, raw, quote, unit))
    return sorted(candidates, key=lambda x: -x[0])


def build_candidate(question, index, metadata):
    row = {"id": question["id"], "question": question["question"]}
    empty = {"id": row["id"], "answer_value":"is_blank",
             "ref_ids":[], "evidence":[],
             "explanation":"No numerically grounded claim earned admission."}
    for _, chunk, value, quote, unit in numeric_candidates(row["question"], index)[:25]:
        candidate = {"id":row["id"], "answer_value":value,
            "answer":value if unit=="is_blank" else value+" "+unit,
            "ref_ids":[chunk["ref_id"]],
            "evidence":[{"ref_id":chunk["ref_id"],"page":chunk["page"],"quote":quote}],
            "derivation":{"expression":"x","inputs":{"x":{"value":value,"evidence_index":0}}},
            "explanation":"CANDIDATE only: cited numeric literal and independent arithmetic check; semantic entailment unverified."}
        try:
            checked = verify_candidate(candidate,row,metadata,index)
            checked["answer_unit"] = unit
            return checked
        except (ValueError, KeyError, TypeError, ZeroDivisionError):
            continue
    return verify_candidate(empty,row,metadata,index)


def run(official_zip, max_docs=24):
    if max_docs not in (8,24):
        raise ValueError("Only 8/24-paper bounded comparisons are supported")
    with zipfile.ZipFile(official_zip) as z:
        metadata=load_csv(z,"metadata.csv")
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),keep_default_na=False)
        docs={d["id"]:d for d in metadata}
        with tempfile.TemporaryDirectory(prefix="wattbot_score_") as td:
            score_fn=load_score(z,td)
            dev=train[~train["id"].map(is_holdout)].copy()
            hold=train[train["id"].map(is_holdout)].copy()
            dev_refs=Counter(ref for _,r in dev.iterrows()
                             for ref in parse_refs(str(r["ref_id"])))
            sources=sorted((ref for ref in dev_refs if ref in docs
                     and (urlparse(docs[ref]["url"]).hostname or "").lower() in ARXIV_HOSTS),
                     key=lambda x:(-dev_refs[x],x))[:max_docs]
            chunks=[]
            valid=[]
            for i,ref in enumerate(sources):
                if i:
                    time.sleep(3.1)
                pdf=Path(td)/f"paper-{i}.pdf"
                try:
                    download_one(docs[ref]["url"],pdf)
                    page_chunks=chunks_from_pages(ref,docs[ref]["url"],pdf)
                    if not page_chunks:
                        raise ValueError("No PDF text")
                    chunks.extend(page_chunks)
                    valid.append(ref)
                except (requests.RequestException,ValueError,RuntimeError,OSError) as e:
                    # Any missing source stays UNKNOWN, never substituted.
                    print("PAPER_FETCH_FAILURE_TYPE="+type(e).__name__)
            # Every source's metadata is searchable even if its PDF is not.
            meta_chunks=[{"ref_id":d["id"],"url":d["url"],"page":0,
                          "text":" ".join(str(d.get(k,"") or "")
                          for k in ("title","citation","year","venue"))} for d in metadata]
            index=meta_chunks+chunks
            rows=[]
            admitted=0
            for _,r in hold.iterrows():
                row={"id":str(r["id"]),"question":str(r["question"])}
                hits=ranked(row["question"],index,min(100,len(index)))
                proposed=build_candidate(row,hits,docs)
                admitted+=proposed["answer_value"]!="is_blank"
                rows.append(proposed)
            predicted=pd.DataFrame(rows,columns=list(blank_submission(hold).columns))
            blanks=blank_submission(hold)
            score=lambda frame:float(score_fn(hold.copy(deep=True),
                            frame.copy(deep=True),row_id_column_name="id",verbose=False))
            result={"holdout_rows":len(hold),"dev_rows":len(dev),
                    "selected_sources":len(sources),"retrieved_valid_pdfs":len(valid),
                    "pdf_chunks":len(chunks),"admitted_numeric_candidates":admitted,
                    "abstentions":len(hold)-admitted,
                    "official_train_holdout_blank_score":round(score(blanks),8),
                    "official_train_holdout_numeric_score":round(score(predicted),8),
                    "claim_boundary":"Numeric literals plus pinned page provenance only, not semantic entailment or leaderboard score."}
            print("WATTBOT_GROUNDED_NUMERIC_PILOT="+json.dumps(result,sort_keys=True))


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip",required=True)
    p.add_argument("--max-docs",type=int,default=24)
    a=p.parse_args()
    run(a.official_zip,a.max_docs)
