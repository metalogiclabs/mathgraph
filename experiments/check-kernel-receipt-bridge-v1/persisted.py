"""Strict cross-job stored-Flash-receipt consumer; no kernel execution.

The input bytes and metadata alone cannot authenticate themselves. The caller
MUST obtain `metadata` from the GitHub Actions API and `expected_digest` from
the successful producer's trusted GitHub Actions job output. `current_context`
MUST come from the reader job environment, never from saved report JSON. This
is scoped same-run Actions provenance, not a portable signature.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.request import Request, urlopen

import bridge
import native
from conformance.protocol_v1.consumer import parse_json, ProtocolError


ARTIFACT_NAME = "kernel-bridge-native-evidence"
PRODUCER_JOB = "native-receipt"
RESEARCH_BRANCH = "research/check-kernel-persisted-reuse-20261104"
WORKFLOW_PATH = ".github/workflows/check-kernel-receipt-bridge-v1.yml"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SHA40 = re.compile(r"[0-9a-f]{40}\Z")


def _unknown(reason: str) -> dict:
    return {"status": "UNKNOWN", "permission": "ADVISORY_ONLY", "reason": reason}


def _run_metadata_admitted(metadata: dict, policy: dict, context: dict) -> bool:
    if not isinstance(metadata, dict) or not isinstance(context, dict):
        return False
    run, jobs, artifacts = (metadata.get("run"), metadata.get("jobs"),
                            metadata.get("artifacts"))
    if not isinstance(run, dict) or not isinstance(jobs, list) or not isinstance(artifacts, list):
        return False
    repository = run.get("repository")
    if (not isinstance(repository, dict)
            or type(run.get("id")) is not int
            or type(run.get("run_attempt")) is not int
            or type(context.get("run_id")) is not int
            or type(context.get("attempt")) is not int):
        return False
    repo, workflow = policy["runner"]["repository"], policy["runner"]["workflow"]
    if workflow != WORKFLOW_PATH.rsplit("/", 1)[-1]:
        return False
    if (run.get("id") != context.get("run_id") or run.get("head_sha") != context.get("source_commit")
            or run.get("run_attempt") != context.get("attempt")
            or repository.get("full_name") != context.get("repository")
            or run.get("path") != WORKFLOW_PATH
            or run.get("head_branch") != RESEARCH_BRANCH
            or run.get("event") != "push" or run.get("status") != "in_progress"
            or context.get("repository") != repo or context.get("workflow") != workflow):
        return False
    producers = [job for job in jobs if isinstance(job, dict) and job.get("name") == PRODUCER_JOB]
    if len(producers) != 1:
        return False
    job = producers[0]
    if (type(job.get("id")) is not int or job["id"] < 1
            or type(job.get("run_id")) is not int
            or job["run_id"] != context.get("run_id")
            or job.get("status") != "completed" or job.get("conclusion") != "success"):
        return False
    stored = [artifact for artifact in artifacts
              if isinstance(artifact, dict) and artifact.get("name") == ARTIFACT_NAME]
    if len(stored) != 1:
        return False
    artifact = stored[0]
    workflow_run = artifact.get("workflow_run")
    if (type(artifact.get("id")) is not int or artifact["id"] < 1
            or artifact.get("expired") is not False
            or not isinstance(workflow_run, dict)
            or type(workflow_run.get("id")) is not int
            or workflow_run.get("id") != context["run_id"]
            or workflow_run.get("head_sha") != context["source_commit"]
            or not isinstance(artifact.get("digest"), str)
            or not artifact["digest"].startswith("sha256:")
            or not _SHA256.fullmatch(artifact["digest"][7:])):
        return False
    return True


def appraise(metadata: dict, source_bytes: bytes, expected_digest: str,
            policy: dict, current_context: dict) -> dict:
    """Appraise trusted external run facts plus exact report and adapter pins."""
    if (not isinstance(source_bytes, bytes)
            or not isinstance(expected_digest, str)
            or not _SHA256.fullmatch(expected_digest)):
        return _unknown("INVALID_EXPECTED_DIGEST")
    if hashlib.sha256(source_bytes).hexdigest() != expected_digest:
        return _unknown("ARTIFACT_BYTES_MISMATCH")
    if not _run_metadata_admitted(metadata, policy, current_context):
        return _unknown("UNTRUSTED_PRODUCER_METADATA")
    try:
        report = parse_json(source_bytes, "native-report.json")
    except ProtocolError as error:
        return _unknown(error.reason_code)
    if (report.get("schema") != "mathgraph.kernel-receipt-bridge-report.v1"
            or report.get("status") != "WARRANTED_BOUNDED"):
        return _unknown("UNQUALIFIED_NATIVE_REPORT")
    validated = report.get("source_validation")
    if validated != {
        "checker_commit": policy["checker"]["commit"],
        "config_sha256": policy["source"]["config_sha256"],
        "export_sha256": policy["source"]["export_sha256"],
        "theorem": policy["theorem"]["name"],
    }:
        return _unknown("SOURCE_CONTEXT_DRIFT")
    observation = report.get("observation")
    qualification = report.get("qualification")
    mutation = report.get("mutation")
    withdrawal = report.get("withdrawal")
    if not all(isinstance(x, dict) for x in (observation, qualification, mutation, withdrawal)):
        return _unknown("INCOMPLETE_NATIVE_REPORT")
    if not (isinstance(mutation.get("native"), dict)
            and isinstance(mutation.get("same_config_unmutated_control"), dict)
            and type(mutation["native"].get("exit_code")) is int
            and mutation["native"]["exit_code"] == 1
            and type(mutation["same_config_unmutated_control"].get("exit_code")) is int
            and mutation["same_config_unmutated_control"]["exit_code"] == 0):
        return _unknown("NATIVE_CONTROL_INCOMPLETE")
    decision = bridge.qualify(observation, policy["consumer"], policy,
                              trusted_context=current_context)
    if (decision["status"] != "ADMITTED_BOUNDED"
            or qualification.get("status") != "ADMITTED_BOUNDED"
            or qualification.get("fingerprint") != decision["fingerprint"]):
        return _unknown("CHECKER_OR_ADAPTER_DRIFT")
    removed = bridge.resolve(observation, policy["consumer"], policy,
                             trusted_context=current_context,
                             withdrawn=frozenset({"native.accept"}))["states"]
    if (withdrawal.get("after") != removed
            or removed.get("kernel.bar") != "UNKNOWN"
            or removed.get("consumer.exact_bar_type") != "UNKNOWN"
            or removed.get("independent.control") != "WARRANTED_BOUNDED"):
        return _unknown("INVALID_NATIVE_WITHDRAWAL")
    return {"status": "ADMITTED_PERSISTED_BOUNDED", "permission": "ADVISORY_ONLY",
            "reason": "NONE", "report": report}


def consume(metadata: dict, source_bytes: bytes, expected_digest: str,
            policy: dict, current_context: dict, *,
            withdrawn: frozenset[str] = frozenset()) -> dict:
    """Retrieve a historical warrant, never infer a freshly measured candidate."""
    session = WarmReceiptSession(metadata, source_bytes, expected_digest, policy,
                                 current_context)
    return session.lookup(policy["consumer"], policy, withdrawn=withdrawn)


class WarmReceiptSession:
    """Authenticate once, serve exact historical warrant lookups locally.

    A consumer of a saved report has NOT independently measured any current
    checker binary. In particular, it must not invoke bridge.reuse with a
    candidate constructed from the saved observation. Any applicability to a
    fresh source checkout remains UNKNOWN until independently remeasured.
    """

    def __init__(self, metadata: dict, source_bytes: bytes, expected_digest: str,
                 policy: dict, current_context: dict):
        self._policy = copy.deepcopy(policy)
        self._context = copy.deepcopy(current_context)
        self._appraisal = appraise(metadata, source_bytes, expected_digest,
                                   self._policy, self._context)
        self._observation = None
        self._base_states = None
        self._fingerprint = None
        if self._appraisal["status"] == "ADMITTED_PERSISTED_BOUNDED":
            self._observation = self._appraisal["report"]["observation"]
            closure = bridge.resolve(self._observation, self._policy["consumer"],
                                     self._policy, trusted_context=self._context)
            self._base_states = closure["states"]
            self._fingerprint = closure["decision"]["fingerprint"]

    def lookup(self, request: dict, policy: dict, *,
               withdrawn: frozenset[str] = frozenset()) -> dict:
        if self._observation is None:
            return {**self._appraisal, "current_applicability": "UNKNOWN"}
        if policy != self._policy or request != self._policy["consumer"]:
            return {**_unknown("FRESH_CANDIDATE_IDENTITY_NOT_ESTABLISHED"),
                    "current_applicability": "UNKNOWN"}
        if withdrawn:
            closure = bridge.resolve(self._observation, request, self._policy,
                                     trusted_context=self._context, withdrawn=withdrawn)
            states = closure["states"]
        else:
            states = self._base_states.copy()
        supported = states.get("consumer.exact_bar_type") == "WARRANTED_BOUNDED"
        return {
            "status": "HISTORICAL_WARRANT_RETRIEVED" if supported else "UNKNOWN",
            "current_applicability": "UNKNOWN",
            "permission": "ADVISORY_ONLY",
            "reason": "NONE" if supported else "WITHDRAWN_OR_UNSUPPORTED",
            "source": "STORED_GITHUB_ACTIONS_ARTIFACT",
            "fingerprint": self._fingerprint,
            "states": states,
        }


def fetch_metadata(context: dict, token: str) -> dict:
    """Read-only GitHub REST evidence, using the runner's scoped job token."""
    if (not isinstance(context, dict) or context.get("repository") != "metalogiclabs/mathgraph"
            or type(context.get("run_id")) is not int or context["run_id"] < 1
            or type(context.get("attempt")) is not int or context["attempt"] < 1
            or not isinstance(context.get("source_commit"), str)
            or not _SHA40.fullmatch(context["source_commit"])
            or not isinstance(token, str) or not token):
        raise ValueError("UNTRUSTED_API_CONTEXT")
    root = ("https://api.github.com/repos/metalogiclabs/mathgraph/actions/runs/"
            + str(context["run_id"]))

    def fetch(url: str) -> dict:
        request = Request(url, headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with urlopen(request, timeout=25) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("GITHUB_METADATA_TOO_LARGE")
        return parse_json(raw, url)

    run = fetch(root)
    jobs = fetch(root + "/jobs?per_page=100")
    artifacts = fetch(root + "/artifacts?per_page=100")
    if not isinstance(jobs.get("jobs"), list) or not isinstance(artifacts.get("artifacts"), list):
        raise ValueError("INVALID_GITHUB_METADATA")
    return {"run": run, "jobs": jobs["jobs"], "artifacts": artifacts["artifacts"]}


def run_consumer(report_file: Path, external_digest: str, policy: dict,
                 context: dict, *, metadata_provider) -> dict:
    """Read the stored file, then use externally obtained producer authority."""
    start = time.perf_counter_ns()
    metadata = metadata_provider()
    metadata_ns = time.perf_counter_ns() - start
    start = time.perf_counter_ns()
    if not report_file.is_file() or report_file.stat().st_size > 8_000_000:
        raise ValueError("STORED_REPORT_MISSING_OR_OVERSIZED")
    raw = report_file.read_bytes()
    read_ns = time.perf_counter_ns() - start
    start = time.perf_counter_ns()
    session = WarmReceiptSession(metadata, raw, external_digest, policy, context)
    result = session.lookup(policy["consumer"], policy)
    appraisal_ns = time.perf_counter_ns() - start
    warm = native.timing_stats(lambda: session.lookup(policy["consumer"], policy))
    return {**result, "native_checker_invocations_in_consumer": 0,
            "timing_ns": {"metadata_fetch": metadata_ns,
                          "stored_file_read": read_ns,
                          "appraisal_and_resolve": appraisal_ns,
                          "warm_lookup_median": warm["median_ns"],
                          "warm_lookup_p95": warm["p95_ns"]},
            "warm_lookup_samples": warm["iterations"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        policy = json.loads((Path(__file__).parent / "policy.json").read_text())
        context = native.ci_context(os.environ, policy)
        if native.git_head(native.HERE.parents[1]) != context["source_commit"]:
            raise ValueError("READER_SOURCE_REVISION_MISMATCH")
        expected_digest = os.environ.get("PRODUCER_REPORT_SHA256", "")
        result = run_consumer(args.artifact, expected_digest, policy, context,
                              metadata_provider=lambda: fetch_metadata(
                                  context, os.environ.get("GITHUB_TOKEN", "")))
    except (ValueError, OSError, ProtocolError) as error:
        result = _unknown(str(error))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(f"Persisted Flash read: {result['status']} ({result['reason']})")
    return 0 if result["status"] == "HISTORICAL_WARRANT_RETRIEVED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
