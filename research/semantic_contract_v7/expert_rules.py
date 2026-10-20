#!/usr/bin/env python3
"""Independent conventional expert-authored rulebook for same public API/docs.

This is an independently written conventional baseline, not a blinded human.
Both arms see exact same frozen source-document inventory before native execution.
"""
import argparse,hashlib,json,pathlib,re

STANDARD_OPTIONS={
 "safe_mode":("escape",("escape",)),
 "escape_html":(True,("true",)),
 "escape":(True,("true",)),
}

def conventional_rules(view):
    proposals=[]
    for fn in sorted(view["api"],key=lambda d:(d["path"],d["symbol"])):
        for source in view["public_doc_paragraphs"]:
            prose=source["text"].lower()
            if "html" not in prose or "escap" not in prose:
                continue
            # Ordinary reviewer follows the example of the callable and its option.
            if fn["symbol"].lower()+"(" not in prose and not re.search(
                r"\b"+re.escape(fn["symbol"].lower())+r"\s*\(",prose):
                continue
            if any(re.search(r"\b(?:not|never|does not|doesn't|without|no)\s+(?:be\s+)?escap",part)
                   for part in re.split(r"[.;]",prose)):
                continue
            for option in fn["accepted_modes"]:
                if option not in STANDARD_OPTIONS:
                    continue
                value,aliases=STANDARD_OPTIONS[option]
                if not any(re.search(r"\b"+re.escape(option)+r"\s*(?:=|:|is|to)\s*[^a-z0-9]{0,3}"+alias+r"\b",prose)
                           for alias in aliases):
                    continue
                if not re.search(r"(?:escape\w*[^.]{0,45}html|html[^.]{0,45}escap\w*)",prose):
                    continue
                proposals.append({
                    "claim_id":fn["module"]+"."+fn["symbol"]+"::"+option+"::escaped-text",
                    "module":fn["module"],"symbol":fn["symbol"],"api_path":fn["path"],
                    "api_sha256":fn["file_sha256"],"mode":option,"value":value,
                    "relation":"raw script tag absent AND original source text retained as HTML text",
                    "document_path":source["source_path"],
                    "document_sha256":source["source_sha256"],
                    "document_paragraph":source["text"],"paragraph_index":source["paragraph_index"],
                    "paragraph_sha256":source["paragraph_sha256"],
                    "scope":"one frozen literal raw HTML input; not HTML sanitization/security generally",
                })
    return sorted(proposals,key=lambda c:(c["document_path"],c["api_path"],c["claim_id"]))[:3]

def main():
    p=argparse.ArgumentParser()
    for x in ("view","metadata","out"):p.add_argument("--"+x,type=pathlib.Path,required=True)
    a=p.parse_args()
    inventory=json.loads(a.view.read_text());meta=json.loads(a.metadata.read_text())
    assert inventory["protocol"]=="DOCUMENTED_HTML_ESCAPING_V7"
    claims=conventional_rules(inventory)
    receipt={"protocol":"DOCUMENTED_HTML_ESCAPING_V7","arm":"expert_rule",
             "repository":meta["repository"],"source_sha":meta["source_sha"],
             "view_sha256":hashlib.sha256(a.view.read_bytes()).hexdigest(),
             "claims":claims,"status":"CANDIDATE_DOC_ATTRIBUTED" if claims
             else "UNKNOWN_NO_EXPLICIT_PUBLIC_ESCAPING_CONTRACT",
             "disclaimer":"Conventional expert-authored rulebook, not a recruited expert."}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("FROZEN_CONVENTIONAL_RULE_PRE_NATIVE",receipt["status"],[x["claim_id"] for x in claims])
if __name__=="__main__":main()
