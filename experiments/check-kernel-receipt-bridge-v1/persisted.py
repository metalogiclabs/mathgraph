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


def _run_metadata_admitted(metadata: dict, policy: dict, context: dict, *,
                           trusted_completed_producer: bool = False) -> bool:
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
            or run.get("event") != "push"
            or context.get("repository") != repo or context.get("workflow") != workflow):
        return False
    if trusted_completed_producer is True:
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            return False
    elif run.get("status") != "in_progress":
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
            policy: dict, current_context: dict, *,
            trusted_completed_producer: bool = False) -> dict:
    """Appraise trusted external run facts plus exact report and adapter pins."""
    if (not isinstance(source_bytes, bytes)
            or not isinstance(expected_digest, str)
            or not _SHA256.fullmatch(expected_digest)):
        return _unknown("INVALID_EXPECTED_DIGEST")
    if hashlib.sha256(source_bytes).hexdigest() != expected_digest:
        return _unknown("ARTIFACT_BYTES_MISMATCH")
    if not _run_metadata_admitted(metadata, policy, current_context,
                                 trusted_completed_producer=trusted_completed_producer):
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
                 policy: dict, current_context: dict, *,
                 trusted_completed_producer: bool = False):
        self._policy = copy.deepcopy(policy)
        self._context = copy.deepcopy(current_context)
        self._producer_trust_boundary = (
            "PINNED_COMPLETED_GITHUB_RUN" if trusted_completed_producer is True
            else "SAME_IN_PROGRESS_GITHUB_RUN")
        self._appraisal = appraise(metadata, source_bytes, expected_digest,
                                   self._policy, self._context,
                                   trusted_completed_producer=trusted_completed_producer)
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
            "producer_trust_boundary": self._producer_trust_boundary,
            "fingerprint": self._fingerprint,
            "states": states,
        }

    def remeasure_and_reuse(self, flash_checkout: Path, checker_binary: Path,
                            request: dict, policy: dict, *,
                            withdrawn: frozenset[str] = frozenset()) -> dict:
        """Exact reuse only after measuring the actual candidate files anew.

        The caller supplies paths, not an identity fabricated from the report.
        The binary may be an immutable verified prior artifact, provided it is
        the actual checker candidate under consideration. This does not prove
        that a separately rebuilt binary is equivalent.
        """
        if self._observation is None:
            return {**_unknown("PRIOR_RECEIPT_NOT_ADMITTED"),
                    "current_applicability": "UNKNOWN"}
        if policy != self._policy or request != self._policy["consumer"]:
            return {**_unknown("CURRENT_REQUEST_OR_POLICY_DRIFT"),
                    "current_applicability": "UNKNOWN"}
        try:
            if (not checker_binary.is_file()
                    or not 0 < checker_binary.stat().st_size <= 128_000_000):
                raise ValueError("CHECKER_BINARY_MISSING_OR_OVERSIZED")
            validated_source = native.validate_checkout(flash_checkout, self._policy)
            candidate = native.measured_candidate_identity(checker_binary, request,
                                                            self._policy)
        except (OSError, ValueError) as error:
            return {**_unknown(str(error)), "current_applicability": "UNKNOWN"}
        decision = bridge.reuse(self._observation, request, self._policy,
                                candidate=candidate, prior_trusted_context=self._context,
                                trusted_prior_receipt=True)
        closure = bridge.resolve(self._observation, request, self._policy,
                                 trusted_context=self._context, withdrawn=withdrawn)
        states = closure["states"]
        supported = (decision["status"] == "REUSABLE_BOUNDED"
                     and states.get("consumer.exact_bar_type") == "WARRANTED_BOUNDED")
        return {
            "status": "REUSABLE_BOUNDED" if supported else "UNKNOWN",
            "current_applicability": "EXACT_REMEASURED" if supported else "UNKNOWN",
            "permission": "ADVISORY_ONLY",
            "reason": "NONE" if supported else "MEASURED_CANDIDATE_DRIFT_OR_WITHDRAWAL",
            "source": "STORED_GITHUB_ACTIONS_ARTIFACT_PLUS_FRESH_FILE_MEASUREMENT",
            "producer_trust_boundary": self._producer_trust_boundary,
            "fingerprint": decision["fingerprint"],
            "states": states,
            "measured_source": validated_source,
            "native_checker_invocations_in_consumer": 0,
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
                 context: dict, *, metadata_provider,
                 flash_checkout: Path | None = None,
                 checker_binary: Path | None = None,
                 trusted_completed_producer: bool = False) -> dict:
    """Read the stored file, then use externally obtained producer authority."""
    if (flash_checkout is None) != (checker_binary is None):
        raise ValueError("INCOMPLETE_MEASURED_CANDIDATE_PATHS")
    start = time.perf_counter_ns()
    metadata = metadata_provider()
    metadata_ns = time.perf_counter_ns() - start
    start = time.perf_counter_ns()
    if not report_file.is_file() or report_file.stat().st_size > 8_000_000:
        raise ValueError("STORED_REPORT_MISSING_OR_OVERSIZED")
    raw = report_file.read_bytes()
    read_ns = time.perf_counter_ns() - start
    start = time.perf_counter_ns()
    session = WarmReceiptSession(metadata, raw, external_digest, policy, context,
                                 trusted_completed_producer=trusted_completed_producer)
    result = session.lookup(policy["consumer"], policy)
    appraisal_ns = time.perf_counter_ns() - start
    warm = native.timing_stats(lambda: session.lookup(policy["consumer"], policy))
    measured_ns = None
    if flash_checkout is not None and checker_binary is not None:
        start = time.perf_counter_ns()
        result = session.remeasure_and_reuse(
            flash_checkout, checker_binary, policy["consumer"], policy)
        measured_ns = time.perf_counter_ns() - start
    timings = {"metadata_fetch": metadata_ns,
               "stored_file_read": read_ns,
               "appraisal_and_resolve": appraisal_ns,
               "warm_lookup_median": warm["median_ns"],
               "warm_lookup_p95": warm["p95_ns"]}
    if measured_ns is not None:
        timings["measured_candidate_and_reuse"] = measured_ns
    return {**result, "native_checker_invocations_in_consumer": 0,
            "timing_ns": timings,
            "warm_lookup_samples": warm["iterations"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--flash-repo", type=Path)
    parser.add_argument("--candidate-binary", type=Path)
    parser.add_argument("--prior-run-id", type=int)
    parser.add_argument("--prior-source-commit")
    parser.add_argument("--prior-attempt", type=int)
    parser.add_argument("--prior-report-sha256")
    args = parser.parse_args(argv)
    try:
        policy = json.loads((Path(__file__).parent / "policy.json").read_text())
        prior_fields = (args.prior_run_id, args.prior_source_commit,
                        args.prior_attempt, args.prior_report_sha256)
        if any(value is not None for value in prior_fields) and not all(
                value is not None for value in prior_fields):
            raise ValueError("INCOMPLETE_PINNED_PRIOR_PRODUCER")
        completed = all(value is not None for value in prior_fields)
        context = native.ci_context(
            os.environ, policy,
            reader_workflow="kernel-flash-cross-run-reuse-v1.yml" if completed else None)
        if native.git_head(native.HERE.parents[1]) != context["source_commit"]:
            raise ValueError("READER_SOURCE_REVISION_MISMATCH")
        if completed:
            if (args.prior_run_id < 1 or args.prior_run_id == context["run_id"]
                    or args.prior_attempt < 1
                    or not _SHA40.fullmatch(args.prior_source_commit)
                    or not _SHA256.fullmatch(args.prior_report_sha256)):
                raise ValueError("INVALID_PINNED_PRIOR_PRODUCER")
            producer_context = {**context, "run_id": args.prior_run_id,
                                "attempt": args.prior_attempt,
                                "source_commit": args.prior_source_commit,
                                "workflow": policy["runner"]["workflow"]}
            expected_digest = args.prior_report_sha256
        else:
            producer_context = context
            expected_digest = os.environ.get("PRODUCER_REPORT_SHA256", "")
        result = run_consumer(args.artifact, expected_digest, policy, producer_context,
                              metadata_provider=lambda: fetch_metadata(
                                  producer_context, os.environ.get("GITHUB_TOKEN", "")),
                              flash_checkout=args.flash_repo,
                              checker_binary=args.candidate_binary,
                              trusted_completed_producer=completed)
        if completed:
            result = {**result, "prior_run_id": producer_context["run_id"],
                      "current_run_id": context["run_id"]}
    except (ValueError, OSError, ProtocolError) as error:
        result = _unknown(str(error))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(f"Persisted Flash read: {result['status']} ({result['reason']})")
    return 0 if result["status"] in {"HISTORICAL_WARRANT_RETRIEVED",
                                      "REUSABLE_BOUNDED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
