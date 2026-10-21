#!/usr/bin/env python3
"""Independent exact subset and decoder oracle for decision mode, without using its search."""
import json
from itertools import combinations, product
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from decision_sufficient_observation_v1.audit import partitions, independent_opt, kernel, measure
from decision_sufficient_observation_v1.decision_mode import compile_decision_sufficient

def check_decoder(record, goal, readouts, names, base=()):
    assert record["status"] == "DECISION_SUFFICIENT_BASIS"
    chosen=record["basis"]
    for p in chosen:
        assert len(p["program"]) == 1 or len(p["program"]) >= 2
    decoder={tuple(r["observed"]):r["decision"] for r in record["decoder"]}
    for i, expected in enumerate(goal):
        observed=tuple(readouts[name][i] for name in base)
        for o in chosen:
            observed+=(o["values"][i],)
        assert observed in decoder and decoder[observed]==expected, (i,observed,record)

def test_small_panels():
    checks=0
    counts={}
    for n in (3,4):
        readouts=list(product((0,1),repeat=n))
        failures=0
        for goal in partitions(n):
            for panel in combinations(readouts,2):
                obj={"name":"test","protected":list(goal),
                    "operations":[],
                    "readouts":[{"name":f"r{i}","values":list(a),"cost":1}
                                for i,a in enumerate(panel)],
                    "grants":["r0","r1"],"base_readouts":[],
                    "desired_labels":list(goal)}
                got=compile_decision_sufficient(obj)
                opt=independent_opt(panel,goal,"sufficient")
                if opt is None:
                    assert got["status"]=="UNREALIZABLE_DECISION_IN_DECLARED_FINITE_GRAMMAR",got
                    assert got["diagnosis"]=="NO_SOURCE_DECLARED_SAFE_OPERATOR_SUFFICIENT",got
                else:
                    assert got["status"]=="DECISION_SUFFICIENT_BASIS",got
                    assert got["basis_cost"]==opt["cost"],(n,goal,panel,got,opt)
                    check_decoder(got,goal,{"r0":panel[0],"r1":panel[1]},["r0","r1"])
                checks+=1
        counts[str(n)]=checks
    return {"checked":checks,"states_3_cases":140,"states_4_cases":1800}

def test_protection_permission_and_effects():
    state_dir=ROOT/"consequence_experiment_compiler_v1"
    obj=json.loads((state_dir/"example_model.json").read_text())
    result=compile_decision_sufficient(obj)
    assert result["status"]=="DECISION_SUFFICIENT_BASIS" and result["basis_cost"]==4,result
    assert result["basis"][0]["program"]==["couple_h_xor_r","read_r"],result
    by_name={r["name"]:tuple(r["values"]) for r in obj["readouts"]}
    check_decoder(result,tuple(obj["desired_labels"]),by_name,list(by_name),tuple(obj["base_readouts"]))
    # Changing the granted coupling *without changing source-defined tables*
    # must revoke the observed decision and NOT admit destructive alternatives.
    changed=json.loads(json.dumps(obj))
    changed["grants"].remove("couple_h_xor_r")
    denied=compile_decision_sufficient(changed)
    assert denied["status"]=="UNREALIZABLE_DECISION_IN_DECLARED_FINITE_GRAMMAR",denied
    assert denied["diagnosis"]=="MISSING_PERMISSION_FOR_EXISTING_SAFE_OPERATOR",denied
    assert denied["hypothetical_granted_cost"]==4
    # Existing safe coupling becomes inadmissible if protection expands to record.
    unsafe=json.loads(json.dumps(obj))
    unsafe["protected"]=list(range(4))
    no_safe=compile_decision_sufficient(unsafe)
    assert no_safe["status"]=="UNREALIZABLE_DECISION_IN_DECLARED_FINITE_GRAMMAR",no_safe
    assert no_safe["diagnosis"]=="NO_SOURCE_DECLARED_SAFE_OPERATOR_SUFFICIENT",no_safe
    # Original source bytes/compiled code remain untouched.
    return {"original_effect_goal_cost":result["basis_cost"],
        "withdrawn_grant":"MISSING_PERMISSION",
        "expanded_protection":"NO_SOURCE_DECLARED_SAFE_OPERATOR"}

def main():
    c=test_small_panels()
    p=test_protection_permission_and_effects()
    result={"status":"DECISION_SUFFICIENCY_MODE_FINITE_ORACLE_PASS",
        "native_original_v1_unchanged":True,
        "finite_test":c,"effectful_protection_and_grant_checks":p,
        "limitations":["fully supplied finite deterministic readout/action semantics",
                       "known deterministic goal labels, no stochastic data",
                       "no new physical operator, no real-source transfer",
                       "no runtime or cost advantage versus equally informed exact baseline"]}
    out=Path("out/decision_sufficiency_falsifier")
    out.mkdir(parents=True,exist_ok=True)
    (out/"decision_mode_report.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("DECISION_SUFFICIENCY_MODE_RESULT="+json.dumps(result,sort_keys=True))
    print("DECISION_SUFFICIENCY_MODE_INDEPENDENT_ORACLE_PASS")

if __name__=="__main__":
    main()
