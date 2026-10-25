#!/usr/bin/env python3
"""V7 independent HTML meaning + selective source attribution evaluator.

No source author claim is admitted without exact doc bytes and API-file SHA.
"""
import argparse,hashlib,html.parser,importlib,json,pathlib,sys,xml.etree.ElementTree as ET

PAYLOAD='<script data-mg="yes">audit_me</script>'

class HTMLObserver(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.script_tags=[]
        self.text=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower()=="script":
            self.script_tags.append(dict(attrs))
    def handle_data(self,data):
        self.text.append(data)

def observe(html_text):
    if not isinstance(html_text,str):
        return {"supported":False}
    parser=HTMLObserver();parser.feed(html_text);parser.close()
    return {"supported":True,
            "raw_script_count":len(parser.script_tags),
            "retained_text":PAYLOAD in "".join(parser.text),
            "native_output_sha256":hashlib.sha256(html_text.encode()).hexdigest()}

def native_gate(junit,exitfile):
    root=ET.parse(junit).getroot()
    suites=[root] if root.tag=="testsuite" else list(root.iter("testsuite"))
    r={k:sum(int(n.attrib.get(k,0)) for n in suites)
       for k in ("tests","failures","errors","skipped")}
    r["exit_code"]=int(exitfile.read_text().strip())
    r["admitted"]=(r["tests"]>r["skipped"] and r["failures"]==r["errors"]==0 and r["exit_code"]==0)
    return r

def audit_claim(claim,root,native):
    file=root/claim["document_path"]
    api=root/claim["api_path"]
    assert hashlib.sha256(file.read_bytes()).hexdigest()==claim["document_sha256"],"CHANGED_DOCUMENT_AUTHORITY"
    assert hashlib.sha256(api.read_bytes()).hexdigest()==claim["api_sha256"],"CHANGED_PUBLIC_API_AUTHORITY"
    row={"claim_id":claim["claim_id"],
         "document_path":claim["document_path"],"paragraph_sha256":claim["paragraph_sha256"],
         "api_path":claim["api_path"],"mode":claim["mode"],
         "verdict":"UNKNOWN_NO_NATIVE_AUTHORITY"}
    if not native["admitted"]:
        return row
    try:
        if claim["module"] in sys.modules:del sys.modules[claim["module"]]
        module=importlib.import_module(claim["module"])
        src=pathlib.Path(module.__file__).resolve()
        assert src.is_relative_to(root.resolve()),"WRONG_IMPORTED_MODULE"
        fn=getattr(module,claim["symbol"])
        output=fn(PAYLOAD,**{claim["mode"]:claim["value"]})
        witness=observe(output)
        raw_control=observe(PAYLOAD)
        assert raw_control["raw_script_count"]==1 and not raw_control["retained_text"], "INDEPENDENT_HTML_ORACLE_BROKEN"
        row["original_observation"]=witness
        row["negative_control"]=raw_control
        if not witness["supported"]:
            row["verdict"]="UNKNOWN_UNSUPPORTED_OUTPUT"
        elif witness["raw_script_count"]==0 and witness["retained_text"]:
            row["verdict"]="WARRANTED_BOUNDED_DOC_BOUND_HTML_ESCAPE"
        else:
            row["verdict"]="REJECTED_BOUNDED_DOCUMENTED_ESCAPING_RELATION"
    except (TypeError,ValueError,ImportError,AttributeError,AssertionError) as e:
        row["verdict"]="UNKNOWN_UNSUPPORTED_NATIVE_CALL"
        row["error"]=type(e).__name__+":"+str(e)[:200]
    return row

def main():
    p=argparse.ArgumentParser()
    for x in ("metadata","view","candidate","expert","source","native_junit","native_exit","out"):
        p.add_argument("--"+x.replace("_","-"),type=pathlib.Path,required=True)
    a=p.parse_args()
    root=a.source.resolve()
    meta=json.loads(a.metadata.read_text());view=json.loads(a.view.read_text())
    proposals={name:json.loads(getattr(a,name).read_text()) for name in ("candidate","expert")}
    assert view["protocol"]=="DOCUMENTED_HTML_ESCAPING_V7"
    for name,rec in proposals.items():
        assert rec["arm"]==("expert_rule" if name=="expert" else "candidate")
        assert rec["repository"]==meta["repository"] and rec["source_sha"]==meta["source_sha"]
        assert rec["view_sha256"]==hashlib.sha256(a.view.read_bytes()).hexdigest()
        for claim in rec["claims"]:
            assert any(claim["document_sha256"]==doc["source_sha256"]
                       and claim["paragraph_sha256"]==doc["paragraph_sha256"]
                       and claim["document_paragraph"]==doc["text"]
                       for doc in view["public_doc_paragraphs"]),"UNBOUND_DOC_CLAIM"
            assert any(claim["api_path"]==api["path"] and claim["api_sha256"]==api["file_sha256"]
                       and claim["mode"] in api["accepted_modes"] for api in view["api"]),"UNBOUND_API"
    sys.path.insert(0,str(root/"src"))
    sys.path.insert(0,str(root/"lib"))
    sys.path.insert(0,str(root))
    native=native_gate(a.native_junit,a.native_exit)
    arms={name:[audit_claim(x,root,native) for x in proposals[name]["claims"]]
          for name in ("candidate","expert")}
    label="WARRANTED_BOUNDED_DOC_BOUND_HTML_ESCAPE"
    c=sum(x["verdict"]==label for x in arms["candidate"])
    e=sum(x["verdict"]==label for x in arms["expert"])
    if not arms["candidate"] and not arms["expert"]:
        comparison="INCONCLUSIVE_ZERO_APPLICABLE"
    elif not native["admitted"]:
        comparison="INCONCLUSIVE_NATIVE_RED"
    else:
        comparison="TIE" if c==e else "CANDIDATE_AHEAD_RULEBOOK" if c>e else "EXPERT_RULEBOOK_AHEAD"
    ret={"protocol":"DOCUMENTED_HTML_ESCAPING_V7",
         "source":meta,"native":native,"arms":arms,
         "comparison":{"candidate_warrants":c,"expert_rule_warrants":e,"verdict":comparison,
            "baseline":"independently coded conventional expert-rule matcher; NOT recruited human"},
         "science_status":"WARRANTED_BOUNDED_ONE_HTML_SEMANTIC_RELATION"
             if c>0 else "UNKNOWN_NO_POSITIVE_PROSPECTIVE_RELATION",
         "proposal_sha256":{n:hashlib.sha256(getattr(a,n).read_bytes()).hexdigest()
                            for n in ("candidate","expert")},
         "native_junit_sha256":hashlib.sha256(a.native_junit.read_bytes()).hexdigest(),
         "limits":"One raw script test and source-declared escaping configuration only. No general sanitization, browser safety, author-intent psychology, G2 or human-expert advantage."}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(ret,sort_keys=True,indent=2)+"\n")
    print("V7_DOCUMENTED_HTML_SEMANTIC_PROSPECT",json.dumps({
        "native":native,"candidate":arms["candidate"],"expert":arms["expert"],
        "comparison":comparison,"science_status":ret["science_status"]},sort_keys=True))

if __name__=="__main__":main()
