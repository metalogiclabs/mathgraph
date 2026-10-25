#!/usr/bin/env python3
"""Frozen API+author-documentation semantic obligation proposer.

A name is NOT a contract. Mode and escaping claim must both appear in one
source-document paragraph. No imports or execution before a sealed proposal.
"""
import argparse,hashlib,json,pathlib,re

def mode_from_prose(paragraph):
    text=paragraph.lower()
    if re.search(r"\bsafe_mode\s*(?:[:=]|is|to)\s*[^a-z0-9]{0,3}escape\b",text):
        return ("safe_mode","escape")
    if re.search(r"\bescape_html\s*(?:[:=]|is|to)\s*[^a-z0-9]{0,3}true\b",text):
        return ("escape_html",True)
    if re.search(r"\bescape\s*(?:[:=]|is|to)\s*[^a-z0-9]{0,3}true\b",text):
        return ("escape",True)
    return None

def explicitly_positive(paragraph):
    s=paragraph.lower()
    if not re.search(r"(?:escap\w{0,5}.{0,45}(?:raw\s+)?html|(?:raw\s+)?html.{0,45}escap\w{0,5})",s):
        return False
    for bad in (r"\b(?:not|never|doesn't|does not|won't|will not)\s+(?:be\s+)?escap",
                r"\bwithout\s+escap",r"\bno\s+escap"):
        if re.search(bad,s):return False
    return True

def produce(view,meta):
    claims=[]
    for doc in view["public_doc_paragraphs"]:
        text=doc["text"]
        setting=mode_from_prose(text)
        if setting is None or not explicitly_positive(text):
            continue
        mode,value=setting
        for api in view["api"]:
            if mode not in api["accepted_modes"]:
                continue
            if not re.search(r"\b"+re.escape(api["symbol"])+r"\s*\(",text,re.I):
                continue
            claims.append({
                "claim_id":api["module"]+"."+api["symbol"]+"::"+mode+"::escaped-text",
                "module":api["module"],"symbol":api["symbol"],"api_path":api["path"],
                "api_sha256":api["file_sha256"],"mode":mode,"value":value,
                "relation":"raw script tag absent AND original source text retained as HTML text",
                "document_path":doc["source_path"],"document_sha256":doc["source_sha256"],
                "document_paragraph":text,"paragraph_index":doc["paragraph_index"],
                "paragraph_sha256":doc["paragraph_sha256"],
                "scope":"one frozen literal raw HTML input; not HTML sanitization/security generally",
            })
    return sorted(claims,key=lambda c:(c["document_path"],c["api_path"],c["claim_id"]))[:3]

def main():
    p=argparse.ArgumentParser()
    for name in ("view","metadata","out"):p.add_argument("--"+name,type=pathlib.Path,required=True)
    a=p.parse_args()
    view=json.loads(a.view.read_text());meta=json.loads(a.metadata.read_text())
    assert view["protocol"]=="DOCUMENTED_HTML_ESCAPING_V7"
    claims=produce(view,meta)
    ret={"protocol":"DOCUMENTED_HTML_ESCAPING_V7","arm":"candidate",
         "repository":meta["repository"],"source_sha":meta["source_sha"],
         "view_sha256":hashlib.sha256(a.view.read_bytes()).hexdigest(),
         "claims":claims,
         "status":"CANDIDATE_DOC_ATTRIBUTED" if claims else "UNKNOWN_NO_EXPLICIT_PUBLIC_ESCAPING_CONTRACT"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(ret,indent=2,sort_keys=True)+"\n")
    print("FROZEN_CANDIDATE_PRE_NATIVE",ret["status"],[c["claim_id"] for c in claims])
if __name__=="__main__":main()
