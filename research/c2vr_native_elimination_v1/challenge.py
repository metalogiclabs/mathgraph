#!/usr/bin/env python3
"""Falsify adjudication using mutations of *real completed native logs*."""
import argparse,hashlib,json,shutil,tempfile
from pathlib import Path
from adjudicate import check

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def attack(root,tool,evidence):
    root,tool,evidence=map(Path,(root,tool,evidence))
    assert check(root,tool,evidence)["status"]=="WARRANTED_BOUNDED_NATIVE_OBLIGATION_PROBE"
    outcomes={"unmodified":"ACCEPTED"}
    cases=("missing_negative_log","modified_real_log","coordinated_fake_success",
           "extra_trusted_lemma","changed_original_program","missing_positive_program")
    for case in cases:
        with tempfile.TemporaryDirectory(prefix="native-evidence-control-") as tmp:
            copy=Path(tmp)/"evidence"
            shutil.copytree(evidence,copy,ignore=shutil.ignore_patterns("__pycache__"))
            receipt_path=copy/"receipt.json"
            receipt=json.loads(receipt_path.read_text())
            if case=="missing_negative_log":
                (copy/"gcd/negative.log").unlink()
            elif case=="modified_real_log":
                p=copy/"gcd/negative.log";p.write_bytes(p.read_bytes()+b"\nfalse success\n")
            elif case=="coordinated_fake_success":
                p=copy/"gcd/negative.log"
                shutil.copyfile(copy/"gcd/positive.log",p)
                receipt["lanes"]["gcd/negative"]["exit"]=0
                receipt["lanes"]["gcd/negative"]["log_sha256"]=digest(p)
            elif case=="extra_trusted_lemma":
                p=copy/"gcd/positive.rs"
                p.write_text(p.read_text().replace("} // verus!",
                             "#[verifier::external_body]\nproof fn unexpected_trust() {}\n} // verus!"))
                receipt["lanes"]["gcd/positive"]["program_sha256"]=digest(p)
            elif case=="changed_original_program":
                p=copy/"gcd/original.rs"
                shutil.copyfile(copy/"gcd/positive.rs",p)
                receipt["lanes"]["gcd/original"]["program_sha256"]=digest(p)
            else:
                (copy/"fibo/positive.rs").unlink()
            receipt_path.write_text(json.dumps(receipt,sort_keys=True))
            try:
                check(root,tool,copy)
                raise AssertionError("FALSE_ACCEPT:"+case)
            except ValueError as e:
                outcomes[case]="REJECTED:"+str(e)
    if len(outcomes)!=7:raise AssertionError("NEGATIVE_CENSUS")
    return outcomes

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("source",type=Path);parser.add_argument("tool",type=Path);parser.add_argument("evidence",type=Path)
    args=parser.parse_args()
    result=attack(args.source,args.tool,args.evidence)
    (args.evidence/"negative_controls.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))
