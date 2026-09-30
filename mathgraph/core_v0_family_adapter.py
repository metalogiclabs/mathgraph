"""Adapter from bounded cross-prover family discovery into Core V0.

The adapter accepts verifier authority and projection endpoints as explicit
inputs. Discovery rows alone never promote a claim or invent an implication.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping, Sequence

from mathgraph.core_v0 import (
    CoreGraph,
    EvidenceReceipt,
    Grammar,
    Object,
    Relation,
    RelationKind,
    Status,
    Support,
    Unknown,
    normalize,
    verify,
)


@dataclass(frozen=True)
class FamilyReplay:
    graph: CoreGraph
    object_by_claim: Mapping[str, Object]
    unknown_by_source: Mapping[str, Unknown]
    partition: Mapping[str, int]


def replay_family(
    discovery: Mapping[str, Any],
    *,
    grammar: Grammar,
    source_digests: Mapping[str, str],
    verified_claim_authorities: Mapping[str, Sequence[str]],
    refuted_source_authorities: Mapping[str, Sequence[str]] = (),
    implication_authorities: Mapping[str, Mapping[str, Any]] = (),
    repository: str,
    commit: str,
) -> FamilyReplay:
    """Compile one discovery result, preserving proof and UNKNOWN boundaries.

    ``verified_claim_authorities`` maps canonical claim IDs to already checked
    authority references. ``implication_authorities`` maps source occurrence
    IDs to explicit ``source_claim_id``, ``target_claim_id``, and authority
    references. Both are supplied by an outer verifier workflow.
    """

    refuted = dict(refuted_source_authorities)
    projections = dict(implication_authorities)
    graph = CoreGraph(grammars=[grammar])
    object_by_claim: dict[str, Object] = {}
    unknown_by_source: dict[str, Unknown] = {}

    def source_id(row: Mapping[str, Any]) -> str:
        return f"{row['theory']}.{row['formula']}"

    def ensure_object(claim_id: str, schema: str = "claim") -> Object:
        existing = object_by_claim.get(claim_id)
        if existing is not None:
            return existing
        return ensure_object_form(
            claim_id,
            {"canonical_claim_id": claim_id, "schema": schema},
        )

    def ensure_object_form(
        identity_key: str,
        normal_form: Mapping[str, Any],
        semantic_type: str = "claim",
    ) -> Object:
        existing = object_by_claim.get(identity_key)
        if existing is not None:
            return existing
        obj = normalize(
            identity_key,
            grammar,
            lambda _: normal_form,
            semantic_type=semantic_type,
        )
        assert isinstance(obj, Object)
        object_by_claim[identity_key] = obj
        graph.add_candidate(obj)
        return obj

    def attach_external_warrant(
        subject: Object | Relation | Unknown,
        *,
        source_ref: str,
        source_digest: str,
        authority_refs: Sequence[str],
        outcome: Status = Status.WARRANTED,
    ) -> None:
        support = Support(
            source_ref=source_ref,
            source_digest=source_digest,
            assumptions=tuple(authority_refs),
        )
        graph.add_support(support)
        graph.add_candidate(subject) if isinstance(subject, (Object, Relation)) else graph.add_unknown(subject)
        receipt = EvidenceReceipt.for_candidate(
            subject,
            verifier="cross-prover-closure-adapter",
            support_ids=(support.id,),
            boundary="external-verifier-authority-refs-required",
            payload={
                "authority_refs": sorted(authority_refs),
                "source_ref": source_ref,
                "source_digest": source_digest,
            },
            outcome=outcome,
        )
        graph.admit(verify(subject, receipt))

    occurrence_by_source: dict[str, Mapping[str, Any]] = {}
    for row in discovery.get("supported_occurrences", ()):
        name = source_id(row)
        occurrence_by_source[name] = row
        claim_id = str(row["claim_id"])
        obj = ensure_object(claim_id, str(row.get("certificate_schema", "claim")))
        source_digest = source_digests[str(row["theory"])]
        if row.get("source_proof_status") == "PINNED_PROOF_PRESENT":
            authorities = tuple(verified_claim_authorities.get(claim_id, ()))
            if not authorities:
                raise ValueError(f"missing external verifier authority for {claim_id}")
            attach_external_warrant(
                obj,
                source_ref=f"{repository}@{commit}:{row['theory']}.{row['formula']}",
                source_digest=source_digest,
                authority_refs=authorities,
            )
        elif row.get("source_proof_status") == "NO_PINNED_PROOF":
            unknown = normalize(row["normalized_surface"], grammar, lambda _: None)
            assert isinstance(unknown, Unknown)
            unknown_by_source[name] = unknown
            graph.add_unknown(unknown)

    for row in discovery.get("unsupported_occurrences", ()):
        name = source_id(row)
        occurrence_by_source[name] = row
        unknown = normalize(row["normalized_surface"], grammar, lambda _: None)
        assert isinstance(unknown, Unknown)
        unknown_by_source[name] = unknown
        graph.add_unknown(unknown)
        if name in refuted:
            authorities = tuple(refuted[name])
            if not authorities:
                raise ValueError(f"empty refutation authority for {name}")
            attach_external_warrant(
                unknown,
                source_ref=f"{repository}@{commit}:{name}",
                source_digest=source_digests[str(row["theory"])],
                authority_refs=authorities,
                outcome=Status.REJECTED,
            )

    for name, authority in sorted(projections.items()):
        if name not in occurrence_by_source:
            raise ValueError(f"projection source is not in discovery: {name}")
        source_claim = str(authority["source_claim_id"])
        target_claim = str(authority["target_claim_id"])
        authority_refs = tuple(authority.get("authority_refs", ()))
        if not source_claim or not target_claim or not authority_refs:
            raise ValueError(f"projection mapping for {name} lacks endpoints or authority")
        source_obj = (
            ensure_object_form(
                source_claim,
                authority["source_normal_form"],
                str(authority.get("source_semantic_type", "claim")),
            )
            if "source_normal_form" in authority
            else ensure_object(source_claim)
        )
        target_obj = (
            ensure_object_form(
                target_claim,
                authority["target_normal_form"],
                str(authority.get("target_semantic_type", "claim")),
            )
            if "target_normal_form" in authority
            else ensure_object(target_claim)
        )
        edge = Relation(RelationKind.IMPLIES, (source_obj.id,), (target_obj.id,))
        row = occurrence_by_source[name]
        attach_external_warrant(
            edge,
            source_ref=f"{repository}@{commit}:{name}:interface-projection",
            source_digest=source_digests[str(row["theory"])],
            authority_refs=authority_refs,
        )

    # Trigger closure once so derived edges and consequences are part of .mg.
    graph.close()
    partition = {
        "source_occurrences": int(discovery.get("source_lemma_count", 0)),
        "supported_occurrences": int(discovery.get("supported_occurrence_count", 0)),
        "warranted_exact_occurrences": sum(
            1 for row in discovery.get("supported_occurrences", ())
            if row.get("source_proof_status") == "PINNED_PROOF_PRESENT"
        ),
        "unknown_supported_occurrences": sum(
            1 for row in discovery.get("supported_occurrences", ())
            if row.get("source_proof_status") == "NO_PINNED_PROOF"
        ),
        "unsupported_occurrences": len(discovery.get("unsupported_occurrences", ())),
        "rejected_unsupported_occurrences": len(refuted),
        "warranted_implication_occurrences": len(projections),
    }
    return FamilyReplay(graph, object_by_claim, unknown_by_source, partition)


def git_blob_sha1(data: bytes) -> str:
    """Git blob digest helper used by the pinned-source adapter workflow."""

    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
