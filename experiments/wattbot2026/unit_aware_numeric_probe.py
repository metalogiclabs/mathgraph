#!/usr/bin/env python3
"""WattBot: score source-grounded numeric extraction using the supplied answer_unit.

The official TEST question file exposes answer_unit as a question-side field.
This is allowed task input, not a hidden test label. This program uses only
TRAIN labels for model-selection scoring and runs no protected TEST inference.
It must never inspect the TEST answer values or use gold citation IDs to
produce a candidate.

All candidate values come from literal numeric spans in the pinned source
PDFs, plus independently verified exact unit conversion when enabled.
Quotation presence/derivation are checked; semantic entailment is UNKNOWN.
"""
from __future__ import annotations
import argparse
from collections import Counter
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import tempfile
import zipfile

import pandas as pd

import submit_full_reader as source
from holdout_probe import is_holdout
from numeric_answer_probe import numeric_candidates
from score_ablation import blank_submission, load_score
from wattbot import as_fraction, ranked, verify_candidate

OFFICIAL_SCORE_PIN = "e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075"
BASELINE_HOLDOUT_NUMERIC = 0.25846561
POLICIES = ("baseline", "unit_bonus", "unit_first", "unit_strict", "unit_convert")
NA = frozenset(("","is_blank","na","n/a","none","null","nan"))

ALIASES = {
    "%":"percent","percentage":"percent","percent":"percent",
    "wh":"wh", "watthour":"wh", "watthours":"wh",
    "kwh":"kwh","kilowatthour":"kwh","kilowatthours":"kwh",
    "mwh":"mwh","megawatthour":"mwh","megawatthours":"mwh",
    "gwh":"gwh","gigawatthour":"gwh","gigawatthours":"gwh",
    "twh":"twh","terawatthour":"twh","terawatthours":"twh",
    "w":"w","watt":"w","watts":"w",
    "kw":"kw","kilowatt":"kw","kilowatts":"kw",
    "mw":"mw","megawatt":"mw","megawatts":"mw",
    "gw":"gw","gigawatt":"gw","gigawatts":"gw",
    "litre":"l","litres":"l","liter":"l","liters":"l","l":"l",
    "gallon":"gal","gallons":"gal","gal":"gal",
    "gco2e":"gco2e","kgco2e":"kgco2e","tco2e":"tco2e","mtco2e":"mtco2e",
    "years":"year","year":"year","hrs":"hour","hours":"hour","hour":"hour",
}
# Exact rational conversion; avoid gallons because "gallon" may mean US/imperial,
# or mass "ton" where metric versus short is not established.
SCALE = {
    "wh":("energy",Fraction(1)),
    "kwh":("energy",Fraction(10**3)),
    "mwh":("energy",Fraction(10**6)),
    "gwh":("energy",Fraction(10**9)),
    "twh":("energy",Fraction(10**12)),
    "w":("power",Fraction(1)),
    "kw":("power",Fraction(10**3)),
    "mw":("power",Fraction(10**6)),
    "gw":("power",Fraction(10**9)),
    "gco2e":("carbon",Fraction(1)),
    "kgco2e":("carbon",Fraction(10**3)),
    "tco2e":("carbon",Fraction(10**6)),
    "mtco2e":("carbon",Fraction(10**12)),
}


def normalize_unit(unit):
    text=str(unit or "").strip().casefold().replace("²","2").replace("₂","2")
    text="".join(c for c in text if not c.isspace() and c not in "-_")
    if text in NA:
        return "is_blank"
    return ALIASES.get(text,text)


def safe_ratio(found,wanted):
    a,b=normalize_unit(found),normalize_unit(wanted)
    if a==b and a!="is_blank":
        return Fraction(1)
    if a not in SCALE or b not in SCALE:
        return None
    at,scale_a=SCALE[a]
    bt,scale_b=SCALE[b]
    if at!=bt:
        return None
    return scale_a/scale_b


def display_fraction(value: Fraction):
    with localcontext() as ctx:
        ctx.prec=34
        num=Decimal(value.numerator)/Decimal(value.denominator)
    if not num.is_finite() or abs(num)>Decimal("1e40"):
        raise ValueError("Out of bounded numeric scope")
    # Round to 10 fractional digits, well below the scorer's tolerance for
    # normalized magnitudes, without floating-point representation drift.
    result=format(num,"f")
    if "." in result:
        whole,part=result.split(".")
        if len(part)>10:
            result=format(num.quantize(Decimal("0.0000000001")),"f")
        result=result.rstrip("0").rstrip(".") if "." in result else result
    return result


def checked_numeric(question, hit, raw, quote, observed_unit, docs, index, ratio=None):
    value=as_fraction(raw)
    if ratio is None:
        ratio=Fraction(1)
    converted=value*ratio
    output=display_fraction(converted)
    formula=("x" if ratio==1 else
             "x * " + str(ratio.numerator) + " / " + str(ratio.denominator))
    candidate={
        "id":question["id"],
        "answer":output+" "+str(question.get("answer_unit") or observed_unit),
        "answer_value":output,
        "ref_ids":[hit["ref_id"]],
        "evidence":[{"ref_id":hit["ref_id"],"page":hit["page"],"quote":quote}],
        "derivation":{"expression":formula,"inputs":{
            "x":{"value":raw,"evidence_index":0}}},
        "explanation":"CANDIDATE: exact PDF numeric literal and checked unit conversion, "
                      "semantic entailment still UNKNOWN.",
    }
    return verify_candidate(candidate,question,docs,index)


def abstain(question,docs,index):
    return verify_candidate({
        "id":question["id"],"answer_value":"is_blank","ref_ids":[],"evidence":[],
        "explanation":"No admissible unit-matched numeric evidence."
    },question,docs,index)


def candidate(question,hits,docs,policy):
    if policy=="baseline":
        from numeric_answer_probe import build_candidate
        return build_candidate(question,hits,docs)
    wanted=normalize_unit(question.get("answer_unit"))
    source=numeric_candidates(question["question"],hits)
    if wanted=="is_blank":
        from numeric_answer_probe import build_candidate
        return build_candidate(question,hits,docs)
    ranked_candidates=[]
    for priority,hit,raw,quote,unit in source[:100]:
        observed=normalize_unit(unit)
        ratio=safe_ratio(unit,wanted)
        exact=(observed==wanted)
        convertible=(ratio is not None and ratio!=1)
        if policy=="unit_strict" and not exact:
            continue
        if policy=="unit_first" and not exact:
            continue
        if policy=="unit_bonus":
            merit=priority + (40 if exact else -20)
        elif policy=="unit_convert":
            merit=priority + (40 if exact else 30 if convertible else -20)
        else:
            merit=priority
        ranked_candidates.append((merit,priority,hit,raw,quote,unit,
                                  ratio if policy=="unit_convert" and convertible else None))
    ranked_candidates.sort(key=lambda x:(-x[0],-x[1]))
    for _,_,hit,raw,quote,unit,ratio in ranked_candidates:
        # Conversions are never implied by unit mismatch unless explicitly
        # selected under the unit_convert policy with exact rational ratio.
        try:
            return checked_numeric(question,hit,raw,quote,unit,docs,hits,ratio)
        except (ValueError,TypeError,KeyError,ZeroDivisionError):
            continue
    if policy=="unit_strict":
        return abstain(question,docs,hits)
    from numeric_answer_probe import build_candidate
    return build_candidate(question,hits,docs)


def self_test():
    assert normalize_unit("MWh")=="mwh"
    assert normalize_unit("megawatt-hours")=="mwh"
    assert normalize_unit("kgCO2e")=="kgco2e"
    assert normalize_unit("is_blank")=="is_blank"
    assert safe_ratio("GWh","MWh")==1000
    assert safe_ratio("MW","GW")==Fraction(1,1000)
    assert safe_ratio("kgCO2e","tCO2e")==Fraction(1,1000)
    assert safe_ratio("gallons","litres") is None
    assert display_fraction(Fraction(1000,3))=="333.3333333333"
    assert display_fraction(Fraction(1000))=="1000"
    assert display_fraction(Fraction(0))=="0"
    print("WATTBOT_UNIT_AWARE_NUMERIC_SELF_TEST=PASS")


def run(official_zip):
    self_test()
    train,metadata,test=source.pinned_data(official_zip)
    with zipfile.ZipFile(official_zip) as z:
        if hashlib.sha256(z.read("Score.py")).hexdigest()!=OFFICIAL_SCORE_PIN:
            raise RuntimeError("Unpinned scorer")
        with tempfile.TemporaryDirectory(prefix="wattbot_unit_eval_") as tmp:
            docs,index,manifest=source.corpus(train,metadata,Path(tmp))
            cols=list(blank_submission(train).columns)
            frames={p:[] for p in POLICIES}
            states=Counter()
            for _,item in train.iterrows():
                question={"id":str(item["id"]),"question":str(item["question"]),
                          "answer_unit":str(item["answer_unit"])}
                hits=ranked(question["question"],index,min(100,len(index)))
                states["explicit_unit_train"]+=int(
                    normalize_unit(question["answer_unit"])!="is_blank")
                for policy in POLICIES:
                    value=candidate(question,hits,docs,policy)
                    states[policy+"_nonblank"]+=int(value["answer_value"]!="is_blank")
                    frames[policy].append(value)
            answers={p:pd.DataFrame(rows,columns=cols) for p,rows in frames.items()}
            keep_dev=~train["id"].astype(str).map(is_holdout)
            keep_hold=~keep_dev
            scorer=load_score(z,tmp)
            def score(mask,policy):
                sol=train.loc[mask].copy(deep=True)
                pred=answers[policy].loc[mask].copy(deep=True)
                return round(float(scorer(sol,pred,row_id_column_name="id",
                    verbose=False)),8)
            dev_scores={p:score(keep_dev,p) for p in POLICIES}
            chosen=max(POLICIES,key=lambda p:(dev_scores[p],-POLICIES.index(p)))
            hold_scores={p:score(keep_hold,p) for p in POLICIES}
            baseline=hold_scores["baseline"]
            result={
                "scope":"Complete officially pinned corpus; TRAIN-only development+reused holdout",
                "authority":"Exact official Score.py, not Kaggle leaderboard",
                "source_manifest":manifest,
                "dev_rows":int(keep_dev.sum()),
                "holdout_rows":int(keep_hold.sum()),
                "test_rows_used":0,
                "unit_present_train":states["explicit_unit_train"],
                "unit_present_test":int(sum(normalize_unit(u)!="is_blank"
                    for u in test["answer_unit"])),
                "dev_policy_scores":dev_scores,
                "chosen_on_dev_only":chosen,
                "holdout_policy_scores":hold_scores,
                "chosen_holdout_delta":round(hold_scores[chosen]-baseline,8),
                "historical_numeric_holdout":BASELINE_HOLDOUT_NUMERIC,
                "prediction_counts":dict(states),
                "boundary":"answer_unit is provided in TEST; never used hidden TEST "
                           "answer_value, citations or labels. PDF quotes and exact "
                           "rational units checked; semantic consequence not established.",
            }
            print("WATTBOT_UNIT_AWARE_NUMERIC="+json.dumps(result,sort_keys=True),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--official-zip")
    a=p.parse_args()
    if a.self_test:self_test()
    elif a.official_zip:run(a.official_zip)
    else:p.error("Supply --self-test or --official-zip")
