#!/usr/bin/env python3
"""Physical *documentation authority* withdrawal in an ephemeral checkout.

The native code remains byte-identical. Requalification requires restoration
of exact original bytes and rescanning with the frozen source-neutral grammar.
"""
import argparse,hashlib,importlib.util,json,pathlib,re

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,str(path))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def sha(x):
    return hashlib.sha256(x).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    for x in ("source","metadata","view","candidate_script","inventory_script","out"):
        ap.add_argument("--"+x.replace("_","-"),type=pathlib.Path,required=True)
    a=ap.parse_args()
    root=a.source
    meta=json.loads(a.metadata.read_text())
    original=json.loads(a.view.read_text())
    candidate=load("v7_candidate",a.candidate_script)
    inventory=load("v7_inventory",a.inventory_script)
    before=candidate.produce(original,meta)
    if not before:
        receipt={"status":"UNKNOWN_NO_DOCUMENTED_CLAIM_TO_WITHDRAW",
                 "changed_claims":[],"unchanged_claims":[]}
    else:
        target=before[0]
        path=root/target["document_path"]
        raw=path.read_bytes()
        pieces=re.split(r"(\n\s*\n+)",raw.decode("utf-8"))
        index=target["paragraph_index"]
        pos=index*2
        assert pos<len(pieces),"MISSING_ORIGINAL_DOCUMENT_PARAGRAPH"
        original_text=" ".join(pieces[pos].split())
        assert sha(original_text.encode())==target["paragraph_sha256"],"WRONG_PARAGRAPH_AUTHORITY"
        pieces[pos]="Documented HTML escaping statement intentionally withdrawn for local audit."
        try:
            path.write_text("".join(pieces))
            mutated=inventory.snapshot(root)
            after=candidate.produce(mutated,meta)
            before_keys={(x["claim_id"],x["document_path"],x["paragraph_index"]) for x in before}
            after_keys={(x["claim_id"],x["document_path"],x["paragraph_index"]) for x in after}
            expected_lost={x for x in before_keys if x[1:]==(target["document_path"],target["paragraph_index"])}
            assert before_keys-after_keys==expected_lost, "NONSPECIFIC_AUTHORITY_WITHDRAWAL"
            assert not (after_keys-before_keys), "NOVEL_CLAIM_APPEARED_AFTER_WITHDRAWAL"
            receipt={"status":"WARRANTED_BOUNDED_DOCUMENT_AUTHORITY_WITHDRAWAL",
                     "withdrawn_paragraph":target["document_path"]+":"+str(target["paragraph_index"]),
                     "changed_claims":sorted(str(x) for x in expected_lost),
                     "unchanged_claims":sorted(str(x) for x in (before_keys & after_keys)),
                     "native_code_modified":False}
        finally:
            path.write_bytes(raw)
        restored=inventory.snapshot(root)
        after_restore=candidate.produce(restored,meta)
        assert sha(path.read_bytes())==sha(raw), "DOC_BYTES_NOT_RESTORED"
        assert after_restore==before, "DOCUMENTED_WARRANT_NOT_REQUALIFIED_AFTER_RESTORE"
        receipt["restored_source_sha256"]=sha(raw)
        receipt["restoration"] ="BYTE_EXACT_AND_CLAIM_GRAPH_REQUALIFIED"
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("V7_DOC_AUTHORITY_WITHDRAWAL",receipt["status"],receipt.get("restoration"))

if __name__=="__main__":main()
