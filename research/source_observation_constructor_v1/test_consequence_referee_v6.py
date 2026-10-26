#!/usr/bin/env python3
"""Source-free F1 V6 malicious-receipt regression + independent exact oracles."""
import argparse,hashlib,importlib.util,io,json,random,zipfile
from pathlib import Path

def load():
    spec=importlib.util.spec_from_file_location("referee_v6",Path(__file__).with_name("consequence_referee_v6.py"))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

def repack(raw,mutate):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        files={name:z.read(name) for name in z.namelist()}
    mutate(files)
    lines=[hashlib.sha256(files[name]).hexdigest()+"  evidence/f1-v5-real/"+name
           for name in sorted(files) if name!="SHA256SUMS"]
    files["SHA256SUMS"]=("\n".join(lines)+"\n").encode()
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(files.items()):z.writestr(name,data)
    return out.getvalue()

def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--archive",type=Path,required=True)
    arg.add_argument("--out",type=Path,required=True)
    a=arg.parse_args()
    m=load()
    raw=a.archive.read_bytes()
    d=m.verify(raw)
    assert (d["native_unique_cases"],d["native_failed_cases"])==(276,56)
    assert d["conventional"]=="TIE_ON_CLEAN_VS_FAULT_DECISION"
    assert d["selective_document_withdrawal"] and d["alternative_independent_support_survives"]

    def expect(blob,code):
        try:m.verify(blob,expected_sha=None)
        except m.Refusal as e:assert str(e)==code,(str(e),code)
        else:raise AssertionError("improperly admitted "+code)
    bad=bytearray(raw);bad[len(bad)//2]^=1
    try:m.verify(bytes(bad))
    except m.Refusal as e:assert str(e)=="ARCHIVE_DIGEST_MISMATCH"
    else:raise AssertionError("invalid outer digest accepted")
    checks={"outer_archive":"PASS"}
    def change_json(f,**kw):
        d=json.loads(f["result.json"]);d.update(kw);f["result.json"]=json.dumps(d).encode()
    expect(repack(raw,lambda f:change_json(f,target_original_case="wrong/target")),"PROTECTED_TARGET_MISMATCH")
    checks["forged_target"]="PASS"
    expect(repack(raw,lambda f:change_json(f,pinned_source="0"*40)),"SOURCE_IDENTITY_MISMATCH")
    checks["forged_source"]="PASS"
    expect(repack(raw,lambda f:f.__setitem__("candidate.log",f["candidate.log"]+b"\nBAD\n")),"RUNNER_LOG_BINDING_MISMATCH")
    checks["raw_tamper"]="PASS"
    def forge_informed(f):
        f["informed.log"]=f["informed.log"].replace(b"markdown2/tm/emphasis ... FAIL",b"markdown2/tm/emphasis ... ok")
        d=json.loads(f["result.json"])
        d["same_information_rulebook"]["log_sha256"]=m.sha(f["informed.log"])
        f["result.json"]=json.dumps(d).encode()
    expect(repack(raw,forge_informed),"INFORMED_COMPARATOR_DISAGREES")
    checks["false_comparator"]="PASS"
    def forge_protected(f):
        f["candidate.log"]=f["candidate.log"].replace(b"markdown2/tm/emphasis ... FAIL",b"markdown2/tm/emphasis ... ok")
        d=json.loads(f["result.json"]);d["candidate"]["log_sha256"]=m.sha(f["candidate.log"])
        f["result.json"]=json.dumps(d).encode()
    expect(repack(raw,forge_protected),"PROTECTED_CONSEQUENCE_ABSENT")
    checks["forged_consequence"]="PASS"
    def forge_generic(f):
        f["generic.log"]=f["generic_original.log"]
        d=json.loads(f["result.json"]);d["fixed_generic"]["log_sha256"]=m.sha(f["generic.log"])
        f["result.json"]=json.dumps(d).encode()
    expect(repack(raw,forge_generic),"ORDINARY_COMPARATOR_NOT_SEPARATING")
    checks["false_conventional"]="PASS"
    expect(repack(raw,lambda f:f.__setitem__("rogue.txt",b"x")),"ZIP_MEMBER_SCOPE_MISMATCH")
    checks["extra_member"]="PASS"
    def inflate(f):change_json(f,status="SUPERIOR_TO_ALL_AGENTS")
    assert m.verify(repack(raw,inflate),expected_sha=None)["conventional"]=="TIE_ON_CLEAN_VS_FAULT_DECISION"
    checks["self_proclaimed_superiority_ignored"]="PASS"
    rng=random.Random(20261026)
    for i in range(1024):
        tokens=list(map(str,range(rng.randrange(1,8))))
        supports=[[t for t in tokens if rng.randrange(2)] for _ in range(8)]
        live={t for t in tokens if rng.randrange(2)}
        admitted=[frozenset(s) for s in supports if set(s)<=live]
        exact=[sorted(x) for x in set(admitted) if not any(y<x for y in admitted)]
        exact.sort(key=lambda z:(len(z),z))
        assert m.minimal_supports(supports,live)==exact
    for i in range(512):
        rows=[("markdown2/tm/s"+str(j),rng.choice(("ok","FAIL","ERROR","skipped")))
              for j in range(rng.randrange(1,25))]
        log=("\n".join(x+" ... "+y for x,y in rows)
             +"\nRan "+str(len(rows))+" tests in 0.1s\nOK\n").encode()
        assert m.native_cases(log)==dict(rows)
    result={"status":"PASS_F1_V6_EXPOSED_REFEREE",
            "source":"EXPOSED_ONLY","protected_heldout_read":False,
            "oracle_support_trials":1024,"oracle_native_log_trials":512,
            "negative_controls":checks,"testcase_count":276,"fault_failures":56,
            "qualified_advantage":"TIE_NOT_SUPERIORITY",
            "operator_kind_invention":"UNKNOWN"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"controls":len(checks),
                      "support_oracle":1024,"log_oracle":512},sort_keys=True))

if __name__=="__main__":main()
