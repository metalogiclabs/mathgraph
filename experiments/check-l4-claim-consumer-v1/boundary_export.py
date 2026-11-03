"""Re-admit the exact historical L4YAML Lean artifact to one Boundary Warrant.

This is a retrospective, exact-artifact adapter. It never creates Lean proofs
from labels or reruns Lean, and cannot authorize an arbitrary future artifact.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

from mathgraph_check.boundary_warrant import (
    BoundaryWarrant, Conclusion, Dependency, Obligation, Relation, Subject,
    Verification, required_dependencies, scope_identity,
)
from mathgraph_check.warrant_resolution import Receipt

HERE = Path(__file__).resolve().parent
ARTIFACT_SHA256 = "57d139153c4d61003d61a002fd715c9ac7bbdc3f0f88431b710e45f9c558e5e2"
ARTIFACT_ID = 13214576201
RUN_ID = 41600843950
CONTROLLER = "2fb1fdb6558ae2b34861f73ed14cf2e8658b3378"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_rules():
    spec = importlib.util.spec_from_file_location("l4_claim_boundary_rules", HERE / "rules.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def export_l4_boundary(artifact_zip: Path) -> tuple[BoundaryWarrant, Receipt, dict]:
    """Require archived native observations, checked consumer and exact provenance.

    Only the byte-identified Actions artifact is accepted; the source-claim
    authority remains upstream-PR-declared, not independently customer-approved.
    """
    if _sha(Path(artifact_zip).read_bytes()) != ARTIFACT_SHA256:
        raise ValueError("ARTIFACT_IDENTITY_MISMATCH")
    with zipfile.ZipFile(artifact_zip) as archive:
        members = archive.namelist()
        if (len(members) != len(set(members))
                or any(info.file_size > 2_000_000 for info in archive.infolist())
                or sum(info.file_size for info in archive.infolist()) > 5_000_000):
            raise ValueError("UNSAFE_ARTIFACT")

        def raw(path: str) -> bytes:
            try:
                return archive.read(path)
            except KeyError as exc:
                raise ValueError("INCOMPLETE_ARTIFACT:" + path) from exc

        def observed(path: str) -> dict:
            return json.loads(raw(path))

        root = "experiments/check-l4-claim-consumer-v1/"
        frozen = ["contract.json", "claim-source.json"]
        frozen += ["probes/" + path.name for path in sorted((HERE / "probes").glob("*.lean"))]
        for relative in frozen:
            if raw(root + relative) != (HERE / relative).read_bytes():
                raise ValueError("FROZEN_CONTRACT_CHANGED:" + relative)

        data = observed("claim-results/receipt.json")
        archived_assessment = observed("claim-results/assessment.json")
        if data.get("controller_sha") != CONTROLLER:
            raise ValueError("CONTROLLER_IDENTITY_MISMATCH")
        for arm, outcomes in data.get("arms", {}).items():
            for probe, outcome in outcomes.items():
                name = "claim-results/logs/" + arm + "-" + probe
                for stream in ("stdout", "stderr"):
                    if outcome.get(stream) != raw(name + "." + stream).decode("utf-8"):
                        raise ValueError("NATIVE_LOG_RECEIPT_MISMATCH")
        for stream in ("stdout", "stderr"):
            if data.get("law", {}).get(stream) != raw(
                    "claim-results/logs/weakening-law." + stream).decode("utf-8"):
                raise ValueError("NATIVE_LOG_RECEIPT_MISMATCH")

    assessment = _read_rules().admit(data, CONTROLLER)
    if assessment != archived_assessment or assessment["state"] != "WARRANTED_BOUNDED":
        raise ValueError("UNQUALIFIED_LEAN_CONSUMER")
    if (assessment.get("weak_offering") != "REJECTED_AS_SUPPORT_FOR_STRONG_OBLIGATION"
            or assessment.get("axiom_free_claim") != "REJECTED"):
        raise ValueError("CONSUMER_NEGATIVE_CONTROL_MISSING")
    contract = json.loads((HERE / "contract.json").read_bytes())
    source = Subject(contract["repository"], contract["head_sha"],
                     data["archive_sha256"]["head"])
    obligation = Obligation(
        "l4yaml.empty-tail-constructors",
        contract["obligation"],
        contract["claim_authority"],
        _sha((HERE / "claim-source.json").read_bytes()),
    )
    relation = Relation(
        "logical_entailment",
        "Head constructor witnesses satisfy the named P consumer; P or True does not.",
        (("consumer_sha256", contract["probes_sha256"]["Consumer.lean"]),
         ("weak_consumer_sha256", contract["probes_sha256"]["WeakConsumer.lean"])),
    )
    verification = Verification(
        "formal", contract["toolchain"], _sha((HERE / "contract.json").read_bytes()),
        tuple(assessment["proof_assumptions"]["strong_consumer"]),
        "l4yaml:run:" + str(RUN_ID) + ":artifact:" + str(ARTIFACT_ID),
    )
    dependencies = required_dependencies(source, obligation, relation, verification) + (
        Dependency("evidence", "l4yaml:claim-consumer-artifact", ARTIFACT_SHA256),
    )
    warrant = BoundaryWarrant(
        source, obligation, relation, verification,
        Conclusion("SUPPORTED", tuple(assessment["boundary"])),
        dependencies,
    )
    return warrant, Receipt(verification.receipt_id, "formal", scope_identity(warrant)), assessment
