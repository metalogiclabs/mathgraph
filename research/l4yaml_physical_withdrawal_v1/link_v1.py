#!/usr/bin/env python3
"""Selective physical-source authority replay using the unchanged MathGraph V1 core.

Native Lean checks and two independently interpreted YAML consumer checks are
source-qualified per lane. Changing the source rev invalidates ALL old claims
until native replay. Targeted dump or reader authority withdrawal only affects
declared dependents. This never promotes a general YAML repair.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

CORE_BLOB="2b50c382407cd3da07c95b4863b74947fb489920"
ORIGIN="nasa-jpl/L4YAML@fdef03caf19e8862792034793da11020b39d6110"
DUMP_NATIVE={"distinct_dump_option_values","round_trip_some_null"}
EXTERNAL={"bool_true_is_bool_in_both","none_is_null_in_both",
          "qNone_is_null_in_both","qStringNull_is_string_in_both"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--core",type=Path,required=True)
    a=ap.parse_args()
    code = a.core.resolve()
    assert subprocess.check_output(["git","hash-object",str(code)],text=True).strip()==CORE_BLOB
    sys.path.insert(0,str(code.parent))
    from protocol import Obligation,assess
    lanes={}
    for name in ("BASE","MUTANT","RESTORED"):
        receipts=json.loads((a.root/f"{name}-receipt.json").read_text())
        assert receipts["lane"]==name and receipts["source"]==ORIGIN
        assert len(receipts["native_checks"])==11
        assert set(receipts["independent_checks"])==EXTERNAL
        assert (a.root/f"{name}-build.log").exists()
        assert "Build completed successfully" in (a.root/f"{name}-build.log").read_text()
        assert receipts["original_oracle_file_git_blob"]=="1e701edbfac8ef6cd6f2b92dac28d6bc6639e7e2"
        assert receipts["original_native_probe_git_blob"]=="81659ba21ccfdf6e1a43879c2318a8010f58ae55"
        key = {
            "source_rev": receipts["source_file_git_blob"],
            "native_lane": receipts["frozen_lean_stdout_sha256"],
            "interpretation": receipts["external_oracle_method_sha256"],
            "dump_authority": receipts["source_file_git_blob"]+":allowReservedPlain",
            "external_readers": "ruamel_yaml_0.18.17_YAML12_and_PyYAML_6.0.3_common_subset",
        }
        items=[]
        values={"native:"+k:v for k,v in receipts["native_checks"].items()}
        values.update({"external:"+k:v for k,v in receipts["independent_checks"].items()})
        for label,value in values.items():
            is_external=label.startswith("external:")
            is_dump=is_external or label.split(":",1)[1] in DUMP_NATIVE
            deps=["source_rev","native_lane","interpretation"]
            if is_dump: deps.append("dump_authority")
            if is_external: deps.append("external_readers")
            items.append(Obligation(name=label,
                source=ORIGIN+"#local-blob:"+receipts["source_file_git_blob"],
                relation="MATCH" if value else "MISMATCH",
                authority="ASSERTED",
                dependencies=tuple(deps),
                qualifier=("Ruamel YAML1.2 and PyYAML shared core interpretation"
                           if is_external else "Unmodified source-native Lean regression predicate")))
        tup=tuple(items)
        verdicts=assess(tup,key,key)
        assert len(verdicts)==15 and all(v in {"SCOPED_AGREEMENT","DIVERGENT_BOUNDED"} for v in verdicts.values())
        lanes[name]={"cases":tup,"required":key,"verdicts":verdicts}
    b,m,r=lanes["BASE"],lanes["MUTANT"],lanes["RESTORED"]
    assert b["verdicts"]==r["verdicts"] and b["verdicts"]!=m["verdicts"]
    changed={k for k in b["verdicts"] if b["verdicts"][k]!=m["verdicts"][k]}
    assert changed=={"external:"+k for k in EXTERNAL},changed
    # A new source revision invalidates every old full-source warrant until
    # it is independently requalified by genuine Lean and reader reexecution.
    old_warrants_at_new_source=assess(b["cases"],m["required"],b["required"])
    assert set(old_warrants_at_new_source.values())=={"UNKNOWN_WITHDRAWN_OR_CHANGED"}
    targeted=dict(b["required"],dump_authority="WITHDRAWN")
    after_targeted=assess(b["cases"],targeted,b["required"])
    expected_target={"external:"+k for k in EXTERNAL} | {"native:"+k for k in DUMP_NATIVE}
    assert {k for k in after_targeted if after_targeted[k]!=b["verdicts"][k]}==expected_target
    assert all(after_targeted[k]=="UNKNOWN_WITHDRAWN_OR_CHANGED" for k in expected_target)
    no_reader=dict(b["required"],external_readers="WITHDRAWN")
    after_reader=assess(b["cases"],no_reader,b["required"])
    assert {k for k in after_reader if after_reader[k]!=b["verdicts"][k]}=={"external:"+k for k in EXTERNAL}
    # Restoration is a real third compiled native lane with exact original
    # blob, rather than copying the old record or setting an optimistic flag.
    assert b["required"]["source_rev"]==r["required"]["source_rev"]
    assert b["required"]["source_rev"]!=m["required"]["source_rev"]
    result={
        "status":"WARRANTED_BOUNDED_CROSS_DOMAIN_PHYSICAL_CHANGE_SENSITIVE_REQUALIFICATION",
        "domain":"L4YAML independent complement to PKC V7",
        "source":ORIGIN,
        "unchanged_v1_core_git_blob":CORE_BLOB,
        "source_revision_by_lane":{l:v["required"]["source_rev"] for l,v in lanes.items()},
        "verdicts_by_lane":{l:v["verdicts"] for l,v in lanes.items()},
        "only_changed_outcomes":sorted(changed),
        "old_source_warrants_under_mutant":old_warrants_at_new_source,
        "targeted_dump_authority_withdrawal":after_targeted,
        "external_reader_authority_withdrawal":after_reader,
        "restoration_requires_actual_compiled_replay":True,
        "no_fixed_green":True,
        "no_autonomous_interpretation_discovery":True,
        "bounds":"Four shared-Core-Schema interpretation cases and 11 unchanged native probes, one synthetic single-line local dump-default toggle."
    }
    (a.root/"v8-v1-warrant-replay.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("L4YAML_V8_UNCHANGED_V1_WARRANT_ENGINE_PHYSICAL_SOURCE_REPLAY_PASS")
    print(json.dumps({l:{k:v for k,v in x["verdicts"].items() if k in changed}
                      for l,x in lanes.items()},sort_keys=True))

if __name__=="__main__":
    main()
