"""Frozen source-reuse qualification, not a discovery or human-cost benchmark."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import time

ORIGINAL = "3e855548afa1c70bcc2aa77f7b86587de5658743"
LATER = "14eb6dbab845d2ac61f171a9ed61906d3f9ffb2f"
ABSENT = "122064d0c853be8d6c2f4cd255c6fcd67acc4ae8"
LATER_BLOB = "d02b18f300bd547dabf83d58ee97d35219516e83"
ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "integrations/mathgraph-check-github/pr-pilot-v1/local-report-check.mjs"
VERIFIER_PATHS = ("integrations/mathgraph-check-github", "experiments/check-retained-report-v1",
                  ".github/workflows/check-retained-report-v1.yml")
REQUIRED_FILES = ("integrations/mathgraph-check-github/pr-pilot-v1/local-report-check.mjs",
                  "integrations/mathgraph-check-github/pr-pilot-v1/local-report-native.py",
                  "experiments/check-retained-report-v1/qualify.py",
                  ".github/workflows/check-retained-report-v1.yml")


def verifier_identity(root=ROOT):
    """A commit label is valid only for committed, unchanged executable inputs."""
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()
    git("ls-files", "--error-unmatch", "--", *REQUIRED_FILES)
    if git("status", "--porcelain", "--untracked-files=all", "--", *VERIFIER_PATHS):
        raise RuntimeError("VERIFIER_INPUTS_NOT_COMMITTED_AND_CLEAN")
    return {"commit": git("rev-parse", "HEAD"), "tree": git("rev-parse", "HEAD^{tree}"),
            "qualifier_sha256": hashlib.sha256((root / REQUIRED_FILES[2]).read_bytes()).hexdigest()}


def require_same_method(runs):
    methods = [run.get("method") for run in runs]
    if not methods or methods[0] is None or any(method != methods[0] for method in methods):
        raise RuntimeError("METHOD_CHANGED_BETWEEN_RUNS")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--lean", required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir()
    verifier = verifier_identity()
    protocol = {"verifier_commit": verifier["commit"], "verifier_tree": verifier["tree"],
                "qualifier_sha256": verifier["qualifier_sha256"], "original": ORIGINAL, "later": LATER,
                "later_blob": LATER_BLOB, "unsupported_main": ABSENT,
                "purpose": "Fixed finite profile reuse, not blind discovery",
                "human_trial": "NOT_RUN", "comparative_advantage": "NOT_RUN"}
    (out / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    outcomes = {}
    started = time.monotonic()
    for name, base, head in (("forward", ORIGINAL, LATER), ("reverse", LATER, ORIGINAL),
                             ("unchanged", LATER, LATER), ("unsupported-main", LATER, ABSENT)):
        cmd = ["node", str(CLI), "--repo", str(Path(args.repo).resolve()), "--base", base,
               "--head", head, "--out", str(out / name), "--lean", args.lean]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        (out / (name + ".log")).write_text(run.stdout + run.stderr)
        result_path = out / name / "result.json"
        result = json.loads(result_path.read_text())
        outcomes[name] = {"exit_code": run.returncode, "status": result["status"],
                          "reason": result.get("reason"), "cost": result["cost"],
                          "subjects": result["subjects"], "method": result.get("method"),
                          "base_observations": len(result.get("base", {}).get("observations", [])),
                          "head_observations": len(result.get("head", {}).get("observations", [])),
                          "base_discrepancies": len(result.get("base", {}).get("mismatches", [])),
                          "head_discrepancies": len(result.get("head", {}).get("mismatches", [])),
                          "result_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest()}
        print(name + ": " + result["status"] + ", head discrepancies=" +
              str(outcomes[name]["head_discrepancies"]), flush=True)
        (out / "summary.json").write_text(json.dumps({"protocol": protocol, "runs": outcomes}, indent=2) + "\n")
    forward, reverse, unchanged, missing = [outcomes[k] for k in ("forward", "reverse", "unchanged", "unsupported-main")]
    assert all(r["status"] in ("OBSERVED_AGREEMENT", "OBSERVED_MISMATCH") and
               r["base_observations"] == 19 and r["head_observations"] == 19
               for r in (forward, reverse, unchanged)), "NATIVE_PROFILE_REUSE_INCOMPLETE"
    assert forward["subjects"]["head"]["git_blob"] == LATER_BLOB, "SELECTED_SOURCE_CHANGED"
    assert forward["base_discrepancies"] == reverse["head_discrepancies"] == 6
    assert forward["head_discrepancies"] == reverse["base_discrepancies"] == unchanged["head_discrepancies"]
    require_same_method((forward, reverse, unchanged, missing))
    assert verifier_identity() == verifier, "VERIFIER_CHANGED_DURING_QUALIFICATION"
    assert missing["exit_code"] == 2 and missing["status"] == "UNKNOWN" and "MODULE_ABSENT" in missing["reason"]
    summary = {"protocol": protocol, "engineering_qualification": "PASSED", "runs": outcomes,
               "wall_seconds": time.monotonic() - started,
               "meaning": "Finite source-reuse observations; inspect each run's actual discrepancies"}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("SOURCE_REUSE_QUALIFIED; human trial and comparative advantage NOT_RUN")


if __name__ == "__main__":
    main()
