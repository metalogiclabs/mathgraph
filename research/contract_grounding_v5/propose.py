#!/usr/bin/env python3
"""Freeze docstring-attributed bounded semantic obligations before native execution.

All proposed relations must have an exact original-source sentence authority.
Two independently authored rule families see the *identical* doc snapshot.
"""
import argparse, hashlib, json, pathlib, re

RELATIONS=("lowercase-output","uppercase-output","underscore-elimination","trim-surrounding-space")


def clauses(doc):
    first=doc.strip().split("\n\n",1)[0]
    parts=re.split(r"(?<=[.!?])\s+|\n+",first)
    return [" ".join(part.split()) for part in parts if part.strip()][:6]


def candidate_relations(sentence):
    s=sentence.lower()
    relations=[]
    if re.search(r"\b(?:make|makes|convert|converts|return|returns|produce|produces)\b[^.]{0,110}\b(?:lowercase|lower-case|lower case)\b",s):
        relations.append("lowercase-output")
    if re.search(r"\b(?:make|makes|convert|converts|return|returns|produce|produces)\b[^.]{0,110}\b(?:entirely uppercase|all uppercase|uppercase string)\b",s):
        relations.append("uppercase-output")
    if re.search(r"\b(?:replace|replaces|convert|converts|change|changes)\b[^.]{0,100}\bunderscores?\b[^.]{0,70}\b(?:dashes?|hyphens?)\b",s):
        relations.append("underscore-elimination")
    if re.search(r"\b(?:strip|trim|remove|removes)\b[^.]{0,100}\b(?:leading and trailing|surrounding)\b[^.]{0,60}\b(?:spaces?|whitespace)\b",s):
        relations.append("trim-surrounding-space")
    return relations


def expert_relations(sentence):
    # Separately expressed conventional-expert rulebook, with identical evidence.
    s=sentence.lower()
    verbs=any(x in s for x in ("make ","makes ","convert","return","produce"))
    out=[]
    if verbs and any(x in s for x in ("lowercase","lower-case","lower case")):
        out.append("lowercase-output")
    if verbs and any(x in s for x in ("all uppercase","entirely uppercase","uppercase string")):
        out.append("uppercase-output")
    if any(x in s for x in ("replace ","replaces ","convert ","converts ","change ")) and (
        "underscore" in s and any(x in s for x in ("dash","hyphen"))
    ):
        out.append("underscore-elimination")
    if any(x in s for x in ("strip ","trim ","remove ")) and any(
        x in s for x in ("surrounding","leading and trailing")
    ) and any(x in s for x in ("space","whitespace")):
        out.append("trim-surrounding-space")
    return out


def propose(view, metadata, arm):
    assert arm in ("candidate","expert")
    f=candidate_relations if arm=="candidate" else expert_relations
    result={
        "protocol":"DOC_BOUND_SEMANTIC_OBLIGATION_V5",
        "arm":arm,"repository":metadata["repository"],"source_sha":metadata["source_sha"],
        "api_sha256":view["api"].get("api_sha256"),
        "status":"UNKNOWN_NO_SUPPORTED_EXPLICIT_AUTHOR_CONTRACT",
        "claims":[],"unknowns":view["unknowns"],
        "authority":"exact source-declared callable docstring, NOT public name or inferred external policy",
    }
    if view["status"]!="PUBLIC_DOCSTRING_AUTHORITY_EXTRACTED":
        result["status"]="UNKNOWN_MISSING_SOURCE_CONTRACT:"+view["status"]
        return result
    for item in sorted(view["contracts"],key=lambda x:(x["symbol"],x["relative_source_path"]))[:10]:
        by_relation={}
        for clause in clauses(item["docstring"]):
            for relation in f(clause):
                by_relation.setdefault(relation,clause)
        for relation,clause in sorted(by_relation.items()):
            result["claims"].append({
                "claim_id":item["symbol"]+"::"+relation,
                "symbol":item["symbol"],"relation":relation,
                "authority_sentence":clause,
                "authority_sentence_sha256":hashlib.sha256(clause.encode()).hexdigest(),
                "relative_source_path":item["relative_source_path"],
                "source_sha256":item["source_sha256"],
                "doc_sha256":item["doc_sha256"],
                "source_line":item["line"],
            })
    if result["claims"]:
        result["status"]="PROPOSED_DOC_BOUND_PENDING_NATIVE_AND_INDEPENDENT_ORACLE"
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--view",type=pathlib.Path,required=True)
    p.add_argument("--metadata",type=pathlib.Path,required=True)
    p.add_argument("--arm",choices=("candidate","expert"),required=True)
    p.add_argument("--out",type=pathlib.Path,required=True)
    a=p.parse_args()
    out=propose(json.loads(a.view.read_text()),json.loads(a.metadata.read_text()),a.arm)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("FROZEN_BEFORE_NATIVE_DOC_BOUND_PROPOSAL",a.arm,out["status"],
          [(q["claim_id"],q["authority_sentence"]) for q in out["claims"]])


if __name__=="__main__":
    main()
