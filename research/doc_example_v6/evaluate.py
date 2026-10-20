#!/usr/bin/env python3
"""Qualify frozen literal source-doctest correspondence and stdlib incumbent.

Both candidate and stdlib doctest see the SAME source-attested example and runtime.
No human expert is claimed, no arbitrary documentation code is executed.
"""
import argparse,ast,doctest,hashlib,importlib,json,pathlib,sys,xml.etree.ElementTree as ET


def native_tests(path):
    doc=ET.parse(path).getroot()
    suites=[doc] if doc.tag=="testsuite" else list(doc.iter("testsuite"))
    result={k:sum(int(x.attrib.get(k,0)) for x in suites) for k in ("tests","failures","errors","skipped")}
    result["admitted"]=result["tests"]>result["skipped"] and result["failures"]==result["errors"]==0
    return result


def get_callable(module,item):
    if item["class"]:
        factory=getattr(module,item["class"],None)
        if not callable(factory):
            return None
        instance=factory()
        return getattr(instance,item["method"],None)
    return getattr(module,item["method"],None)


def fake_expected(x):
    if isinstance(x,str):return x+"__WRONG_EXPECTED__"
    if isinstance(x,bool):return not x
    if isinstance(x,(int,float)):return x+1
    if isinstance(x,list):return x+["__WRONG_EXPECTED__"]
    return "__WRONG_EXPECTED__"


def source_doctest_baseline(module,item):
    """Use existing standard-library doctest machinery, same example/permissions."""
    if item["class"]:
        cls=getattr(module,item["class"])
        expr=ast.parse(item["source_example"],mode="eval").body
        target=expr.func.value
        names={item["class"]:cls}
        if isinstance(target,ast.Name):
            names[target.id]=cls()
    else:
        names={item["method"]:getattr(module,item["method"])}
    snippet=">>> "+item["source_example"]+"\n"+item["wanted_repr"]+"\n"
    test=doctest.DocTestParser().get_doctest(snippet,names,"safe-source-example",None,0)
    runner=doctest.DocTestRunner(verbose=False)
    result=runner.run(test,out=lambda x:None,clear_globs=False)
    return {"attempted":result.attempted,"failed":result.failed}


def judge(proposals,module,original_native,source_root):
    rows=[]
    for i,item in enumerate(proposals["obligations"]):
        p=source_root/item["source_path"]
        expected_source=hashlib.sha256(p.read_bytes()).hexdigest()
        assert expected_source==item["source_file_sha256"],"DOC_SOURCE_CHANGED_AFTER_FREEZE"
        row={"id":i,"relation":item["relation"],"authority":{
            "source_path":item["source_path"],"sha256":item["source_file_sha256"],
            "doc_sha256":item["doc_sha256"],"source_line":item["source_line"],
            "example":item["source_example"],"wanted":item["wanted_repr"]}}
        if not original_native["admitted"]:
            row["verdict"]="UNKNOWN_NO_NATIVE_AUTHORITY"
            rows.append(row)
            continue
        try:
            fn=get_callable(module,item)
            if not callable(fn):
                row["verdict"]="UNKNOWN_UNRESOLVED_PUBLIC_CALLABLE"
                rows.append(row)
                continue
            actual=fn(*item["args"],**item["kwargs"])
            expected=item["expected"]
            same=(actual==expected and type(actual)==type(expected))
            negative=(actual!=fake_expected(expected))
            doctest_reference=source_doctest_baseline(module,item)
            row["actual_repr"]=repr(actual)[:320]
            row["actual_type"]=type(actual).__name__
            row["independent_negative_rejected"]=bool(negative)
            row["stdlib_doctest_reference"]=doctest_reference
            if not same:
                row["verdict"]="REJECTED_BOUNDED_SOURCE_EXAMPLE"
            elif not negative:
                row["verdict"]="UNKNOWN_NEGATIVE_CONTROL"
            elif doctest_reference=={"attempted":1,"failed":0}:
                row["verdict"]="WARRANTED_BOUNDED_SOURCE_DOC_EXAMPLE"
            else:
                row["verdict"]="UNKNOWN_ORACLE_DISAGREEMENT"
        except Exception as e:
            row["verdict"]="UNKNOWN_UNSUPPORTED_SOURCE_EXECUTION"
            row["error"]=type(e).__name__+":"+str(e)[:200]
        rows.append(row)
    return rows


def main():
    parser=argparse.ArgumentParser()
    for name in ("metadata","proposals","source","native_junit","out"):
        parser.add_argument("--"+name.replace("_","-"),type=pathlib.Path,required=True)
    a=parser.parse_args()
    meta=json.loads(a.metadata.read_text())
    prop=json.loads(a.proposals.read_text())
    assert meta["repository"]==prop["repository"] and meta["source_sha"]==prop["source_sha"]
    source=a.source.resolve()
    sys.path.insert(0,str(source/"src"))
    sys.path.insert(0,str(source))
    module=importlib.import_module(prop["api"]["module"])
    assert pathlib.Path(module.__file__).resolve().is_relative_to(source),"INCORRECT_NATIVE_IMPORT"
    native=native_tests(a.native_junit)
    rows=judge(prop,module,native,source)
    passed=sum(x["verdict"]=="WARRANTED_BOUNDED_SOURCE_DOC_EXAMPLE" for x in rows)
    rejected=sum(x["verdict"]=="REJECTED_BOUNDED_SOURCE_EXAMPLE" for x in rows)
    baseline_positive=sum(x.get("stdlib_doctest_reference")=={"attempted":1,"failed":0} for x in rows)
    result={"source":meta,"native":native,"candidate_source_doc_warrants":passed,
            "source_doc_examples_rejected":rejected,
            "stdlib_doctest_reference_warrants":baseline_positive,
            "comparison":"TIE" if passed==baseline_positive and passed else
                "INCONCLUSIVE_ZERO_CLAIMS" if not rows else "BOUNDARY_MISMATCH_INVESTIGATE",
            "observations":rows,"status":"BOUNDED_NATIVE_EXAMPLES" if rows else "UNKNOWN_NO_APPLICABLE_DOC_EXAMPLES",
            "baseline":"Python stdlib doctest of SAME safe examples, not a blinded expert reviewer",
            "proposals_sha256":hashlib.sha256(a.proposals.read_bytes()).hexdigest(),
            "native_junit_sha256":hashlib.sha256(a.native_junit.read_bytes()).hexdigest(),
            "limitations":"Attests only literal documentation examples and original native source, not general author intent or autonomous grammar invention"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("DOC_EXAMPLE_NATIVE_RESULT",json.dumps({"native":native,"candidate":passed,"stdlib_doctest":baseline_positive,
          "rejected":rejected,"comparison":result["comparison"],"state":result["status"]},sort_keys=True))


if __name__=="__main__":
    main()
