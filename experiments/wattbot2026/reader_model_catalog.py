#!/usr/bin/env python3
"""Read public OpenRouter model catalog for controlled WattBot reader selection.

No inference and no credential required. Prints published pricing only.
Budget decisions must be made against live prices before any paid requests.
"""
from __future__ import annotations
import json
import math
import urllib.request

MATCHES=("gemini-3","gemini-2.5-pro","gemini-2.5-flash","gemini-3.5",
         "gpt-5.6","gpt-6","claude-5","claude-sonnet","claude-opus",
         "deepseek-v4","qwen3","qwen4","kimi-k3")
MAX_PRINT=60

def main():
    req=urllib.request.Request("https://openrouter.ai/api/v1/models",headers={
        "User-Agent":"Metalogic MathGraph WattBot model-catalog audit"})
    with urllib.request.urlopen(req,timeout=30) as response:
        raw=json.load(response)["data"]
    selected=[]
    for item in raw:
        mid=str(item.get("id",""))
        if not any(substring in mid.casefold() for substring in MATCHES):
            continue
        prices=item.get("pricing") or {}
        try:
            prompt=float(prices["prompt"])
            completion=float(prices["completion"])
        except (ValueError,KeyError,TypeError):
            continue
        if not all(math.isfinite(v) and v>=0 for v in (prompt,completion)):
            continue
        selected.append({
            "id":mid,"per_million_input_usd":round(prompt*1e6,4),
            "per_million_output_usd":round(completion*1e6,4),
            "context_length":item.get("context_length"),
            "output_modalities":(item.get("architecture") or {}).get("output_modalities",[])
        })
    selected.sort(key=lambda r:(r["per_million_input_usd"]*2+
                                r["per_million_output_usd"],r["id"]))
    print("WATTBOT_LIVE_MODEL_PRICE_CANDIDATES="+json.dumps({
        "model_count":len(selected),
        "models":selected[:MAX_PRINT],
        "strong_model_spotlight":[m for m in selected if any(
            token in m["id"] for token in (
                "openai/gpt-6","google/gemini-3.8-flash",
                "google/gemini-3.7-flash","google/gemini-3.6-flash",
                "google/gemini-3.5-flash","google/gemini-3.1-pro",
                "claude-sonnet-5.5","claude-opus-5.5","gpt-5.6-high"))],
        "boundary":"Public catalog only. Model quality unknown until frozen scored probe; no tokens purchased."
    },sort_keys=True))

if __name__=="__main__":main()
