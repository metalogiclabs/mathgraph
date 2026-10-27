#!/usr/bin/env python3
"""Adversarial tests on *authentic*, freshly generated V4/V5 receipts.

The fixtures here are NOT fabricated scientific evidence. We copy a completed
source-native run, withdraw or corrupt one fact, and require the independent
verifier to refuse to preserve its earlier warrant.
"""
from __future__ import annotations
import argparse
import json
import pathlib
import shutil
import tempfile

from independent_checker import PIN, Corrupt, assess

def require(p: bool, why: str) -> None:
    if not p:
        raise AssertionError(why)

def test(v4: pathlib.Path, v5: pathlib.Path, out: pathlib.Path) -> None:
    base = assess(v4, v5, PIN)
    require(base.get("authority") == "WARRANTED_BOUNDED_SELECTED_CITATION",
            "AUTHENTIC_REPLAY_NOT_WARRANTED")
    require([x["verdict"] for x in base["primary_controls"]] == [
        "WARRANTED_CITATION_ONLY", "REJECTED_UNCHECKED_STATEMENT",
        "REJECTED_INVALID_EVIDENCE", "REJECTED_UNCHECKED_STATEMENT",
        "WITHDRAWN", "WITHDRAWN"], "UNEXPECTED_PRIMARY_CONTROL_VECTOR")
    trials = []

    stale = assess(v4, v5, "ffffffffffffffffffffffffffffffffffffffff")
    require(stale["authorization"] == "WITHDRAWN" and
            stale["reason"] == "STALE_SOURCE_REVISION", "STALE_REVISION_ADMITTED")
    trials.append({"name":"different_source_revision","verdict":"WITHDRAWN","reason":stale["reason"]})

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        dst = root / "v5"
        shutil.copytree(v5, dst)
        (dst / "false_statement.sysml").unlink()
        missing = assess(v4, dst, PIN)
        require(missing["authorization"] == "WITHDRAWN", "WITHDRAWAL_ADMITTED")
        trials.append({"name":"withdraw_authentic_sysml","verdict":"WITHDRAWN",
                       "reason":missing["reason"]})

        shutil.copytree(v5, root / "altered", dirs_exist_ok=False)
        alter = root / "altered" / "convert-false_statement-api.json"
        text = alter.read_text()
        require("False" in text, "NO_AUTHENTIC_CLAIM_IN_CONVERTER_OUTPUT")
        alter.write_text(text.replace("False", "NotFalse", 1))
        try:
            assess(v4, root / "altered", PIN)
        except Corrupt as ex:
            trials.append({"name":"tamper_external_converter_claim",
                           "verdict":"REJECTED_EVIDENCE", "reason":str(ex)})
        else:
            raise AssertionError("FORGED_CONVERTER_OUTPUT_ACCEPTED")

        shutil.copytree(v5, root / "no_comment", dirs_exist_ok=False)
        gen = root / "no_comment" / "OriginalFalseGenerated.lean"
        text = gen.read_text()
        require("-- checked:" in text, "ORIGINAL_GENERATED_LEAN_UNEXPECTED")
        gen.write_text(text.replace("-- checked:", "-- suppressed:", 1))
        try:
            assess(v4, root / "no_comment", PIN)
        except Corrupt as ex:
            trials.append({"name":"tamper_generated_lean_statement_boundary",
                           "verdict":"REJECTED_EVIDENCE", "reason":str(ex)})
        else:
            raise AssertionError("MISSING_COMMENT_PROVENANCE_ACCEPTED")

        shutil.copytree(v5, root / "counterfeit", dirs_exist_ok=False)
        tsv = root / "counterfeit" / "native-results.tsv"
        x = tsv.read_text()
        require("strict\tfalse_statement\t" in x, "STRICT_CASE_NOT_IN_TSV")
        rows = []
        for line in x.splitlines():
            if line.startswith("strict\tfalse_statement\t"):
                cols = line.split("\t")
                cols[2] = "0"
                line = "\t".join(cols)
            rows.append(line)
        tsv.write_text("\n".join(rows)+"\n")
        try:
            assess(v4, root / "counterfeit", PIN)
        except Corrupt as ex:
            trials.append({"name":"forge_strict_native_success",
                           "verdict":"REJECTED_EVIDENCE", "reason":str(ex)})
        else:
            raise AssertionError("FALSE_NATIVE_CLAIM_ACCEPTED")

    require(len(trials) == 5, "NEGATIVE_CONTROL_COUNT")
    report = {
        "protocol":"MATHGRAPH_CLAIM_ASSURANCE_V1_NEGATIVE_REPLAY",
        "authentic_reference_source":f"nasa-jpl/PropertyKindCalculus@{PIN}",
        "baseline_controls":len(base["primary_controls"]),
        "adversarial_withdrawal_and_forgery":trials,
        "status":"PASS_ALL_5_WITHDRAWAL_AND_FORGERY_CONTROLS",
        "no_upstream_writes":True,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("MATHGRAPH_CLAIM_ASSURANCE_V1_NEGATIVES_PASS", len(trials))

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--v4",type=pathlib.Path,required=True)
    p.add_argument("--v5",type=pathlib.Path,required=True)
    p.add_argument("--output",type=pathlib.Path,required=True)
    a=p.parse_args()
    test(a.v4,a.v5,a.output)
