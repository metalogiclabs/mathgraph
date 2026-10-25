#!/usr/bin/env python3
"""Independent V6 native-historical audit; NEVER upgrades source-doctest UNKNOWN.

Inputs are full SHA256 authenticated GitHub Actions ZIPs from original/runner-only
replay. Scientific frozen proposer and evaluator are not modified or rerun.
"""
import argparse,hashlib,json,zipfile,xml.etree.ElementTree as ET
from pathlib import Path

BEFORE="c9e1893accf55e46c35c555132aa72f4db6be2b63acc482b9e877932cf370da8"
AFTER="85cc890df28cebd208ada6b1b6330391da739dc74aba9d5b3573f3125e1aa130"
PROPOSAL_SHA="91f39a06ceed5bc4f74e7a8d396915b1becef490a013c9dcd8df772695890691"
SOURCE="d449488ce6baf5bcc386186cc01c40bf2afdc82c"


def checkzip(p,sha):
    raw=p.read_bytes()
    actual=hashlib.sha256(raw).hexdigest()
    assert actual==sha,(p,actual,sha)
    with zipfile.ZipFile(p) as z:
        return {name:z.read(name) for name in z.namelist()}


def native_summary(xml):
    r=ET.fromstring(xml)
    suites=[r] if r.tag=="testsuite" else list(r.iter("testsuite"))
    return {k:sum(int(s.attrib.get(k,"0")) for s in suites)
            for k in ("tests","failures","errors","skipped")}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first",type=Path,required=True)
    p.add_argument("--cwd-replay",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    first=checkzip(args.first,BEFORE)
    second=checkzip(args.cwd_replay,AFTER)
    for archive in (first,second):
        assert hashlib.sha256(archive["proposals.json"]).hexdigest()==PROPOSAL_SHA
        assert archive["pre-native-proposal-sha256.txt"].decode().splitlines()[0].split()[0]==PROPOSAL_SHA
        proposal=json.loads(archive["proposals.json"])
        metadata=json.loads(archive["metadata.json"])
        lock=json.loads(archive["selection-lock.json"])
        assert proposal["status"]=="UNKNOWN_NO_SAFE_LITERAL_SOURCE_EXAMPLE"
        assert proposal["obligations"]==[]
        assert proposal["api"]["status"]=="STATIC_EXPORT_CLOSURE_BOUNDED"
        assert metadata["source_sha"]==SOURCE
        assert metadata["repository"]=="lepture/mistune"
        assert lock["selected"]["sha"]==SOURCE
        assert lock["frozen_method_commit"]=="dfcc088ca6f4a280272c361e043dd0f49afa1b5b"
        assert lock["pinned_export_resolver"]=="7f38aa7029c8d89006db956941767033b09717ca"
    assert first["proposals.json"]==second["proposals.json"]
    assert first["frozen-method-sha256.txt"]==second["frozen-method-sha256.txt"]
    assert first["export-resolver-sha256.txt"]==second["export-resolver-sha256.txt"]
    assert first["native-exit-code.txt"].strip()==b"1"
    assert second["native-exit-code.txt"].strip()==b"0"
    native=native_summary(second["native-junit.xml"])
    assert native=={"tests":1183,"failures":0,"errors":0,"skipped":0},native
    assert "1183 passed" in second["native-test.log"].decode(errors="replace")
    previous=first["native-test.log"].decode(errors="replace")
    assert "TestMiscCases.test_project_script_entrypoint" in previous
    assert "mistune.__main__:cli" in previous and 'name = "mathgraph"' in previous
    assert second["prospective-result.json"] if "prospective-result.json" in second else True
    # The corrected run's native suite is GREEN; frozen evaluate.py threw KeyError
    # because frozen propose.py did not supply a separate repository/source_sha
    # envelope. That instrumentation mismatch cannot promote zero proposals.
    receipt={
      "program":"V6_SOURCE_DOC_EXAMPLE_PROSPECTIVE_FIRST_ELIGIBLE",
      "status":"UNKNOWN_NO_SAFE_LITERAL_SOURCE_EXAMPLE",
      "science_verdict":"INAPPLICABLE_ZERO_PRESEALED_OBLIGATIONS",
      "native_verdict":"WARRANTED_BOUNDED_ORIGINAL_NATIVE_SUITE",
      "source":"lepture/mistune@"+SOURCE,
      "frozen_method_commit":"dfcc088ca6f4a280272c361e043dd0f49afa1b5b",
      "selection_commit":"491dafaacdc52efe609026eaa8d1e6612da94d4b",
      "initial_artifact_sha256":BEFORE,
      "replayed_artifact_sha256":AFTER,
      "unchanged_proposal_sha256":PROPOSAL_SHA,
      "native_original":native,
      "original_apparatus_failure":"wrong cwd: relative pyproject.toml read MathGraph root",
      "replay_evaluator_failure":"frozen proposal/evaluator schema mismatch: metadata repository missing; NOT semantic failure",
      "independent_baseline":"NOT_EXECUTED_ZERO_PRESEALED_EXAMPLES",
      "relative_comparison":"INCONCLUSIVE_NOT_TIE",
      "native_source_changed":False,
      "source_exposed_now":True,
      "reusable_capability":"UNKNOWN_UNTIL_PROSPECTIVE_NONEMPTY_RESULT",
      "bounds":"two authenticated archival receipts; second original pytest GREEN, no actual semantic correspondence obligation",
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("V6_FIRST_PROSPECT_NATIVE_GREEN_ZERO_OBLIGATION_SCIENTIFIC_UNKNOWN",
          json.dumps({"native":native,"proposals":0,"relative_comparison":"INCONCLUSIVE_NOT_TIE"},sort_keys=True))


if __name__=="__main__":
    main()
