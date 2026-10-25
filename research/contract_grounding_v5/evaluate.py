#!/usr/bin/env python3
"""Verify presealed doc-attributed claims with native source and independent stdlib relations."""
import argparse,hashlib,importlib,json,pathlib,sys,xml.etree.ElementTree as ET

INPUTS=[
    "HelloWorld",
    "USER_name",
    "Mixed_Case",
    "already_lower",
    "two_words_here",
    " With Spaces ",
]


def native_tests(junit):
    root=ET.parse(junit).getroot()
    suites=[root] if root.tag=="testsuite" else list(root.iter("testsuite"))
    totals={k:sum(int(x.attrib.get(k,0)) for x in suites)
            for k in ("tests","failures","errors","skipped")}
    totals["native_admissible"]=totals["tests"]>totals["skipped"] and totals["failures"]==totals["errors"]==0
    return totals


def relation_oracle(relation,value):
    if not isinstance(value,str):
        return None
    if relation=="lowercase-output":
        return value==value.lower()
    if relation=="uppercase-output":
        return value==value.upper()
    if relation=="underscore-elimination":
        return "_" not in value
    if relation=="trim-surrounding-space":
        return value==value.strip()
    return None


def malformed(relation,value):
    return (value+"A" if relation=="lowercase-output" else
            value+"a" if relation=="uppercase-output" else
            value+"_" if relation=="underscore-elimination" else
            " "+value+" " if relation=="trim-surrounding-space" else value)


def evaluate_arm(proposal,module,native,view):
    records=[]
    for claim in proposal["claims"]:
        assert claim["claim_id"]==claim["symbol"]+"::"+claim["relation"]
        docs=[x for x in view["contracts"] if x["symbol"]==claim["symbol"] and x["doc_sha256"]==claim["doc_sha256"]
              and x["relative_source_path"]==claim["relative_source_path"]
              and x["source_sha256"]==claim["source_sha256"]]
        assert len(docs)==1, "MISSING_OR_CHANGED_SOURCE_DECLARED_AUTHORITY"
        assert claim["authority_sentence"] in " ".join(docs[0]["docstring"].split()), "CLAUSE_NOT_IN_AUTHORITY"
        obj=getattr(module,claim["symbol"],None)
        row={"claim_id":claim["claim_id"],"evidence":claim,"observations":[]}
        if not callable(obj):
            row["verdict"]="UNKNOWN_NOT_CALLABLE"
            records.append(row)
            continue
        for index,source in enumerate(INPUTS):
            try:
                value=obj(source)
                good=relation_oracle(claim["relation"],value)
                bad=(relation_oracle(claim["relation"],malformed(claim["relation"],value)) is False
                     if isinstance(value,str) else None)
                row["observations"].append({"index":index,"input":source,"output":repr(value)[:300],
                                            "is_string":isinstance(value,str),"relation_holds":good,
                                            "malformed_output_rejected":bad})
            except Exception as exc:
                row["observations"].append({"index":index,"input":source,
                                            "relation_holds":None,"malformed_output_rejected":None,
                                            "exception":type(exc).__name__+":"+str(exc)[:180]})
        results=[x["relation_holds"] for x in row["observations"]]
        negatives=[x["malformed_output_rejected"] for x in row["observations"]]
        outputs=[x.get("output") for x in row["observations"]]
        if not native["native_admissible"]:
            row["verdict"]="UNKNOWN_NATIVE_AUTHORITY"
        elif any(x is False for x in results):
            row["verdict"]="REJECTED_BOUNDED_DOC_ATTRIBUTED_RELATION"
        elif not all(x is True for x in results):
            row["verdict"]="UNKNOWN_UNSUPPORTED_SOURCE_INPUT"
        elif not all(x is True for x in negatives):
            row["verdict"]="UNKNOWN_INDEPENDENT_NEGATIVE_CONTROL"
        elif len(set(outputs))<2:
            row["verdict"]="UNKNOWN_VACUOUS_CONSTANT_OUTPUT"
        else:
            row["verdict"]="WARRANTED_BOUNDED_DOC_BOUND_REFERENCE"
        records.append(row)
    return {"arm":proposal["arm"],"status":proposal["status"],"results":records}


def main():
    ap=argparse.ArgumentParser()
    for name in ("metadata","view","candidate","expert","source","native_junit","out"):
        ap.add_argument("--"+name.replace("_","-"),type=pathlib.Path,required=True)
    a=ap.parse_args()
    metadata=json.loads(a.metadata.read_text())
    view=json.loads(a.view.read_text())
    proposals={name:json.loads(getattr(a,name).read_text()) for name in ("candidate","expert")}
    for name,prop in proposals.items():
        assert prop["arm"]==name
        assert prop["repository"]==metadata["repository"]
        assert prop["source_sha"]==metadata["source_sha"]
        assert prop["api_sha256"]==view["api"]["api_sha256"]
    assert view["api"]["status"]=="STATIC_EXPORT_CLOSURE_BOUNDED"
    pkg=view["api"]["module"]
    root=a.source.resolve()
    sys.path.insert(0,str(root/"src"))
    sys.path.insert(0,str(root))
    native=native_tests(a.native_junit)
    module=importlib.import_module(pkg)
    assert pathlib.Path(module.__file__).resolve().is_relative_to(root),"IMPORTED_NON_NATIVE_SOURCE"
    arms={name:evaluate_arm(prop,module,native,view) for name,prop in proposals.items()}
    def count(arm,verdict):
        return sum(x["verdict"]==verdict for x in arm["results"])
    wanted="WARRANTED_BOUNDED_DOC_BOUND_REFERENCE"
    c=count(arms["candidate"],wanted); e=count(arms["expert"],wanted)
    result={
        "protocol":"DOC_BOUND_SEMANTIC_OBLIGATION_V5",
        "source_sha":metadata["source_sha"],
        "native":native,
        "arms":arms,
        "comparison":{"candidate_warrants":c,"expert_rule_warrants":e,"advantage":c-e,
                      "verdict":"TIE" if c==e else "CANDIDATE_AHEAD" if c>e else "EXPERT_RULE_AHEAD",
                      "baseline":"Source-doc-equally-informed separate conventional expert rulebook, NOT real human expert"},
        "proposals_sha256":{k:hashlib.sha256(getattr(a,k).read_bytes()).hexdigest()
                             for k in ("candidate","expert")},
        "native_junit_sha256":hashlib.sha256(a.native_junit.read_bytes()).hexdigest(),
        "bounds":"Six fixed strings, explicit source docs, author native suite and stdlib output properties. No universal semantic intent theorem; no automatic grammar invention.",
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("CONTRACT_GROUNDED_PROSPECTIVE",json.dumps({
        "native":native,"candidate":{q["claim_id"]:q["verdict"] for q in arms["candidate"]["results"]},
        "expert":{q["claim_id"]:q["verdict"] for q in arms["expert"]["results"]},
        "comparison":result["comparison"]},sort_keys=True))


if __name__=="__main__":
    main()
