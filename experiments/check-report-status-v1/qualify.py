"""Known-case status reuse with an actual local candidate and withdrawal.

This creates Git objects only; it does not change a subject branch or checkout.
The experiment establishes neither novel discovery nor an external human trial.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
CLI_PATH = "integrations/mathgraph-check-github/pr-pilot-v1/local-report-check.mjs"
QUALIFIER_PATH = "experiments/check-report-status-v1/qualify.py"
STATUS_REFERENCE_PATH = "integrations/mathgraph-check-github/pr-pilot-v1/report-status-reference.py"
VERIFIER_PATHS = ("integrations/mathgraph-check-github", "experiments/check-report-status-v1",
                  "experiments/check-retained-report-v1", ".github/workflows/check-retained-report-v1.yml")
REQUIRED_FILES = (CLI_PATH,
                  "integrations/mathgraph-check-github/pr-pilot-v1/local-report-native.py",
                  "integrations/mathgraph-check-github/pr-pilot-v1/report-status.mjs",
                  "integrations/mathgraph-check-github/pr-pilot-v1/report-status-cases.json",
                  STATUS_REFERENCE_PATH, QUALIFIER_PATH,
                  ".github/workflows/check-retained-report-v1.yml")

SOURCE_PATH = "Tests/SuiteRunner/Reports.lean"
ORIGINAL = "14eb6dbab845d2ac61f171a9ed61906d3f9ffb2f"
ORIGINAL_BLOB = "d02b18f300bd547dabf83d58ee97d35219516e83"
ORIGINAL_SOURCE_SHA = "8e9bc2716fbfde4fbedf4f9a82fd1a0607878898c99c4700f55765a384393542"
CANDIDATE_SOURCE_SHA = "d9e149f37f0b864f2a4d0b907280cbda362d59fe05b424157464eaabfed564c2"
ABSENT = "122064d0c853be8d6c2f4cd255c6fcd67acc4ae8"
ORIGINAL_CONDITION = 'else if name == "failure" && isStart && cur.isSome then failed := true'
CANDIDATE_CONDITION = 'else if (name == "failure" || name == "error") && isStart && cur.isSome then failed := true'
STATUS_PROFILE = "junit-status-preservation-v1"
ENVELOPE_PROFILE = "junit-report-integrity-v1"
ENVELOPE_CORPUS_SHA = "751b26c525fb7024044e5cccbdcf794531634b930dbb69c87711cc0d400a53d0"
STATUS_CASE_IDS = ("plain_pass", "assertion_failure", "skipped_case", "error_empty",
                   "error_text", "error_then_pass", "mixed_outcomes", "error_text_control")
MISMATCH_IDS = ("error_empty", "error_text", "error_then_pass", "mixed_outcomes")
ENVELOPE_CASE_IDS = ("prefix", "suffix", "duplicate", "attribute_entity", "content_entity",
                     "closing_content", "empty", "one", "failure", "skip", "comment_cdata",
                     "entities", "truncated", "mismatch", "two_roots", "unquoted",
                     "open_comment", "open_tag", "no_root")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def git(repo, *args, data=None, env=None, binary=False, optional=False):
    result = subprocess.run(["git", "-C", str(repo), *args], input=data,
                            capture_output=True, timeout=30, env=env)
    if result.returncode:
        if optional:
            return None
        raise RuntimeError("GIT_COMMAND_FAILED: " + " ".join(args) + ": " +
                           result.stderr.decode(errors="replace")[-1200:])
    return result.stdout if binary else result.stdout.decode().strip()


def verifier_identity(root=ROOT):
    """A commit label covers only committed, unchanged executable inputs."""
    git(root, "ls-files", "--error-unmatch", "--", *REQUIRED_FILES)
    require(not git(root, "status", "--porcelain", "--untracked-files=all", "--", *VERIFIER_PATHS),
            "VERIFIER_INPUTS_NOT_COMMITTED_AND_CLEAN")
    return {"commit": git(root, "rev-parse", "HEAD"), "tree": git(root, "rev-parse", "HEAD^{tree}"),
            "qualifier_sha256": digest((root / QUALIFIER_PATH).read_bytes()),
            "required_files": {name: digest((root / name).read_bytes()) for name in REQUIRED_FILES}}


def repository_state(repo):
    """Track the caller's HEAD, refs and index, including an unborn checkout."""
    index = Path(git(repo, "rev-parse", "--git-path", "index"))
    if not index.is_absolute():
        index = Path(repo) / index
    return {"head": git(repo, "rev-parse", "--verify", "HEAD", optional=True),
            "symbolic_head": git(repo, "symbolic-ref", "--quiet", "HEAD", optional=True),
            "refs": git(repo, "for-each-ref", "--format=%(refname) %(objectname)"),
            "index_sha256": digest(index.read_bytes()) if index.exists() else None}


def prepare_candidate(repo, out):
    """Patch the pinned blob via a private index and return a real child commit."""
    before = repository_state(repo)
    require(git(repo, "rev-parse", "--verify", ORIGINAL + "^{commit}") == ORIGINAL,
            "ORIGINAL_COMMIT_MISMATCH")
    blob = git(repo, "rev-parse", "--verify", ORIGINAL + ":" + SOURCE_PATH)
    source = git(repo, "cat-file", "blob", blob, binary=True)
    require(blob == ORIGINAL_BLOB and digest(source) == ORIGINAL_SOURCE_SHA,
            "ORIGINAL_SOURCE_MISMATCH")
    old, new = ORIGINAL_CONDITION.encode(), CANDIDATE_CONDITION.encode()
    require(source.count(old) == 1, "REPAIR_CONDITION_NOT_UNIQUE")
    candidate = source.replace(old, new, 1)
    require(digest(candidate) == CANDIDATE_SOURCE_SHA, "CANDIDATE_SOURCE_MISMATCH")
    entry = git(repo, "ls-tree", ORIGINAL, "--", SOURCE_PATH)
    mode = entry.split()[0]
    require(mode == "100644", "UNSUPPORTED_SOURCE_FILE_MODE")
    candidate_blob = git(repo, "hash-object", "-w", "--stdin", data=candidate)
    with tempfile.TemporaryDirectory(prefix="mathgraph-status-index-") as temp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(temp) / "index"),
               "GIT_AUTHOR_NAME": "MathGraph Synthetic Qualification",
               "GIT_AUTHOR_EMAIL": "qualification@example.invalid",
               "GIT_COMMITTER_NAME": "MathGraph Synthetic Qualification",
               "GIT_COMMITTER_EMAIL": "qualification@example.invalid",
               "GIT_AUTHOR_DATE": "2026-11-22T00:00:00+0000",
               "GIT_COMMITTER_DATE": "2026-11-22T00:00:00+0000"}
        git(repo, "read-tree", ORIGINAL, env=env)
        git(repo, "update-index", "--cacheinfo", mode, candidate_blob, SOURCE_PATH, env=env)
        tree = git(repo, "write-tree", env=env)
        message = ("Synthetic local qualification candidate: preserve JUnit error outcome\n\n"
                   "Known-case experiment only. No upstream submission, publisher identity, "
                   "human approval, or production authorization is asserted.\n")
        commit = git(repo, "-c", "commit.gpgsign=false", "commit-tree", tree, "-p", ORIGINAL,
                     data=message.encode(), env=env)
    require(git(repo, "rev-list", "--parents", "-n", "1", commit) == commit + " " + ORIGINAL,
            "CANDIDATE_PARENT_MISMATCH")
    require(git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", ORIGINAL, commit) == SOURCE_PATH,
            "CANDIDATE_CHANGED_UNDECLARED_PATH")
    require(git(repo, "cat-file", "blob", commit + ":" + SOURCE_PATH, binary=True) == candidate,
            "CANDIDATE_COMMIT_BYTES_MISMATCH")
    require(repository_state(repo) == before, "SUBJECT_CHECKOUT_OR_REFS_CHANGED")
    patch = git(repo, "diff", "--no-ext-diff", "--no-textconv", ORIGINAL, commit, "--", SOURCE_PATH,
                binary=True)
    commit_bytes = git(repo, "cat-file", "commit", commit, binary=True)
    (out / "original.lean").write_bytes(source)
    (out / "candidate.lean").write_bytes(candidate)
    (out / "candidate.patch").write_bytes(patch)
    (out / "candidate-commit.txt").write_bytes(commit_bytes)
    metadata = {"commit": commit, "parent": ORIGINAL, "tree": tree, "git_blob": candidate_blob,
                "source_sha256": CANDIDATE_SOURCE_SHA, "path": SOURCE_PATH,
                "provenance": "ACTUAL_LOCAL_SYNTHETIC_GIT_COMMIT", "remote_publication": "NOT_PERFORMED",
                "author": "MathGraph Synthetic Qualification <qualification@example.invalid>",
                "author_and_committer_date": "2026-11-22T00:00:00+0000",
                "patch_sha256": digest(patch), "commit_object_sha256": digest(commit_bytes),
                "changed_paths": [SOURCE_PATH], "caller_checkout_unchanged": True}
    write_json(out / "candidate.json", metadata)
    return metadata


def require_same_method(runs):
    methods = [run.get("method") for run in runs]
    require(bool(methods) and methods[0] is not None and all(method == methods[0] for method in methods),
            "METHOD_CHANGED_BETWEEN_RUNS")


def validate_source(subject, revision, candidate):
    is_candidate = revision == candidate["commit"]
    require(subject.get("revision") == revision and subject.get("path") == SOURCE_PATH and
            subject.get("source_sha256") == (CANDIDATE_SOURCE_SHA if is_candidate else ORIGINAL_SOURCE_SHA) and
            subject.get("git_blob") == (candidate["git_blob"] if is_candidate else ORIGINAL_BLOB) and
            subject.get("provenance") == "LOCALLY_OBSERVED_GIT_OBJECT" and
            subject.get("repository", "").startswith("local-git:"), "RUN_SOURCE_BINDING_MISMATCH")


def validate_run(result, exit_code, base, head, profile, candidate, expected_mismatches):
    require(result.get("method", {}).get("id") == profile, "WRONG_CHECK_PROFILE")
    require(result.get("human_trial") == "NOT_RUN" and result.get("comparative_advantage") == "NOT_RUN" and
            result.get("permission") == "ADVISORY_ONLY" and result.get("cost", {}).get("model_calls") == 0,
            "UNQUALIFIED_HUMAN_OR_MODEL_CLAIM")
    validate_source(result.get("subjects", {}).get("base", {}), base, candidate)
    if head == ABSENT:
        reason = result.get("reason", "")
        require(exit_code == 2 and result.get("status") == "UNKNOWN" and
                "MODULE_ABSENT" in reason and ABSENT in reason, "ABSENT_MODULE_NOT_UNKNOWN")
        return
    validate_source(result.get("subjects", {}).get("head", {}), head, candidate)
    case_ids = STATUS_CASE_IDS if profile == STATUS_PROFILE else ENVELOPE_CASE_IDS
    for side, wanted in zip(("base", "head"), expected_mismatches):
        arm = result.get(side, {})
        rows, mismatches = arm.get("observations", []), arm.get("mismatches", [])
        require(arm.get("complete") is True and len(rows) == len(case_ids) and
                sorted(row.get("id", "") for row in rows) == sorted(case_ids), "NATIVE_CASE_COVERAGE_INCOMPLETE")
        require(all(type(row.get("passed")) is bool for row in rows) and
                mismatches == [row for row in rows if not row["passed"]] and
                sorted(row["id"] for row in mismatches) == sorted(wanted), "UNEXPECTED_NATIVE_DISCREPANCIES")
    expected_status = "OBSERVED_MISMATCH" if expected_mismatches[1] else "OBSERVED_AGREEMENT"
    require(result.get("status") == expected_status and exit_code == (1 if expected_mismatches[1] else 0),
            "NATIVE_OUTCOME_OR_EXIT_MISMATCH")
    require(result.get("cost", {}).get("native_processes", 0) > 0, "FRESH_NATIVE_EXECUTION_NOT_RECORDED")
    if profile == ENVELOPE_PROFILE:
        require(result["method"].get("corpus_sha256") == ENVELOPE_CORPUS_SHA, "FROZEN_ENVELOPE_CORPUS_CHANGED")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--lean", required=True)
    args = parser.parse_args(argv)
    out = Path(args.out).resolve()
    out.mkdir()
    repo = Path(args.repo).resolve()
    started = time.monotonic()
    protocol = {"original": ORIGINAL, "original_blob": ORIGINAL_BLOB,
                "original_source_sha256": ORIGINAL_SOURCE_SHA, "candidate_source_sha256": CANDIDATE_SOURCE_SHA,
                "unsupported_main": ABSENT, "status_profile": STATUS_PROFILE,
                "status_case_ids": STATUS_CASE_IDS, "original_mismatch_ids": MISMATCH_IDS,
                "legacy_profile": ENVELOPE_PROFILE, "legacy_corpus_sha256": ENVELOPE_CORPUS_SHA,
                "purpose": "Known-case outcome preservation, fresh repair and withdrawal; not blind discovery",
                "human_trial": "NOT_RUN", "comparative_advantage": "NOT_RUN"}
    summary = {"protocol": protocol, "engineering_qualification": "INCOMPLETE", "runs": {}}

    def persist():
        summary["wall_seconds"] = time.monotonic() - started
        write_json(out / "protocol.json", protocol)
        write_json(out / "summary.json", summary)

    persist()
    try:
        verifier = verifier_identity()
        protocol.update(verifier_commit=verifier["commit"], verifier_tree=verifier["tree"],
                        qualifier_sha256=verifier["qualifier_sha256"], verifier_inputs=verifier["required_files"])
        persist()
        candidate = prepare_candidate(repo, out)
        protocol["candidate"] = candidate
        require(git(repo, "rev-parse", "--verify", ABSENT + "^{commit}") == ABSENT and
                not git(repo, "ls-tree", ABSENT, "--", SOURCE_PATH), "ABSENT_SOURCE_CONTROL_CHANGED")
        persist()
        fixed = candidate["commit"]
        cases = (("original", ORIGINAL, ORIGINAL, STATUS_PROFILE, (MISMATCH_IDS, MISMATCH_IDS)),
                 ("repair", ORIGINAL, fixed, STATUS_PROFILE, (MISMATCH_IDS, ())),
                 ("withdrawal", fixed, ORIGINAL, STATUS_PROFILE, ((), MISMATCH_IDS)),
                 ("unchanged-candidate", fixed, fixed, STATUS_PROFILE, ((), ())),
                 ("legacy-envelope", ORIGINAL, fixed, ENVELOPE_PROFILE, ((), ())),
                 ("unsupported-main", fixed, ABSENT, STATUS_PROFILE, None))
        results, validation_errors = {}, []
        for name, base, head, profile, expected in cases:
            cmd = ["node", str(ROOT / CLI_PATH), "--repo", str(repo), "--base", base,
                   "--head", head, "--out", str(out / name), "--lean", args.lean]
            if profile == STATUS_PROFILE:
                cmd += ["--profile", profile]
            recorded = {"base_revision": base, "head_revision": head, "requested_profile": profile,
                        "command": cmd, "status": "UNKNOWN", "exit_code": None}
            summary["runs"][name] = recorded
            persist()
            try:
                run = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
                (out / (name + ".log")).write_text(run.stdout + run.stderr)
                recorded["exit_code"] = run.returncode
                result_path = out / name / "result.json"
                result = json.loads(result_path.read_text())
                results[name] = result
                recorded.update(status=result.get("status"), reason=result.get("reason"), cost=result.get("cost"),
                                subjects=result.get("subjects"), method=result.get("method"),
                                result_sha256=digest(result_path.read_bytes()))
                for side in ("base", "head"):
                    recorded[side + "_observations"] = len(result.get(side, {}).get("observations", []))
                    recorded[side + "_mismatch_ids"] = [row["id"] for row in result.get(side, {}).get("mismatches", [])]
                validate_run(result, run.returncode, base, head, profile, candidate, expected)
                recorded["qualification_control"] = "PASSED"
            except Exception as error:
                if isinstance(error, subprocess.TimeoutExpired):
                    raw = b"".join(part.encode() if isinstance(part, str) else (part or b"")
                                   for part in (error.stdout, error.stderr))
                    (out / (name + ".log")).write_bytes(raw)
                recorded["qualification_control"] = "FAILED"
                recorded["qualification_failure"] = type(error).__name__ + ": " + str(error)
                validation_errors.append(name + ": " + recorded["qualification_failure"])
            print(name + ": " + str(recorded["status"]) + "; exit=" + str(recorded["exit_code"]) +
                  "; base/head discrepancies=" + str(len(recorded.get("base_mismatch_ids", []))) + "/" +
                  str(len(recorded.get("head_mismatch_ids", []))) +
                  ("; " + recorded["qualification_failure"] if recorded.get("qualification_failure") else ""), flush=True)
            persist()
        require(not validation_errors, "QUALIFICATION_CONTROLS_FAILED: " + "; ".join(validation_errors))
        require_same_method([results[name] for name, _, _, profile, _ in cases if profile == STATUS_PROFILE])
        require(verifier_identity() == verifier, "VERIFIER_CHANGED_DURING_QUALIFICATION")
        summary["engineering_qualification"] = "PASSED"
        summary["meaning"] = "Eight-case status profile detects the known error-to-PASS discrepancy; local repair and withdrawal qualify; old 19-case envelope profile is unchanged."
        persist()
        print("STATUS_REUSE_QUALIFIED; candidate is local and synthetic; human trial and comparative advantage NOT_RUN")
        return 0
    except (Exception, KeyboardInterrupt) as error:
        summary["engineering_qualification"] = "FAILED"
        summary["failure"] = type(error).__name__ + ": " + str(error)
        persist()
        print("STATUS_REUSE_NOT_QUALIFIED: " + summary["failure"], flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
