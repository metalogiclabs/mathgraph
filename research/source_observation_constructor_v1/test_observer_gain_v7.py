#!/usr/bin/env python3
"""Independent partition-oracle tests for finite F1 V7 sensor novelty."""
import importlib.util
import itertools
import json
import random
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("mg_observer_v7",HERE/"observer_gain_v7.py")
m=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=m
spec.loader.exec_module(m)

def independent_partition(model, sensors):
    """No pair-cover algorithm: enumerate observation fibers and decision labels."""
    options=[]
    for count in range(len(sensors)+1):
        for sub in itertools.combinations(sensors,count):
            cells={}
            for i in range(len(model.worlds)):
                observation=tuple(s.readings[i] for s in sub)
                cells.setdefault(observation,set()).add(model.decisions[i])
            if all(len(decisions)==1 for decisions in cells.values()):
                options.append((sum(s.cost for s in sub),len(sub),
                                tuple(sorted(s.name for s in sub))))
    return min(options) if options else None

def run(archive=None):
    cases=m.fixtures()
    declared={
        "new_coupling":"NEW_DECLARED_DECISION_DISTINCTION",
        "mere_relabel":"OBSTRUCTED_WITHIN_DECLARED_GRAMMAR",
        "combined_senses":"NEW_DECLARED_DECISION_DISTINCTION",
        "efficiency_not_novelty":"CHEAPER_EXISTING_DECISION_INFORMATION",
        "duplicate_sensor":"NO_NEW_DECISION_INFORMATION",
        "raw_information_not_decision":"NO_NEW_DECISION_INFORMATION",
    }
    for name,case in cases.items():
        actual=m.evaluate(case)
        assert actual["classification"]==declared[name],(name,actual)
        assert actual["old_basis"]==independent_partition(case,case.old)
        assert actual["extended_basis"]==independent_partition(case,case.old+case.new)
    assert m.evaluate(cases["new_coupling"],{"source"})["classification"]=="OBSTRUCTED_WITHIN_DECLARED_GRAMMAR"
    assert m.evaluate(cases["new_coupling"],{"source","coupling_permission"})["classification"]=="NEW_DECLARED_DECISION_DISTINCTION"

    # A deterministic postprocessor of existing signals cannot split a fiber.
    for seed in range(512):
        rng=random.Random(seed)
        original=("0","1","0","1")
        recode={"0":str(rng.randrange(100)),"1":str(rng.randrange(100))}
        model=m.Model(("A","B","C","D"),("0","0","1","1"),
            (m.Sensor("original",original,1),),
            (m.Sensor("derived",tuple(recode[x] for x in original),1),))
        assert m.evaluate(model)["classification"]=="OBSTRUCTED_WITHIN_DECLARED_GRAMMAR"

    # Bounded randomized exhaustive exact-solver vs independently formulated oracle.
    rng=random.Random(20261026)
    randomized=0
    for n in range(2,6):
        for _ in range(500):
            decisions=tuple(str(rng.randrange(3)) for _ in range(n))
            old=tuple(m.Sensor("o"+str(j),tuple(str(rng.randrange(3)) for _ in range(n)),rng.randrange(1,7))
                      for j in range(rng.randrange(4)))
            new=tuple(m.Sensor("n"+str(j),tuple(str(rng.randrange(3)) for _ in range(n)),rng.randrange(1,7))
                      for j in range(rng.randrange(4)))
            case=m.Model(tuple(str(i) for i in range(n)),decisions,old,new)
            got=m.evaluate(case)
            x=independent_partition(case,old)
            y=independent_partition(case,old+new)
            assert got["old_basis"]==x and got["extended_basis"]==y
            wanted=("NEW_DECLARED_DECISION_DISTINCTION" if x is None and y is not None
                    else "OBSTRUCTED_WITHIN_DECLARED_GRAMMAR" if x is None
                    else "CHEAPER_EXISTING_DECISION_INFORMATION" if y[0]<x[0]
                    else "NO_NEW_DECISION_INFORMATION")
            assert got["classification"]==wanted,(got,wanted)
            randomized+=1

    # Complete binary truth tables of three worlds / decision plus three channels.
    exhaustive=0
    for values in itertools.product(("0","1"),repeat=12):
        a,b,c,d=[values[i:i+3] for i in range(0,12,3)]
        case=m.Model(("0","1","2"),a,
            (m.Sensor("old_a",b,1),m.Sensor("old_b",c,2)),
            (m.Sensor("added",d,3),))
        got=m.evaluate(case)
        assert got["old_basis"]==independent_partition(case,case.old)
        assert got["extended_basis"]==independent_partition(case,case.old+case.new)
        exhaustive+=1

    report={
        "status":"PASS_F1_V7_FINITE_PARTITION_ORACLE",
        "randomized_models":randomized,
        "exhaustive_binary_models":exhaustive,
        "postprocessor_no_new_sense_cases":512,
        "fixtures":declared,
        "protected_heldout_sources_accessed":False,
        "not_established":["physical sensor availability","autonomous operator-grammar invention",
                           "authentic prospective source effect","superiority over matched conventional method"],
    }
    if archive is not None:
        historical=m.native_receipt_v5_as_model(Path(archive))
        ordinary=independent_partition(historical,historical.old)
        together=independent_partition(historical,historical.old+historical.new)
        assert ordinary is not None and together==ordinary
        result=m.evaluate(historical)
        assert result["classification"]=="NO_NEW_DECISION_INFORMATION"
        assert m.evaluate(historical,{"authenticated_v5"})["classification"]=="NO_NEW_DECISION_INFORMATION"
        report["historical_exposed_v5"]={
          "source":"pinned V5 original artifact",
          "classification":result["classification"],
          "old_optimum":ordinary,
          "joint_optimum":together,
          "author_doc_withdrawal":m.evaluate(historical,{"authenticated_v5"})["classification"],
          "scope":"conditional on independent V6 raw artifact verification, not on candidate claims",
        }
    return report

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--v5",type=Path)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    result=run(args.v5)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":result["status"],
                      "exhaustive":result["exhaustive_binary_models"],
                      "randomized":result["randomized_models"],
                      "historical":result.get("historical_exposed_v5",{}).get("classification")},sort_keys=True))
