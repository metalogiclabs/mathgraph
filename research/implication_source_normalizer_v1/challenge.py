#!/usr/bin/env python3
"""Adversarial and positive controls on COPIES of authentic native observations.

All modifications are synthetic. None are changes to upstream Qwen programs.
Receipts are rehashed to ensure semantic checking rather than digest-only check.
"""
import hashlib,json,shutil,sys,tempfile
from pathlib import Path
from conventional_baseline import assess
from extractor import authorized
def digest(data):return hashlib.sha256(data).hexdigest()
def exercise(original):
    original=Path(original)
    positive=assess(original)
    if positive["verdict"]!="BASELINE_TIE" or positive["cases"]!=2394:
        raise AssertionError("MISSING_UNMODIFIED_POSITIVE_CONTROL")
    outcomes={"authentic_unmodified":"BASELINE_TIE"}
    mutations=[
      "scalar_max_wrong","array_max_wrong","all_even_bool_wrong",
      "conditional_even_index_wrong","double_index_wrong",
      "source_result_wrong","deleted_record","reordered_record",
      "forged_source_blob","permitted_odd_index_change"
    ]
    for change in mutations:
        with tempfile.TemporaryDirectory(prefix="acsl-implication-synthetic-") as tmp:
            dest=Path(tmp)
            shutil.copy2(original/"NATIVE_REPORT.json",dest/"NATIVE_REPORT.json")
            shutil.copy2(original/"OBSERVATIONS.jsonl",dest/"OBSERVATIONS.jsonl")
            meta=json.loads((dest/"NATIVE_REPORT.json").read_text())
            rows=[json.loads(x) for x in (dest/"OBSERVATIONS.jsonl").read_text().splitlines()]
            if change in ("scalar_max_wrong","array_max_wrong","all_even_bool_wrong","conditional_even_index_wrong","double_index_wrong","source_result_wrong","permitted_odd_index_change"):
                idx={"scalar_max_wrong":0,"array_max_wrong":1,"all_even_bool_wrong":2,
                    "conditional_even_index_wrong":3,"double_index_wrong":4,
                    "source_result_wrong":1,"permitted_odd_index_change":3}[change]
                selected=next(v for v in rows if v["case"]==idx and v["probe"] and
                    (len(v["before"])>1 or change=="scalar_max_wrong"))
                if change in ("scalar_max_wrong","array_max_wrong"):
                    selected["target_return"]=987654
                elif change=="all_even_bool_wrong":
                    selected["target_return"]=2
                elif change=="conditional_even_index_wrong":
                    selected["target_after"][0]=123
                elif change=="double_index_wrong":
                    selected["target_after"][1]=999
                elif change=="source_result_wrong":
                    selected["source_return"]=987654
                elif change=="permitted_odd_index_change":
                    selected["target_after"][1]=98765
                    assert authorized("EVEN_INDEX_ZERO_ONLY",tuple(selected["before"]),
                                      tuple(selected["target_after"]),None)
            elif change=="deleted_record":
                rows.pop(5)
            elif change=="reordered_record":
                rows[1],rows[2]=rows[2],rows[1]
            else:
                meta["source_blobs"][0]="0"*40
            data="".join(json.dumps(row,sort_keys=True)+"\n" for row in rows).encode()
            (dest/"OBSERVATIONS.jsonl").write_bytes(data)
            meta["native_observations_sha256"]=digest(data)
            (dest/"NATIVE_REPORT.json").write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
            try:result=assess(dest)["verdict"]
            except (KeyError,IndexError,ValueError) as exc:result="REJECTED_EVIDENCE:"+str(exc)
            if change=="permitted_odd_index_change":
                if result!="BASELINE_TIE":
                    raise AssertionError("FALSE_REJECTION_OF_PERMITTED_BEHAVIOUR:"+result)
            elif result!="BASELINE_CAUGHT_COUNTEREXAMPLE" and not result.startswith("REJECTED_EVIDENCE:"):
                raise AssertionError("FAIL_OPEN:"+change+":"+result)
            outcomes[change]=result
    report={"authentic_source_or_target_defects":0,
        "synthetic_negative_controls":len(mutations)-1,
        "negative_controls_caught_or_refused":len(mutations)-1,
        "positive_partial_spec_control_accepted":outcomes["permitted_odd_index_change"]=="BASELINE_TIE",
        "conventional_baseline_equal_information":True,
        "controls":outcomes,
        "scope":"Synthetic observation mutations, not real C/Rust program defects"}
    (original/"CHALLENGE_REPORT.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))
    return report
if __name__=="__main__":exercise(sys.argv[1])
