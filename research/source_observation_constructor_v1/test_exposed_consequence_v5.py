#!/usr/bin/env python3
"""Independent finite event-log oracle and adversarial controls for V5."""
import importlib.util
import json
from pathlib import Path
import random
import sys

path=Path(__file__).with_name("exposed_consequence_v5.py")
spec=importlib.util.spec_from_file_location("v5_exposed_consequence",path)
m=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=m
spec.loader.exec_module(m)

def as_log(events,warning=False,count=None):
    parts=[]
    for idx,(case,status) in enumerate(events):
        if warning and idx==0 and status=="ok":
            parts += [
                case+" ... WARNING:test:skipping pygments tests ('pygments' module not found)",
                "WARNING:test:skipping emoji tests ('emoji' module not found)",
                "ok"]
        else:
            parts.append(case+" ... "+status)
    parts += ["", "----------------------------------------------------------------------",
              "Ran %d tests in 0.01s" % (len(events) if count is None else count),
              "", "OK"]
    return ("\n".join(parts)+"\n").encode()

def main():
    e=[("cli/fixture/a","ok"),("markdown2/tm/emphasis","ok")]
    got=m.parse_original(as_log(e,True))
    assert got["status"]=="EXACT_NATIVE_CASE_IDS",got
    assert got["warnings"]==2 and got["cases"]==dict(e)
    changed=[(x,("FAIL" if "emphasis" in x else y)) for x,y in e]
    assert m.parse_original(as_log(changed))["cases"]["markdown2/tm/emphasis"]=="FAIL"
    negatives=[
        as_log(e,True,count=3),
        as_log([e[0],e[0]]),
        as_log(e,True).replace(b"WARNING:test:skipping emoji",b"WARNING:test:skipping something"),
        as_log(e).replace(b"cli/fixture/a ... ok",b"cli/fixture/a ... BROKEN"),
        as_log(e).replace(b"Ran 2 tests",b"Ran 2 tests\nRan 2 tests"),
        as_log(e).replace(b"Ran 2 tests",b"summary missing"),
    ]
    for data in negatives:
        assert m.parse_original(data)["status"]=="UNKNOWN_INCOMPLETE_NATIVE_IDENTITIES"
    rng=random.Random(20261026)
    trials=512
    for i in range(trials):
        n=rng.randrange(1,12)
        expected=[("markdown2/tm/random_%d"%j,rng.choice(["ok","FAIL","ERROR","skipped"])) for j in range(n)]
        data=as_log(expected,warning=(expected[0][1]=="ok" and i%2==1))
        got=m.parse_original(data)
        assert got["status"]=="EXACT_NATIVE_CASE_IDS",(i,got)
        assert got["cases"]==dict(expected),(i,got["cases"])
    print(json.dumps({"status":"PASS_F1_V5_SOURCE_FREE_PREFLIGHT",
                      "independent_oracle_trials":trials,
                      "negative_cases":len(negatives),
                      "original_source_access":"NONE",
                      "protected_sources_access":"NONE"},sort_keys=True))

if __name__=="__main__":main()
