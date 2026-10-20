#!/usr/bin/env python3
"""Comprehensive synthetic-only V7 pre-exposure controls; no prospective source read."""
import importlib.util,json,pathlib,subprocess,sys,tempfile

HERE=pathlib.Path(__file__).resolve().parent

def load(name):
    spec=importlib.util.spec_from_file_location("v7_preflight_"+name,HERE/(name+".py"))
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

def main():
    inventory=load("doc_inventory")
    candidate=load("candidate")
    baseline=load("expert_rules")
    evaluate=load("evaluate_html")
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td);source=root/"source";source.mkdir()
        api=source/"renderkit.py"
        api.write_text(
            'import html\n'
            'def markdown(text, safe_mode=None):\n'
            '    return html.escape(text) if safe_mode == "escape" else text\n'
            'def render(text, escape_html=False):\n'
            '    return html.escape(text) if escape_html else text\n'
        )
        docs=source/"README.md"
        original=(
            "Call markdown(text, safe_mode='escape') to escape raw HTML as text, "
            "rather than render a raw HTML element.\n\n"
            "Call render(text, escape_html=True) to escape raw HTML as text "
            "without interpreting the markup as a tag.\n"
        )
        docs.write_text(original)
        meta={"repository":"synthetic/renderkit","source_sha":"a"*40}
        view=inventory.snapshot(source)
        claims=candidate.produce(view,meta)
        expert=baseline.conventional_rules(view)
        assert len(claims)==2,(view,claims)
        assert {x["claim_id"] for x in expert}=={x["claim_id"] for x in claims},expert
        sys.path.insert(0,str(source))
        native={"admitted":True,"tests":5,"failures":0,"errors":0,"skipped":0,"exit_code":0}
        for claim in claims:
            outcome=evaluate.audit_claim(claim,source,native)
            assert outcome["verdict"]=="WARRANTED_BOUNDED_DOC_BOUND_HTML_ESCAPE",outcome
            assert outcome["original_observation"]["retained_text"]
            assert outcome["original_observation"]["raw_script_count"]==0
        assert evaluate.observe(evaluate.PAYLOAD)["raw_script_count"]==1
        assert not evaluate.observe(evaluate.PAYLOAD)["retained_text"]
        for claim in claims:
            outcome=evaluate.audit_claim(claim,source,dict(native,admitted=False))
            assert outcome["verdict"]=="UNKNOWN_NO_NATIVE_AUTHORITY"
        view_path=root/"snapshot.json";view_path.write_text(json.dumps(view))
        meta_path=root/"metadata.json";meta_path.write_text(json.dumps(meta))
        withdraw=HERE/"withdraw_docs.py"
        receipt=root/"withdrawal.json"
        subprocess.run([sys.executable,str(withdraw),
             "--source",str(source),"--metadata",str(meta_path),
             "--view",str(view_path),"--candidate-script",str(HERE/"candidate.py"),
             "--inventory-script",str(HERE/"doc_inventory.py"),"--out",str(receipt)],
             check=True,capture_output=True,text=True)
        wr=json.loads(receipt.read_text())
        assert wr["status"]=="WARRANTED_BOUNDED_DOCUMENT_AUTHORITY_WITHDRAWAL",wr
        assert len(wr["changed_claims"])==1 and len(wr["unchanged_claims"])==1,wr
        assert wr["restoration"]=="BYTE_EXACT_AND_CLAIM_GRAPH_REQUALIFIED"
        assert docs.read_text()==original
        docs.write_text("Call markdown(text, safe_mode='escape') but do not escape raw HTML.\n")
        invalid=inventory.snapshot(source)
        assert not candidate.produce(invalid,meta),"NEGATED_AUTHOR_CLAIM_WAS_ADMITTED"
        assert not baseline.conventional_rules(invalid),"EXPERT_RULEBOOK_ATTRIBUTED_NEGATED_CLAIM"
        docs.write_text(original)
        changed=original.replace("Call markdown(text, safe_mode='escape') to escape raw HTML as text, ",
                                 "Call markdown(text, safe_mode='escape') to escape raw HTML as text, now revised ")
        docs.write_text(changed)
        try:
            evaluate.audit_claim(claims[0],source,native)
        except AssertionError:
            pass
        else:
            raise AssertionError("STALE_DOC_AUTHORITY_ACCEPTED")
        docs.write_text(original)
        assert inventory.snapshot(source)==view
    print("V7_DOC_TO_SEMANTIC_OBSERVER_PREFLIGHT_PASS positive2 comparator2 selective_withdraw1 unchanged1 stale_doc_rejected raw_negative1")

if __name__=="__main__":
    main()
