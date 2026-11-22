#!/usr/bin/env python3
"""Recheck pinned source and historical CI evidence; does not execute Nyx.

Python 3 standard library only. This checks bundled observations against declared
source identities. It does not authenticate a publisher or prove native behavior.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

BEFORE = "09ab47dd4233ad3b80efc64479bf5339739b5570"
AFTER = "7d3253506471a7b9ff58e87fbee50e4a025e0b3f"
CHECKOUT = "78ab554425ee06caa844260f27076f4da8a66d73"
MERGED = "71e31c137bfe2fea641a21455febb84c936fc409"
MERGED_TREE = "6d8f077d27a158c52171ce7a6f8c10aae75a8c60"
WORKFLOW = "20a1c9f1a70669ca02664a1e8c6e87cc1ce32df3"
EXPECTED_BLOBS = {
    "sources/parquet_frame_fidelity.rs": "639a814c4d75365ee9ec0a118f7a8f092cd40e57",
    "sources/traj_after.rs": "e80a17db6babf8691343786fe7aa3353b7446302",
    "sources/traj_before.rs": "2bf034cbf41e83b50974b5aadf291a5dff63af65",
    "sources/sc_traj_before.rs": "4345451f4488cd608fca56ed71869fa8a593b20b",
    "sources/NYX_LICENSE": "f4aa842edff22c02066876c5a06bf1d52d5776f1",
    "sources/check-nyx-parquet-physical-v2.yml": "fca27aa041e49b6ded086bb8c27c848a701b596b",
    "sources/mathgraph_parquet.rs": "3586a9d5b123b630638f18d5a1493c1950d59001",
    "sources/fix_parquet_export.py": "edda77a34ff6d92268a8d86677f377f2790e8403",
    "sources/nonpremium_compat.py": "7e3171078a5d622c13901164bb18b4a0a4ef581e",
}
EXPECTED_TESTS = (
    "filtered_export_uses_the_frame_of_the_selected_rows",
    "mixed_frames_must_be_preserved_or_explicitly_rejected",
    "uniform_frame_round_trip_preserves_frames_and_coordinates",
)

def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)

def json_file(root: Path, name: str):
    return json.loads((root / name).read_text())

def verify(root: Path) -> dict:
    manifest = json_file(root, "source_manifest.json")
    require(len({item["path"] for item in manifest}) == len(manifest),
            "Duplicate manifest paths")
    supplied_blobs = {item["path"]: item["tool_blob_sha"] for item in manifest
                      if item.get("tool_blob_sha")}
    require(supplied_blobs == EXPECTED_BLOBS, "Pinned source identity policy differs")
    source_count = 0
    for item in manifest:
        data = (root / item["path"]).read_bytes()
        require(hashlib.sha256(data).hexdigest() == item["sha256"],
                f"SHA256 mismatch: {item['path']}")
        require(len(data) == item["size_bytes"], f"Size mismatch: {item['path']}")
        if item.get("tool_blob_sha"):
            blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            require(blob == item["tool_blob_sha"], f"Git blob mismatch: {item['path']}")
            source_count += 1
    require(source_count == 9, "Expected nine pinned source/license blobs")

    pr = json_file(root, "records/pr.json")
    require(pr["merged"] is True and pr["number"] == 615, "PR merge status")
    require(pr["base_sha"] == BEFORE and pr["head_sha"] == AFTER, "PR source pins")

    native = json_file(root, "records/native_run.json")
    require(native["id"] == 42925288557 and native["head_sha"] == WORKFLOW,
            "Native workflow identity")
    require(native["status"] == "completed" and native["conclusion"] == "success",
            "Native workflow conclusion")
    require(native["jobs"][0]["id"] == 130210107679 and
            native["jobs"][0]["conclusion"] == "success", "Native job conclusion")
    # Parse actual timestamped JSON output. Echoed script expressions do not count.
    actual = []
    for line in (root / "records/native_job_130210107679_excerpt.log").read_text().splitlines():
        match = re.match(r"L\d+: \d{4}-\d{2}-\d{2}T\S+Z (\{.*\})$", line)
        if match:
            actual.append(json.loads(match.group(1)))
    require(len(actual) == 2, "Expected exactly two executed classification receipts")
    red, green = actual
    require(red == {"run_id": "42925288557", "source_sha": BEFORE,
                    "status": "WARRANTED_BOUNDED_NATIVE_PHYSICAL_AND_FILTERED_FRAME_LOSS"},
            "Historical original-source result")
    require(green["status"] == "WARRANTED_BOUNDED_NATIVE_RED_GREEN" and
            green["green_exit"] == 0 and green["test_count"] == 5 and
            green["source_sha"] == BEFORE and green["red_run_id"] == "42925288557",
            "Historical candidate result")

    head = json_file(root, "records/head_run.json")
    require(head["id"] == 42937928116 and head["head_sha"] == AFTER,
            "Final-head workflow identity")
    require(head["conclusion"] == "failure", "Do not promote run to all-green")
    jobs = {j["name"]: j["conclusion"] for j in head["jobs"]}
    require(jobs["Coverage analysis"] == jobs["Check"] ==
            jobs["Tests (ubuntu-latest, stable)"] == "success", "Selected jobs")
    require(jobs["Lints"] == "failure", "Preserve historical lint failure")
    coverage = (root / "records/coverage_job_130252496810_excerpt.log").read_text()
    require("HEAD is now at 78ab554 Merge " + AFTER + " into " + BEFORE in coverage,
            "Executed coverage checkout identity")
    checkout_identity = json_file(root, "records/checkout_identity.json")
    trees = {c["sha"]: c["tree"] for c in checkout_identity["commits"]}
    require(trees[CHECKOUT] == trees[MERGED] == MERGED_TREE,
            "Executed source tree differs from accepted merged tree")
    require(trees[AFTER] != MERGED_TREE, "Preserve PR-head/merge distinction")
    require("tests/parquet_frame_fidelity.rs" in coverage, "Regression target absent")
    for name in EXPECTED_TESTS:
        require(re.search(r"Z test " + re.escape(name) + r" \.\.\. ok$", coverage,
                          re.MULTILINE) is not None, f"Regression result missing: {name}")
    require("test result: ok. 3 passed; 0 failed" in coverage, "Regression result total")

    # Re-execute the historical patch on the exact old source, without compiling.
    with tempfile.TemporaryDirectory(prefix="nyx-patch-check-") as temporary:
        checkout = Path(temporary)
        target = checkout / "nyx-core/src/md/trajectory/traj.rs"
        target.parent.mkdir(parents=True)
        target.write_bytes((root / "sources/traj_before.rs").read_bytes())
        result = subprocess.run(
            [sys.executable, str(root / "sources/fix_parquet_export.py"), str(checkout)],
            text=True, capture_output=True, timeout=15)
        require(result.returncode == 0, "Historical patch failed: " + result.stderr)
        require(target.read_bytes() == (root / "sources/traj_after.rs").read_bytes(),
                "Historical patch differs from accepted exporter bytes")
    return {
        "status": "PASS_SOURCE_AND_RECORDED_CI_RECHECK",
        "native_execution_this_run": "NOT_RUN",
        "source_git_blobs_verified": source_count,
        "historical_native_repair_tests": 5,
        "historical_accepted_merge_tree_regressions": 3,
        "historical_associated_pr_workflow_ci": "failure",
        "executed_coverage_checkout": CHECKOUT,
        "executed_tree_equals_accepted_merge_tree": True,
        "patch_output_matches_accepted_source": True,
        "source_before": BEFORE,
        "source_after": AFTER,
        "scope": "Pinned source identity, historical recorded outcomes, exact patch identity only",
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    try:
        result = verify(args.root.resolve())
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(json.dumps({"status": "FAIL_EVIDENCE_RECHECK", "error": str(error)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
