#!/usr/bin/env python3
"""Independent evidence validator for V7 source-native physical mutation/restore."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

CASES = (
    "typed_match", "false_mismatch", "typed_mismatch", "wrong_citation",
    "unsupported", "true_unsupported", "no_statement"
)
SOURCE = "nasa-jpl/PropertyKindCalculus@e0deb453e05ffa63297d9704ceb47d0855193824"
SOURCE_BLOB = "9d3359e126fd76298c99e8f9ff5bd3658ebcf5d4"
ORIGINAL = {
    "typed_match": "MATCH", "false_mismatch": "MISMATCH",
    "typed_mismatch": "MISMATCH", "wrong_citation": "MISMATCH",
    "unsupported": "UNKNOWN_UNSUPPORTED",
    "true_unsupported": "UNKNOWN_UNSUPPORTED", "no_statement": "NO_ASSERTION",
}
MUTANT = {**ORIGINAL, "typed_match": "MISMATCH", "typed_mismatch": "MATCH"}
PATTERN = re.compile(r"^V7_TYPE_RESULT lane=(BASE|MUTANT|RESTORED) case=(\w+) status=(\w+) decl=(\S+)$")
EXPECTED_DECL = {
    "wrong_citation": "PropertyKindCalculus.Iso80000.Part3.Edge.height_length"
}
BASE_DECL = "PropertyKindCalculus.Iso80000.Part3.Edge.width_length"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def single(root: Path, basename: str) -> Path:
    paths = [p for p in root.rglob(basename) if p.is_file()]
    assert len(paths) == 1, f"required exactly one archived {basename}, got {len(paths)}"
    return paths[0]


def prepare(archive: Path, target: Path, out: Path):
    src = single(archive, "receipt.json")
    receipt = json.loads(src.read_text())
    assert receipt["upstream"] == SOURCE
    assert receipt["source_native_sysml_to_api_to_kernel"] is True
    assert receipt["source_modified"] is False
    assert receipt["checked_cases"] == ORIGINAL
    assert receipt["original_importer_accepted"] == {k:0 for k in CASES}
    casepath = target / ".lake/build/sysml/typed-v1"
    casepath.mkdir(parents=True, exist_ok=True)
    for case in CASES:
        for ext, key in ((".api.json", "api_json"), (".sysml", "sysml")):
            source = single(archive, case + ext)
            actual = sha(source.read_bytes())
            assert actual == receipt["input_and_output_sha256"][case][key], (case,key)
            shutil.copy2(source, casepath / (case+ext))
    out.mkdir(parents=True, exist_ok=True)
    (out / "v6-original-native-provenance.json").write_text(json.dumps({
        "upstream": SOURCE,
        "v6_exact_source_head": "784b9b59bc3b036e0e9f7a6e97d506979a0da174",
        "v6_original_artifact": 12160348478,
        "v6_original_artifact_sha256": "83e601483fe442a68ec139fb569295dba6256065638049159e724039f4d07740",
        "v6_receipt_sha256": sha(src.read_bytes()),
        "preexisting_native_results": receipt["checked_cases"],
        "copy_claim": "bytes checked against original V6 raw native case hashes",
    }, sort_keys=True, indent=2)+"\n")
    print("V7_V6_RAW_NATIVE_CASES_AUTHENTICATED_AND_COPIED count=7")


def check_lane(lane: str, root: Path, source: Path):
    expected = MUTANT if lane == "MUTANT" else ORIGINAL
    log = (root / (lane + "-typed.log")).read_text()
    observations = {}
    for line in log.splitlines():
        match = PATTERN.fullmatch(line)
        if not match: continue
        ln, case, status, decl = match.groups()
        assert ln == lane and case in CASES and case not in observations
        assert decl == EXPECTED_DECL.get(case, BASE_DECL), (lane,case,decl)
        observations[case] = status
    assert observations == expected, (lane, observations, expected)
    assert f"V7_NATIVE_V6_EXACT_INTERPRETATION_PASS lane={lane} count=7" in log
    assert f"V7_UNAFFECTED_HEIGHT_LENGTH_PROOF lane={lane} verified=true" in log
    import_results = []
    for case in ("typed_match", "typed_mismatch", "wrong_citation"):
        data = (root / f"{lane}-{case}.ingest.log").read_text()
        assert "0 unverified citation(s)" in data
        generated = (root / f"{lane}-{case}.Generated.lean").read_text()
        assert "-- checked:" in generated
        assert "theorem False" not in generated
        assert "example : False" not in generated
        import_results.append(case)
    modified_file = source / "iso80000/PropertyKindCalculus/Iso80000/Part3.lean"
    current_sha = sha(modified_file.read_bytes())
    mode = {
        "lane": lane,
        "source_sha256": current_sha,
        "observed": observations,
        "native_imports_rechecked": import_results,
        "semantic_method":"V6 exact immutable tokenExpr/interpret/declaration/classify",
    }
    if lane == "MUTANT":
        mutant = json.loads((root / "physical-mutant.json").read_text())
        assert mutant["modified_source_sha256"] == current_sha
        assert mutant["original_git_blob"] == SOURCE_BLOB
        assert mutant["dependent_proof_uses_rebound"] == 3
        diff=(root/"physical-source-mutant.diff").read_text()
        assert diff.count("-  | width_length : Edge width.kind length.kind") == 1
        assert diff.count("+  | width_length : Edge width.kind height.kind") == 1
        assert "+  | width_length_original : Edge width.kind length.kind" in diff
        assert diff.count("-  Specializes.of_edge Edge.width_length") >= 1
        mode["source_variant"]="working_tree_mutation_not_upstream_commit"
        mode["modified_source_git_blob"]=mutant["modified_source_git_blob"]
    else:
        assert "  | width_length : Edge width.kind length.kind" in modified_file.read_text()
        mode["source_variant"]="original_pinned_upstream"
    (root/f"{lane}-qualified.json").write_text(json.dumps(mode, sort_keys=True, indent=2)+"\n")
    print("V7_LANE_NATIVE_VERDICT_PASS",lane,json.dumps(observations,sort_keys=True))


def finalize(root: Path):
    base = json.loads((root/"BASE-qualified.json").read_text())
    mutant = json.loads((root/"MUTANT-qualified.json").read_text())
    restored = json.loads((root/"RESTORED-qualified.json").read_text())
    assert base["observed"] == restored["observed"] == ORIGINAL
    assert mutant["observed"] == MUTANT
    assert base["source_sha256"] == restored["source_sha256"]
    assert base["source_sha256"] != mutant["source_sha256"]
    changed={c for c in CASES if base["observed"][c] != mutant["observed"][c]}
    assert changed=={"typed_match","typed_mismatch"}, changed
    assert all(base["observed"][c] == mutant["observed"][c] == restored["observed"][c]
               for c in CASES if c not in changed)
    result={
        "status":"WARRANTED_BOUNDED_PHYSICAL_DECLARATION_TYPE_REVERSAL_AND_REQUALIFICATION",
        "original_source":SOURCE,
        "local_mutant_is_not_upstream_commit":True,
        "source_sha256_by_lane":{x["lane"]:x["source_sha256"] for x in (base,mutant,restored)},
        "verdicts_by_lane":{x["lane"]:x["observed"] for x in (base,mutant,restored)},
        "only_semantic_verdicts_changed":sorted(changed),
        "unaffected_verdicts_requalified_by_actual_native_replay":[c for c in CASES if c not in changed],
        "original_V6_interpreter_copied_unchanged":True,
        "native_importer_still_accepts_all_three_retested_case_names":True,
        "metadata_only_withdrawal_is_not_qualified_as_physical_source_change":True,
        "intended_JPL_statement_contract":"UNKNOWN",
        "claim_limits":[
            "Synthetic one-file controlled mutation is not a candidate scientific PKC model",
            "Original source-level pin only applies to original/restored lanes; mutant is pinned by working-tree diff/blob",
            "Input JSON and source SysML were authenticated from prior V6 source-native converter",
            "This tests one human-authored tiny typed interpretation grammar, not semantic extraction",
            "All old whole-revision dependent warrants invalidate until new native qualification",
        ],
    }
    (root/"v7-final-evidence.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("PKC_V7_PHYSICAL_SOURCE_CHANGE_AND_RESTORATION_QUALIFIED")
    print(json.dumps(result["verdicts_by_lane"],sort_keys=True))

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["prepare","check","finalize"])
    p.add_argument("--v6-archive",type=Path)
    p.add_argument("--target",type=Path)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--lane",choices=["BASE","MUTANT","RESTORED"])
    a=p.parse_args()
    if a.action == "prepare":
        assert a.v6_archive and a.target
        prepare(a.v6_archive,a.target,a.out)
    elif a.action == "check":
        assert a.target and a.lane
        check_lane(a.lane,a.out,a.target)
    else:
        finalize(a.out)
