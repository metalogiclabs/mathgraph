"""Typed boundary claims over the existing qualified-evidence resolver.

This module checks identity and applicability, not the truth of an obligation.
Only a trusted method-specific adapter may construct a Receipt for this API.
An arbitrary status string, GitHub comment, or self-hash is not admission.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Mapping, Sequence

from .warrant_resolution import Claim, Receipt, ResolutionSet, Route, resolve_graph

_HEX40 = re.compile(r"^[a-fA-F0-9]{40}$")
_HEX64 = re.compile(r"^[a-fA-F0-9]{64}$")
_ROLES = frozenset(("source", "obligation", "relation", "verifier", "evidence"))
_METHODS = frozenset(("formal", "native"))


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _require_nonempty(*values: str) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("MISSING_BOUNDARY_IDENTITY")


def _require_sha256(value: str) -> None:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise ValueError("INVALID_SHA256")


@dataclass(frozen=True)
class Subject:
    repository: str
    revision: str
    source_sha256: str

    def __post_init__(self):
        _require_nonempty(self.repository)
        if not isinstance(self.revision, str) or _HEX40.fullmatch(self.revision) is None:
            raise ValueError("INVALID_SOURCE_REVISION")
        _require_sha256(self.source_sha256)


@dataclass(frozen=True)
class Obligation:
    id: str
    statement: str
    authority: str
    authority_sha256: str

    def __post_init__(self):
        _require_nonempty(self.id, self.statement, self.authority)
        _require_sha256(self.authority_sha256)


@dataclass(frozen=True)
class Relation:
    kind: str
    statement: str
    parameters: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        _require_nonempty(self.kind, self.statement)
        object.__setattr__(self, "parameters", tuple(tuple(x) for x in self.parameters))
        if any(len(x) != 2 or not all(isinstance(v, str) and v for v in x)
               for x in self.parameters):
            raise ValueError("INVALID_RELATION_PARAMETERS")
        if len({x[0] for x in self.parameters}) != len(self.parameters):
            raise ValueError("DUPLICATE_RELATION_PARAMETERS")


@dataclass(frozen=True)
class Verification:
    method: str
    verifier_id: str
    policy_sha256: str
    assumptions: tuple[str, ...]
    receipt_id: str

    def __post_init__(self):
        if self.method not in _METHODS:
            raise ValueError("UNKNOWN_VERIFICATION_METHOD")
        _require_nonempty(self.verifier_id, self.receipt_id)
        _require_sha256(self.policy_sha256)
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        if any(not isinstance(x, str) or not x for x in self.assumptions):
            raise ValueError("INVALID_ASSUMPTIONS")


@dataclass(frozen=True)
class Conclusion:
    status: str
    limits: tuple[str, ...]

    def __post_init__(self):
        if self.status not in ("SUPPORTED", "REJECTED", "UNKNOWN"):
            raise ValueError("INVALID_STATUS")
        object.__setattr__(self, "limits", tuple(self.limits))
        if not self.limits or any(not isinstance(x, str) or not x for x in self.limits):
            raise ValueError("UNBOUNDED_CONCLUSION")


@dataclass(frozen=True)
class Dependency:
    role: str
    key: str
    sha256: str

    def __post_init__(self):
        if self.role not in _ROLES:
            raise ValueError("INVALID_DEPENDENCY_ROLE")
        _require_nonempty(self.key)
        _require_sha256(self.sha256)


def required_dependencies(
    subject: Subject, obligation: Obligation, relation: Relation,
    verification: Verification,
) -> tuple[Dependency, ...]:
    """Freeze the four identity planes, independent of the result label."""
    return (
        Dependency("source", "source:" + subject.repository, _digest(asdict(subject))),
        Dependency("obligation", "obligation:" + subject.repository + ":" + obligation.id,
                   _digest(asdict(obligation))),
        Dependency("relation", "relation:" + subject.repository + ":" + obligation.id,
                   _digest(asdict(relation))),
        Dependency("verifier", "verifier:" + subject.repository + ":" + verification.verifier_id,
                   _digest({
                       "method": verification.method,
                       "verifier_id": verification.verifier_id,
                       "policy_sha256": verification.policy_sha256,
                       "assumptions": verification.assumptions,
                   })),
    )


@dataclass(frozen=True)
class BoundaryWarrant:
    subject: Subject
    obligation: Obligation
    relation: Relation
    verification: Verification
    conclusion: Conclusion
    dependencies: tuple[Dependency, ...]

    def __post_init__(self):
        for key, typ in (
            ("subject", Subject), ("obligation", Obligation), ("relation", Relation),
            ("verification", Verification), ("conclusion", Conclusion),
        ):
            if not isinstance(getattr(self, key), typ):
                raise ValueError("INVALID_BOUNDARY_ELEMENT:" + key)
        object.__setattr__(self, "dependencies", tuple(self.dependencies))
        if any(not isinstance(dep, Dependency) for dep in self.dependencies):
            raise ValueError("INVALID_DEPENDENCY")
        names = [dep.key for dep in self.dependencies]
        if len(names) != len(set(names)):
            raise ValueError("DUPLICATE_DEPENDENCY")
        expected = required_dependencies(
            self.subject, self.obligation, self.relation, self.verification,
        )
        supplied = {dep.key: dep for dep in self.dependencies}
        for dep in expected:
            if dep.key not in supplied:
                raise ValueError("MISSING_REQUIRED_DEPENDENCY")
            if supplied[dep.key] != dep:
                raise ValueError("DEPENDENCY_IDENTITY_MISMATCH")
        if any(dep.role != "evidence" for dep in self.dependencies if dep.key not in
               {x.key for x in expected}):
            raise ValueError("UNQUALIFIED_EXTRA_DEPENDENCY")


def scope_identity(warrant: BoundaryWarrant) -> str:
    """Meaning-bearing scope; outcome labels and replay IDs do not grant authority."""
    if not isinstance(warrant, BoundaryWarrant):
        raise ValueError("INVALID_BOUNDARY_WARRANT")
    return _digest({
        "subject": asdict(warrant.subject),
        "obligation": asdict(warrant.obligation),
        "relation": asdict(warrant.relation),
        "method": warrant.verification.method,
        "verifier_id": warrant.verification.verifier_id,
        "policy_sha256": warrant.verification.policy_sha256,
        "assumptions": warrant.verification.assumptions,
        "dependencies": [asdict(dep) for dep in sorted(
            warrant.dependencies, key=lambda dep: (dep.role, dep.key))],
    })


def admitted_route(warrant: BoundaryWarrant, qualified_receipt: Receipt
                   ) -> tuple[Claim, Receipt, Route]:
    """Project caller-verified support into the existing bounded graph.

    This is a typed compatibility check, *not* an evidence authenticator.
    Callers must independently verify raw evidence using the method adapter;
    do not accept Receipt objects from API payloads or generated code.
    """
    if warrant.conclusion.status != "SUPPORTED":
        raise ValueError("NO_SUPPORTING_CONCLUSION")
    if (not isinstance(qualified_receipt, Receipt)
            or qualified_receipt.id != warrant.verification.receipt_id
            or qualified_receipt.kind != warrant.verification.method
            or qualified_receipt.scope != scope_identity(warrant)):
        raise ValueError("UNADMITTED_RECEIPT")
    claim = Claim("boundary:" + scope_identity(warrant), qualified_receipt.kind,
                  scope_identity(warrant))
    return claim, qualified_receipt, Route(claim.id, (qualified_receipt.id,))


def resolve_boundaries(
    admitted: Sequence[tuple[BoundaryWarrant, Receipt]],
    current_dependencies: Mapping[str, str],
) -> ResolutionSet:
    """Recompute selective applicability; a stale route is not a false claim.

    A missing, changed or untrusted *current* dependency withdraws its receipt
    from closure. The caller obtains current identities from its own authority
    adapters; this routine does not poll remote repositories.
    """
    projections = [admitted_route(w, receipt) for w, receipt in admitted]
    withdrawn = frozenset(
        receipt.id for w, receipt in admitted
        if any(current_dependencies.get(dep.key) != dep.sha256
               for dep in w.dependencies)
    )
    return resolve_graph(
        [claim for claim, _, _ in projections],
        [route for _, _, route in projections],
        [receipt for _, receipt, _ in projections],
        withdrawn=withdrawn,
    )
