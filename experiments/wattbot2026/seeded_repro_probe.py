#!/usr/bin/env python3
"""Synthetic-only OpenRouter seeded repeatability audit for WattBot.

A fixed seed may improve model output reproducibility, but endpoint routing,
model updates, and inference implementation can still change outputs.
No official TRAIN or protected TEST data/answers enter this diagnostic.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import time
import requests
import full_reader as base

BASE_BLOB="4e1350ef72a44a333862dec23c737a2262ab99bc"
MAX_RESERVED=.019
ENDPOINT="https://openrouter.ai/api/v1/chat/completions"
FIXTURES=(
 {"question":"How many megawatt-hours did the synthetic solar experiment use?",
  "passages":[
    {"source_index":0,"ref_id":"SYN_SOLAR","page":2,
     "text":"Synthetic solar experiment reported electrical energy of 12.5 MWh."},
    {"source_index":1,"ref_id":"SYN_WIND","page":3,
     "text":"Unrelated wind experiment used 88 MWh."}]},
 {"question":"How many household-years does synthetic training model Z use?",
  "passages":[
    {"source_index":0,"ref_id":"SYN_MODEL","page":1,
     "text":"Synthetic training model Z consumed 1,287 MWh."},
    {"source_index":1,"ref_id":"SYN_HOUSE","page":3,
     "text":"Synthetic census: 35,000 households consumed 377,685 MWh in one year."}]},
 {"question":"Are the two synthetic accelerator measurements contradictory?",
  "passages":[
    {"source_index":0,"ref_id":"SYN_GPU1","page":7,
     "text":"Study A sees high efficiency in unconstrained batches."},
    {"source_index":1,"ref_id":"SYN_GPU2","page":3,
     "text":"Study B sees lower power with a smaller GPU under strict latency limits."}]},
)
def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()

def seed_for(q):
    return int(hashlib.sha256(("metalogic-wattbot-fixed-v1|"+q).encode()).hexdigest()[:8],16)

def self_test():
    assert git_blob(Path(base.__file__).read_bytes())==BASE_BLOB
    assert base.MODEL=="google/gemini-2.5-flash-lite"
    assert base.MAX_OUTPUT_TOKENS==650
    assert len(FIXTURES)==3 and len({seed_for(x["question"]) for x in FIXTURES})==3
    print("WATTBOT_SEEDED_REPRODUCIBILITY_SELF_TEST=PASS")

def run():
    self_test()
    key=os.environ.get("OPENROUTER_API_KEY")
    if not key:raise RuntimeError("Missing model key")
    rate=base.verify_price_ceiling()
    total_reserved=0.
    observed_usd=0.
    cohorts=[]
    for idx,fixture in enumerate(FIXTURES):
        for mode,n in (("seeded",3),("unseeded",2)):
            prompt=json.dumps(fixture,ensure_ascii=False,separators=(",",":"))
            estimated=base.conservative_charge(
                base.SYSTEM+prompt,rate,base.MAX_OUTPUT_TOKENS)
            if total_reserved+estimated*n>MAX_RESERVED:
                raise RuntimeError("Synthetic audit would breach model cost ceiling")
            hashes=[]
            statuses=Counter()
            seen_providers=set()
            attempted=0
            for _ in range(n):
                body={
                    "model":base.MODEL,
                    "messages":[{"role":"system","content":base.SYSTEM},
                                {"role":"user","content":prompt}],
                    "response_format":{"type":"json_object"},
                    "max_tokens":base.MAX_OUTPUT_TOKENS,
                    "temperature":0.0,
                    "stream":False,
                }
                if mode=="seeded":
                    body["seed"]=seed_for(fixture["question"])
                    body["provider"]={"require_parameters":True}
                attempted+=1
                response=requests.post(ENDPOINT,headers={
                   "Authorization":"Bearer "+key,
                   "Content-Type":"application/json",
                   "HTTP-Referer":"https://metalogiclabs.xyz",
                   "X-Title":"WattBot synthetic seed reproducibility audit"},
                   json=body,timeout=(10,75))
                if response.status_code!=200:
                    if mode=="seeded" and response.status_code in (400,422):
                        # Rejection is a measured feature-compatibility result;
                        # it is NOT a deterministic model response and no
                        # answer or source is promoted.
                        statuses["seeded_parameter_rejected"]+=1
                        break
                    raise RuntimeError("Provider request failed: HTTP "+str(response.status_code))
                result=response.json()
                if result.get("error"):
                    raise RuntimeError("Provider returned an error")
                raw=((result.get("choices") or [{}])[0].get("message") or {}).get("content")
                if isinstance(raw,list):
                    raw="\n".join(part.get("text","") for part in raw if isinstance(part,dict))
                try:
                    parsed=json.loads(str(raw or ""))
                    if not isinstance(parsed,dict):
                        raise TypeError("Model did not return a JSON object")
                    canonical=json.dumps(parsed,sort_keys=True,
                                         ensure_ascii=False,separators=(",",":"))
                    statuses["valid_json"]+=1
                except (ValueError,TypeError):
                    canonical=str(raw or "").strip()
                    statuses["invalid_json"]+=1
                hashes.append(hashlib.sha256(canonical.encode()).hexdigest())
                if result.get("provider"):
                    seen_providers.add(str(result["provider"])[:80])
                cost=(result.get("usage") or {}).get("cost")
                if isinstance(cost,(int,float)):
                    observed_usd+=float(cost)
                total_reserved+=estimated
                if total_reserved>MAX_RESERVED:
                    raise RuntimeError("Total synthetic request reservation breached")
                time.sleep(.25)
            cohorts.append({
               "case":idx,"mode":mode,"calls":attempted,
               "unique_canonical_outputs":len(set(hashes)),
               "all_identical":len(set(hashes))==1,
               "valid_json":statuses["valid_json"],
               "invalid_json":statuses["invalid_json"],
               "provider_count_if_reported":len(seen_providers),
               "seeded_parameter_rejected":statuses["seeded_parameter_rejected"]})
    print("WATTBOT_SEEDED_REPRODUCIBILITY="+json.dumps({
       "scope":"Three entirely synthetic scientific question fixtures",
       "model":base.MODEL,
       "cohorts":cohorts,
       "seeded_all_identical":all(x["all_identical"] for x in cohorts
                                   if x["mode"]=="seeded"),
       "unseeded_all_identical":all(x["all_identical"] for x in cohorts
                                     if x["mode"]=="unseeded"),
       "total_calls":sum(x["calls"] for x in cohorts),
       "model_reserved_usd":round(total_reserved,7),
       "model_observed_usd":round(observed_usd,7),
       "boundary":"Exact repeatability of synthetic model requests does not "
         "prove bit-identical Kaggle TEST outputs or scientific correctness. "
         "No WattBot TRAIN or TEST labels, source PDFs, Kaggle quota usage, "
         "or model response artifacts."
    },sort_keys=True),flush=True)

if __name__=="__main__":
    run() if os.environ.get("WATTBOT_RUN_SYNTHETIC_SEEDED")=="1" else self_test()
