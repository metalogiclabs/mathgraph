#!/usr/bin/env python3
"""Bounded SACM evidence-lineage audit; NOT a safety or certification verdict.

The XML is an *argument template*, not independent proof that assessments exist.
Source authenticity must be established separately by Git object matching.
"""
from __future__ import annotations
from collections import defaultdict, deque
from dataclasses import dataclass
from hashlib import sha1, sha256
import itertools
import json
import sys
import xml.etree.ElementTree as ET

OASC_REPO = "EdgeCaseResearch/oasc"
OASC_COMMIT = "abf48ef74d07ff485ef759c5f6f5390953ca45c6"
OASC_BLOB = "8b838d1cc4ed709cda65d2a38d366c95925cc34f"
OASC_PATH = "open-autonomy-safety-case.sacm.xml"

def git_blob(data: bytes) -> str:
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]

@dataclass
class Case:
    claims: dict
    artifacts: dict
    references: dict
    evidence_edges: tuple
    inference_edges: tuple
    context_edges: tuple
    reverse: dict
    source_hash: str

def parse_case(data: bytes, *, pin: str = OASC_BLOB) -> Case:
    if git_blob(data) != pin:
        raise ValueError("source Git blob is not the frozen upstream object")
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("external entity/DOCTYPE not admitted")
    root = ET.fromstring(data)
    if local(root.tag) != "AssuranceCasePackage":
        raise ValueError("unexpected SACM root")
    by_id = {}
    names = {}
    for e in root.iter():
        identity = e.get("id")
        if identity:
            if identity in by_id:
                raise ValueError(f"duplicate SACM identifier: {identity}")
            by_id[identity] = e
            names[identity] = local(e.tag)
    claims = {k: el.get("content", "") for k, el in by_id.items()
              if names[k] == "claim"}
    artifacts = {k: el.get("name", "") for k, el in by_id.items()
                 if names[k] == "artifact"}
    refs = {k: el.get("referencedArtifact") for k, el in by_id.items()
            if names[k] == "artifactReference"}
    for ident, target in refs.items():
        if target not in artifacts:
            raise ValueError(f"broken artifact reference: {ident} -> {target}")
    if len(claims) < 2 or not refs:
        raise ValueError("insufficient argument structure")
    edges = {"assertedEvidence": [], "assertedInference": [], "assertedContext": []}
    for ident, el in by_id.items():
        kind = names[ident]
        if kind not in edges:
            continue
        src = [x.get("href", "") for x in el if local(x.tag) == "source"]
        dst = [x.get("href", "") for x in el if local(x.tag) == "target"]
        if not src or len(dst) != 1 or not all(s.startswith("#") for s in src+dst):
            raise ValueError(f"malformed edge: {ident}")
        src = [s[1:] for s in src]
        d = dst[0][1:]
        if d not in by_id or any(s not in by_id for s in src):
            raise ValueError(f"dangling edge: {ident}")
        if kind == "assertedInference":
            if d not in claims or any(s not in claims for s in src):
                raise ValueError(f"nonclaim inference: {ident}")
        if kind == "assertedEvidence":
            if d not in claims or any(s not in refs for s in src):
                raise ValueError(f"invalid cited-evidence endpoint: {ident}")
        for s in src:
            edges[kind].append((s,d,ident))
        for x in el:
            if local(x.tag) == "reasoning":
                rid = x.get("href", "").lstrip("#")
                if rid not in by_id or names[rid] != "argumentReasoning":
                    raise ValueError(f"bad reasoner reference: {ident}")
    directed = edges["assertedEvidence"] + edges["assertedInference"]
    reverse = defaultdict(list)
    for src, target, edge_id in directed:
        reverse[src].append(target)
    # Refuse cyclic documentary dependence: acyclic forward closure is essential.
    color = {}
    def dfs(node):
        if color.get(node,0) == 1:
            raise ValueError(f"cyclic dependency: {node}")
        if color.get(node,0) == 2:
            return
        color[node] = 1
        for dst in reverse.get(node,()):
            dfs(dst)
        color[node] = 2
    for node in set(refs)|set(claims):
        dfs(node)
    return Case(claims, artifacts, refs, tuple(edges["assertedEvidence"]),
                tuple(edges["assertedInference"]), tuple(edges["assertedContext"]),
                dict(reverse), sha256(data).hexdigest())

def bfs_consequences(case: Case, source: str) -> list[str]:
    if source not in case.references:
        raise ValueError(f"not an evidence reference: {source}")
    reached, frontier = set(), deque([source])
    while frontier:
        node = frontier.popleft()
        for nxt in case.reverse.get(node, ()):
            if nxt not in reached:
                reached.add(nxt)
                frontier.append(nxt)
    return sorted(reached)

def independent_fixpoint(case: Case, source: str) -> list[str]:
    """Different implementation, rescanning all edges until a fixed point."""
    present = {source}
    edges = case.evidence_edges + case.inference_edges
    for _ in range(len(case.claims)+2):
        grown = present | {dst for src,dst,_ in edges if src in present}
        if grown == present:
            return sorted(grown - {source})
        present = grown
    raise AssertionError("closure failed to stabilize")

def inspect_oasc(data: bytes):
    case = parse_case(data)
    if (len(case.claims),len(case.references),
        len(case.evidence_edges),len(case.inference_edges)) != (38,26,23,37):
        raise ValueError("OASC pinned structure changed unexpectedly")
    # 23 inference *relations* and 49 source->target edges.
    if len({eid for _,_,eid in case.inference_edges}) != 23:
        raise ValueError("OASC inference relationship count changed")
    differences = {}
    for ev in sorted({s for s,_,_ in case.evidence_edges}):
        a,b=bfs_consequences(case,ev),independent_fixpoint(case,ev)
        if a != b:
            raise AssertionError(f"independent oracle mismatch for {ev}")
        differences[ev] = a
    changed = differences["EV_63"]  # cited ISO 26262 assessment *placeholder*
    if changed != ["G1","G39","G4","G55"]:
        raise AssertionError(f"unexpected structural change impact: {changed}")
    if "G3" in changed or "G5" in changed:
        raise AssertionError("unrelated assurance branch falsely invalidated")
    # Actual assessment source bytes, signatures, check results are absent from XML.
    # The 26 artifact declarations are *labels and descriptions*, not evidence.
    return {
        "source_repo":OASC_REPO, "source_commit":OASC_COMMIT,
        "source_blob":OASC_BLOB,"source_sha256":case.source_hash,
        "source_kind":"AUTHENTIC_PUBLIC_SACM_TEMPLATE_NOT_KRY10",
        "nodes":{"claims":len(case.claims),"artifact_references":len(case.references),
                 "artifact_declarations":len(case.artifacts),
                 "evidence_links":len(case.evidence_edges),
                 "inference_relations":23,
                 "inference_source_edges":len(case.inference_edges)},
        "independent_oracle_agreement":len(differences),
        "simulated_changed_reference":"EV_63",
        "structurally_affected_claims":changed,
        "structurally_unaffected_claims":len(case.claims)-len(changed),
        "actual_evidence_files_authenticated":0,
        "root_safety_claim":"UNKNOWN",
        "derived_claim_truth":"UNKNOWN",
        "assurance_case_is_complete":"UNKNOWN",
        "Kry10_cart_integration":"NOT_TESTED",
        "comparative_review_efficiency":"UNKNOWN",
        "status":"WARRANTED_BOUNDED_STRUCTURE_ONLY"
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python sacm_transfer.py pinned_OASC.xml")
    from pathlib import Path
    print(json.dumps(inspect_oasc(Path(sys.argv[1]).read_bytes()),indent=2))
