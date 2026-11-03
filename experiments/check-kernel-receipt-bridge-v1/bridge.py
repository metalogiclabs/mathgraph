"""Bounded kernel-exit admission into MathGraph's existing warrant resolver.

SECURITY BOUNDARY: this does not authenticate a run, a GitHub identity or a
kernel result. The privileged native harness must supply `trusted_context`
from its own environment and must itself verify binary/source bytes. Never
populate trusted_context from a user-provided observation or saved JSON.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys


# The experiment is a direct file invocation, not an installed Python package.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mathgraph_check.warrant_resolution import (  # noqa: E402
    Claim, QualifiedRelation, Receipt, Route, resolve_graph,
)


_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
# Bind the adapter once per process. Rehashing here on every graph resolution
# would itself become the bottleneck and mislabel disk I/O as in-memory reuse.
_ADAPTER_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _native_admitted(observation: dict, policy: dict, trusted_context: dict | None) -> bool:
    if not isinstance(observation, dict) or not isinstance(trusted_context, dict):
        return False
    if observation.get("schema") != "mathgraph.kernel-native-observation.v1":
        return False
    if not all(observation.get(key) == policy.get(key) for key in ("checker", "source", "theorem")):
        return False
    runner = observation.get("runner")
    native = observation.get("native")
    if not isinstance(runner, dict) or not isinstance(native, dict):
        return False
    if not all(runner.get(key) == policy["runner"][key] for key in ("repository", "workflow")):
        return False
    fields = ("repository", "workflow", "source_commit", "run_id", "attempt")
    if not all(runner.get(key) == trusted_context.get(key) for key in fields):
        return False
    if runner.get("evidence_acquisition") != "IN_PROCESS_NATIVE_SUBPROCESS":
        return False
    if not isinstance(runner.get("source_commit"), str) or not _HEX40.fullmatch(runner["source_commit"]):
        return False
    if any(type(runner.get(key)) is not int or runner[key] < 1 for key in ("run_id", "attempt")):
        return False
    if type(native.get("exit_code")) is not int or native["exit_code"] != 0:
        return False
    if type(native.get("elapsed_ns")) is not int or native["elapsed_ns"] < 0:
        return False
    return all(isinstance(native.get(key), str) and _HEX64.fullmatch(native[key])
               for key in ("binary_sha256", "stdout_sha256", "stderr_sha256"))


def _fingerprint(observation: dict, request: dict, policy: dict) -> str:
    """A cache identity, not authentication; the run ID stays in provenance."""
    relevant = candidate_identity(observation, request, policy)
    canonical = json.dumps(relevant, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def candidate_identity(observation: dict, request: dict, policy: dict) -> dict:
    """Complete source/context/target identity. Caller must measure source bytes.

    This is a helper for constructing a candidate from trusted measurements;
    constructing it from a prior receipt cannot prove current checkout identity.
    """
    return {
        "checker": policy["checker"], "source": policy["source"],
        "theorem": policy["theorem"], "consumer": request,
        "binary_sha256": observation["native"]["binary_sha256"],
        "adapter_sha256": _ADAPTER_SHA256,
    }


def reuse(prior_observation: dict, request: dict, policy: dict, *,
          candidate: dict, prior_trusted_context: dict | None = None,
          trusted_prior_receipt: bool = False) -> dict:
    """Exact memoization only; no new proof or cross-revision transport.

    `trusted_prior_receipt` is an external authority decision (e.g. admission
    of an authenticated CI artifact), NEVER a field read from saved JSON.
    `candidate` must be independently measured from today's actual input files
    and checker binary. This function only tests exact identity.
    """
    admission = qualify(prior_observation, request, policy,
                        trusted_context=prior_trusted_context)
    exact = (isinstance(candidate, dict)
             and admission["status"] == "ADMITTED_BOUNDED"
             and candidate == candidate_identity(prior_observation, request, policy))
    return {
        "status": "REUSABLE_BOUNDED" if trusted_prior_receipt is True and exact else "UNKNOWN",
        "permission": "ADVISORY_ONLY",
        "fingerprint": admission["fingerprint"] if exact else None,
        "trust_boundary": "TRUSTED_NATIVE_OR_AUTHENTICATED_PRIOR_PLUS_REMEASURED_FILES",
    }


def qualify(observation: dict, request: dict, policy: dict, *,
            trusted_context: dict | None = None) -> dict:
    """Admit only the pinned native acceptance and the exact adopted target."""
    native_ok = _native_admitted(observation, policy, trusted_context)
    target_ok = isinstance(request, dict) and request == policy.get("consumer")
    admitted = native_ok and target_ok
    return {
        "status": "ADMITTED_BOUNDED" if admitted else "UNKNOWN",
        "permission": "ADVISORY_ONLY",
        "native_admitted": native_ok,
        "consumer_admitted": admitted,
        "authority_boundary": "PRIVILEGED_NATIVE_RUNNER_CONTEXT_REQUIRED",
        "source_sha256": policy["source"]["export_sha256"],
        "fingerprint": _fingerprint(observation, request, policy) if admitted else None,
    }


def resolve(observation: dict, request: dict, policy: dict, *,
            withdrawn: frozenset[str] = frozenset(),
            trusted_context: dict | None = None) -> dict:
    """Let the existing resolver determine all active and withdrawn routes."""
    decision = qualify(observation, request, policy, trusted_context=trusted_context)
    kernel_scope = "flash:" + policy["source"]["export_sha256"]
    target_scope = "check:operator-adopted:" + policy["source"]["export_sha256"]
    control_scope = "experiment:unrelated-control"
    claims = [Claim("kernel.bar", "formal", kernel_scope),
              Claim("consumer.exact_bar_type", "formal", target_scope),
              Claim("independent.control", "formal", control_scope)]
    receipts = [Receipt("native.accept", "formal", kernel_scope),
                Receipt("identity.verified", "formal", target_scope),
                Receipt("identity.adoption", "formal", target_scope),
                Receipt("control.fixture", "formal", control_scope)]
    routes = [Route("independent.control", ("control.fixture",))]
    relations = []
    if decision["native_admitted"]:
        routes.append(Route("kernel.bar", ("native.accept",)))
    if decision["consumer_admitted"]:
        exact_route = Route("consumer.exact_bar_type", ("identity.adoption",),
                            ("kernel.bar",), relation="exact-identity")
        routes.append(exact_route)
        relations.append(QualifiedRelation(
            "exact-identity", "formal", kernel_scope, "formal", target_scope,
            "identity.verified", ("identity.adoption",), checked_route=exact_route,
        ))
    result = resolve_graph(claims, routes, receipts, withdrawn=withdrawn,
                           relations=relations)
    return {"decision": decision, "states": dict(result.states),
            "active_routes": [route.conclusion for route in result.active_routes]}
