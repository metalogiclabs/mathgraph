#!/usr/bin/env python3
"""Physical structured author testpath authority withdrawal, then exact restoration.

Does not execute original source under edited test configuration. Reports precisely
the removed source evidence edge and surviving independent config authorities.
"""
import argparse,hashlib,importlib.util,json,pathlib,re


def sha(raw):return hashlib.sha256(raw).hexdigest()


def load(path):
    spec=importlib.util.spec_from_file_location("v9_frozen_scanner",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=pathlib.Path,required=True)
    p.add_argument("--proposal",type=pathlib.Path,required=True)
    p.add_argument("--scanner",type=pathlib.Path,required=True)
    p.add_argument("--out",type=pathlib.Path,required=True)
    a=p.parse_args()
    source=a.source.resolve()
    scanner=load(a.scanner)
    proposal=json.loads(a.proposal.read_text())
    before=scanner.scan(source)
    assert before==proposal["candidate"],"SEALED_SOURCE_AUTHORITY_DRIFT"
    selected=before["selected"]
    receipt={"state":"UNKNOWN_NO_CONFIG_AUTHORITY",
             "source":proposal["source"],"before_status":before["status"],
             "before_selected":selected,"mutated_revision_used_to_claim_native_success":False}
    if selected is not None:
        name=selected["authority_file"]
        path=source/name
        raw=path.read_bytes()
        assert sha(raw)==selected["authority_sha256"]
        text=raw.decode("utf8")
        lines=text.splitlines(keepends=True)
        matches=[i for i,l in enumerate(lines) if re.match(r"^\s*testpaths\s*=",l)]
        if len(matches)!=1 or not re.search(r"=\s*\[.*\]",lines[matches[0]]):
            receipt["state"]="UNKNOWN_UNSUPPORTED_PHYSICAL_TESTPATH_WITHDRAWAL"
        else:
            original_sha=sha(raw)
            lines[matches[0]]="# V9 experimental removal of one structured testpaths authority\n"
            try:
                path.write_text("".join(lines),encoding="utf8")
                after=scanner.scan(source)
            finally:
                path.write_bytes(raw)
            restored=scanner.scan(source)
            assert restored==before,"REQUALIFICATION_SOURCE_NOT_RESTORED"
            assert sha(path.read_bytes())==original_sha
            source_edge=(name,tuple(selected["testpaths"]))
            after_edges={(x["authority_file"],tuple(x["testpaths"])) for x in after["claims"]}
            assert source_edge not in after_edges,"WITHDRAWN_EDGE_STILL_PRESENT"
            receipt.update({"state":"WARRANTED_BOUNDED_STRUCTURED_AUTHORITY_WITHDRAW_RESTORE",
                            "source_file":name,"original_file_sha256":original_sha,
                            "after_status":after["status"],
                            "withdrawn_authority_edge":{"file":name,"testpaths":selected["testpaths"]},
                            "remaining_claims":after["claims"],
                            "source_file_restored_byte_exact":True,
                            "before_and_restored_scanner_equal":True,
                            "native_test_suite_not_executed_on_mutant":True})
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("V9_CONFIG_AUTHORITY_REQUALIFICATION",receipt["state"])


if __name__=="__main__":
    main()
