"""Run the pinned Flash fixture in trusted CI, then admit its bounded receipt.

This executable harness is an experiment, not a Nucleus, production Check, or
human-intent verifier. Native subprocess execution is the only way it creates
the acceptance observation; JSON read from disk cannot enter the trusted path.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time

import bridge


HERE = Path(__file__).resolve().parent
RESEARCH_REFS = frozenset({
    "refs/heads/research/check-kernel-warrant-bridge-20261104",
    "refs/heads/research/check-kernel-persisted-reuse-20261104",
})


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_head(directory: Path) -> str:
    proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=directory,
                          capture_output=True, check=True, text=True, timeout=20)
    return proc.stdout.strip()


def validate_checkout(flash: Path, policy: dict) -> dict:
    """Before execution, verify the actual checkout, bytes, and target record."""
    if git_head(flash) != policy["checker"]["commit"]:
        raise ValueError("CHECKER_REVISION_MISMATCH")
    source = policy["source"]
    export_path, config_path = flash / source["export_path"], flash / source["config_path"]
    exported = export_path.read_bytes()
    configured = config_path.read_bytes()
    if digest(exported) != source["export_sha256"]:
        raise ValueError("EXPORT_SHA256_MISMATCH")
    if digest(configured) != source["config_sha256"]:
        raise ValueError("CONFIG_SHA256_MISMATCH")
    config = json.loads(configured)
    if (config != {"export_file_path": source["export_path"],
                   "permitted_axioms": source["permitted_axioms"],
                   "unpermitted_axiom_hard_error": source["unpermitted_axiom_hard_error"]}):
        raise ValueError("AXIOM_POLICY_MISMATCH")
    lines = [json.loads(line) for line in exported.splitlines() if line.strip()]
    if not lines or "meta" not in lines[0]:
        raise ValueError("EXPORTER_METADATA_MISMATCH")
    meta = lines[0]["meta"]
    expected = source["exporter"]
    if (meta.get("exporter") != {"name": expected["name"], "version": expected["version"]}
            or meta.get("format") != {"version": expected["format"]}
            or meta.get("lean") != {"githash": expected["lean_githash"],
                                    "version": expected["lean_version"]}):
        raise ValueError("EXPORTER_METADATA_MISMATCH")
    theorem = policy["theorem"]
    names = [entry.get("str", {}).get("str") for entry in lines
             if entry.get("in") == theorem["name_id"]]
    matches = [entry["thm"] for entry in lines if "thm" in entry]
    if names != [theorem["name"]] or matches != [{
        "all": [theorem["name_id"]], "levelParams": [],
        "name": theorem["name_id"], "type": theorem["type_expr_id"],
        "value": theorem["value_expr_id"],
    }]:
        raise ValueError("THEOREM_IDENTITY_MISMATCH")
    return {"checker_commit": policy["checker"]["commit"],
            "export_sha256": digest(exported),
            "config_sha256": digest(configured), "theorem": theorem["name"]}


def mutated_export(original: bytes, theorem: dict) -> bytes:
    """Replace this theorem's proof with Sort, retaining its asserted type."""
    lines = original.splitlines(keepends=True)
    matches = [i for i, raw in enumerate(lines)
               if (entry := json.loads(raw)).get("thm", {}).get("name") == theorem["name_id"]]
    if len(matches) != 1:
        raise ValueError("MUTATION_TARGET_NOT_UNIQUE")
    index = matches[0]
    entry = json.loads(lines[index])
    if (entry["thm"].get("value") != theorem["value_expr_id"]
            or entry["thm"].get("type") != theorem["type_expr_id"]):
        raise ValueError("MUTATION_TARGET_MISMATCH")
    entry["thm"]["value"] = 0
    lines[index] = (json.dumps(entry, separators=(",", ":")) + "\n").encode()
    return b"".join(lines)


def run_binary(binary: Path, config: Path, cwd: Path) -> dict:
    if not binary.is_file() or not config.is_file():
        raise ValueError("NATIVE_BINARY_OR_CONFIG_MISSING")
    start = time.perf_counter_ns()
    proc = subprocess.run([str(binary), str(config)], cwd=cwd,
                          capture_output=True, check=False, timeout=120)
    elapsed_ns = time.perf_counter_ns() - start
    return {"exit_code": proc.returncode, "elapsed_ns": elapsed_ns,
            "binary_sha256": digest(binary.read_bytes()),
            "stdout_sha256": digest(proc.stdout),
            "stderr_sha256": digest(proc.stderr)}


def ci_context(env: dict, policy: dict, *, reader_workflow: str | None = None) -> dict:
    """CI-supplied provenance; NEVER derive from a receipt's runner field."""
    repo = policy["runner"]["repository"]
    if reader_workflow is not None and reader_workflow != "kernel-flash-cross-run-reuse-v1.yml":
        raise ValueError("UNTRUSTED_CI_CONTEXT")
    workflow = reader_workflow or policy["runner"]["workflow"]
    research_ref = env.get("GITHUB_REF", "")
    expected_workflow_ref = f"{repo}/.github/workflows/{workflow}@{research_ref}"
    if (env.get("GITHUB_REPOSITORY") != repo
            or env.get("GITHUB_WORKFLOW_REF") != expected_workflow_ref
            or research_ref not in RESEARCH_REFS
            or env.get("GITHUB_EVENT_NAME") != "push"):
        raise ValueError("UNTRUSTED_CI_CONTEXT")
    sha = env.get("GITHUB_SHA", "")
    run_id = env.get("GITHUB_RUN_ID", "")
    attempt = env.get("GITHUB_RUN_ATTEMPT", "")
    if (len(sha) != 40 or not all(c in "0123456789abcdef" for c in sha)
            or not run_id.isdecimal() or not attempt.isdecimal()
            or int(run_id) < 1 or int(attempt) < 1):
        raise ValueError("UNTRUSTED_CI_CONTEXT")
    return {"repository": repo, "workflow": workflow, "run_id": int(run_id),
            "attempt": int(attempt), "source_commit": sha}


def timing_stats(operation, iterations: int = 1000) -> dict:
    measured = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        operation()
        measured.append(time.perf_counter_ns() - start)
    ordered = sorted(measured)
    return {"iterations": iterations, "min_ns": ordered[0],
            "median_ns": int(statistics.median(ordered)),
            "p95_ns": ordered[int(0.95 * (iterations - 1))]}


def measured_candidate_identity(binary: Path, request: dict, policy: dict) -> dict:
    """Construct the new candidate using freshly measured checker bytes."""
    return bridge.candidate_identity(
        {"native": {"binary_sha256": digest(binary.read_bytes())}}, request, policy)


def paired_export_control(binary: Path, original_config: Path,
                          original_export: Path, cwd: Path,
                          theorem: dict) -> tuple[dict, dict, bytes]:
    """Causal control: same temporary config, only proof bytes change.

    The original fixture stays untouched. The pre-mutation temporary arm must
    ACCEPT to rule out path/config compatibility as a cause of rejection.
    """
    with tempfile.TemporaryDirectory(prefix="kernel-receipt-forged-") as tmp:
        copied_export = Path(tmp) / "export"
        original_bytes = original_export.read_bytes()
        copied_export.write_bytes(original_bytes)
        temp_config = copy.deepcopy(json.loads(original_config.read_text()))
        temp_config["export_file_path"] = str(copied_export.resolve())
        config_path = Path(tmp) / "config.json"
        config_path.write_text(json.dumps(temp_config))
        control = run_binary(binary, config_path, cwd)
        changed_bytes = mutated_export(original_bytes, theorem)
        copied_export.write_bytes(changed_bytes)
        negative = run_binary(binary, config_path, cwd)
    return control, negative, changed_bytes


def execute(flash: Path, report_path: Path, policy: dict) -> dict:
    context = ci_context(os.environ, policy)
    if git_head(HERE.parents[1]) != context["source_commit"]:
        raise ValueError("RUNNER_SOURCE_REVISION_MISMATCH")
    verified = validate_checkout(flash, policy)
    binary = (flash / "target/release" / policy["checker"]["binary"]).resolve()
    if binary != flash.resolve() / "target/release" / policy["checker"]["binary"]:
        raise ValueError("BINARY_PATH_MISMATCH")
    original_config = flash / policy["source"]["config_path"]
    positive = run_binary(binary, original_config.resolve(), flash)
    observation = {
        "schema": "mathgraph.kernel-native-observation.v1",
        "checker": policy["checker"], "source": policy["source"],
        "theorem": policy["theorem"],
        "runner": {**context, "evidence_acquisition": "IN_PROCESS_NATIVE_SUBPROCESS"},
        "native": positive,
    }
    request = policy["consumer"]
    qualification = bridge.qualify(observation, request, policy,
                                   trusted_context=context)
    graph = bridge.resolve(observation, request, policy,
                           trusted_context=context)
    control, negative, changed_bytes = paired_export_control(
        binary, original_config, flash / policy["source"]["export_path"],
        flash, policy["theorem"])
    withdrawn_graph = bridge.resolve(
        observation, request, policy, trusted_context=context,
        withdrawn=frozenset({"native.accept"}))
    candidate = measured_candidate_identity(binary, request, policy)
    eligible = lambda: bridge.reuse(
        observation, request, policy, candidate=candidate,
        prior_trusted_context=context, trusted_prior_receipt=True)
    reuse_result = eligible()
    # Operations are measured in process; neither includes Flash startup,
    # cargo build, JSON serialization, file I/O or persisted-artifact admission.
    timings = {"graph_resolution_in_process": timing_stats(lambda: bridge.resolve(
                   observation, request, policy, trusted_context=context)),
               "reuse_eligibility_in_process": timing_stats(eligible)}
    valid_withdrawal = (withdrawn_graph["states"]["kernel.bar"] == "UNKNOWN"
                        and withdrawn_graph["states"]["consumer.exact_bar_type"] == "UNKNOWN"
                        and withdrawn_graph["states"]["independent.control"] == "WARRANTED_BOUNDED")
    valid = (positive["exit_code"] == 0 and control["exit_code"] == 0
             and negative["exit_code"] == 1
             and qualification["status"] == "ADMITTED_BOUNDED"
             and graph["states"]["consumer.exact_bar_type"] == "WARRANTED_BOUNDED"
             and reuse_result["status"] == "REUSABLE_BOUNDED" and valid_withdrawal)
    report = {
        "schema": "mathgraph.kernel-receipt-bridge-report.v1",
        "status": "WARRANTED_BOUNDED" if valid else "UNKNOWN",
        "qualification_boundary": "FLASH_FIXTURE_NATIVE_CI_PLUS_OPERATOR_ADOPTED_IDENTITY",
        "limitations": ["no Nucleus acceptance", "no independent human intent validation",
                        "no cross-commit proof transport", "no cold-Mathlib speed claim",
                        "no persisted receipt retrieval or authentication measured",
                        "persisted reuse would require external artifact authentication"],
        "source_validation": verified,
        "observation": observation,
        "qualification": qualification,
        "graph": graph,
        "withdrawal": {"withdrawn": "native.accept",
                       "after": withdrawn_graph["states"],
                       "expected_dependent_unknown": valid_withdrawal},
        "mutation": {"change": "theorem proof ExprId 16 to Sort ExprId 0",
                     "mutated_export_sha256": digest(changed_bytes),
                     "same_config_unmutated_control": control,
                     "native": negative, "expected_exit_code": 1},
        "reuse": reuse_result,
        "timing": {"positive_native_elapsed_ns": positive["elapsed_ns"],
                   "same_config_control_elapsed_ns": control["elapsed_ns"],
                   "mutated_native_elapsed_ns": negative["elapsed_ns"],
                   **timings},
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flash-repo", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    policy = json.loads((HERE / "policy.json").read_text())
    try:
        report = execute(args.flash_repo.resolve(), args.report, policy)
    except (ValueError, FileNotFoundError, OSError, subprocess.SubprocessError) as error:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({"schema": "mathgraph.kernel-receipt-bridge-report.v1",
                                          "status": "UNKNOWN", "reason": str(error)},
                                         indent=2) + "\n")
        print(f"UNKNOWN: {error}")
        return 1
    print(f"{report['status']}: native ACCEPT={report['observation']['native']['exit_code']}; "
          f"paired unchanged exit={report['mutation']['same_config_unmutated_control']['exit_code']}; "
          f"forged export exit={report['mutation']['native']['exit_code']}; "
          f"graph={report['graph']['states']}")
    return 0 if report["status"] == "WARRANTED_BOUNDED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
