"""Small content-addressed semantic graph kernel.

The module stores normalized meaning, typed relations, external warrants,
support lineage, epistemic status, and the grammar that normalized a surface.
It does not parse prover languages or create verifier authority. A normalizer
and an independently produced evidence receipt enter through explicit
boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from itertools import product
import json
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping

class Status(str, Enum):
    CANDIDATE = "CANDIDATE"
    WARRANTED = "WARRANTED"
    UNKNOWN = "UNKNOWN"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"
    CONFLICTED = "CONFLICTED"


class RelationKind(str, Enum):
    SAME_MEANING = "SAME_MEANING"
    IMPLIES = "IMPLIES"
    REFUTES = "REFUTES"


class UnsupportedGrammar(ValueError):
    """Raised by an external normalizer when it cannot represent a surface."""


def _check_canonical_value(value: Any, path: str = "value") -> None:
    """Reject values whose JSON meaning is ambiguous or non-portable."""

    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        raise TypeError(f"floating-point values are not canonical at {path}")
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise TypeError(f"canonical object keys must be strings at {path}")
            _check_canonical_value(nested, f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _check_canonical_value(nested, f"{path}[{index}]")
        return
    raise TypeError(f"not a canonical JSON value at {path}: {type(value)!r}")


def _canonical_digest(payload: Any) -> str:
    _check_canonical_value(payload)
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _canonical_value(nested) for key, nested in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical_value(nested) for nested in value]
    return value


def _canonical_bytes(value: Any) -> bytes:
    _check_canonical_value(value)
    return json.dumps(
        _canonical_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _content_id(value: Any, *, prefix: str) -> str:
    return f"{prefix}:{hashlib.sha256(_canonical_bytes(value)).hexdigest()}"


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(nested) for key, nested in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(nested) for nested in value)
    return value


@dataclass(frozen=True)
class Grammar:
    grammar_id: str
    version: str
    definition_digest: str

    def __post_init__(self) -> None:
        if not self.grammar_id or not self.version or not self.definition_digest:
            raise ValueError("grammar id, version, and definition digest are required")

    @property
    def id(self) -> str:
        return _content_id(
            {
                "grammar_id": self.grammar_id,
                "version": self.version,
                "definition_digest": self.definition_digest,
            },
            prefix="grammar",
        )


@dataclass(frozen=True)
class Object:
    """A semantic object identified by normalized meaning under one grammar."""

    grammar_id: str
    semantic_type: str
    normal_form: Any

    def __post_init__(self) -> None:
        if not self.grammar_id or not self.semantic_type:
            raise ValueError("object grammar_id and semantic_type are required")
        _check_canonical_value(self.normal_form, "normal_form")
        object.__setattr__(self, "normal_form", _freeze(self.normal_form))

    @property
    def identity_payload(self) -> dict[str, Any]:
        return {
            "grammar_id": self.grammar_id,
            "semantic_type": self.semantic_type,
            "normal_form": self.normal_form,
        }

    @property
    def id(self) -> str:
        return _content_id(self.identity_payload, prefix="object")


@dataclass(frozen=True)
class Unknown:
    grammar_id: str
    surface_digest: str
    reason: str = "UNKNOWN_UNSUPPORTED_GRAMMAR"
    status: Status = Status.UNKNOWN

    def __post_init__(self) -> None:
        if Status(self.status) is not Status.UNKNOWN:
            raise ValueError("an unsupported normalization result must remain UNKNOWN")
        object.__setattr__(self, "status", Status.UNKNOWN)

    @property
    def id(self) -> str:
        return _content_id(
            {
                "grammar_id": self.grammar_id,
                "surface_digest": self.surface_digest,
                "reason": self.reason,
                "status": self.status.value,
            },
            prefix="unknown",
        )


def normalize(
    surface: str | bytes,
    grammar: Grammar,
    normalizer: Callable[[str | bytes], Any],
    *,
    semantic_type: str = "claim",
) -> Object | Unknown:
    """Normalize one surface, returning typed UNKNOWN outside the grammar.

    ``normalizer`` is deliberately injected: prover syntax and mathematical
    parsing are adapter responsibilities, not part of this kernel.
    """

    if not callable(normalizer):
        raise TypeError("normalizer must be callable")
    raw = surface if isinstance(surface, bytes) else surface.encode("utf-8")
    try:
        normal_form = normalizer(surface)
    except UnsupportedGrammar:
        normal_form = None
    if normal_form is None:
        return Unknown(grammar.id, hashlib.sha256(raw).hexdigest())
    try:
        _check_canonical_value(normal_form, "normal_form")
    except TypeError:
        return Unknown(grammar.id, hashlib.sha256(raw).hexdigest())
    return Object(grammar.id, semantic_type, normal_form)


@dataclass(frozen=True)
class Relation:
    """A typed directed hyperedge; sources and targets are object IDs."""

    kind: RelationKind
    sources: tuple[str, ...]
    targets: tuple[str, ...]

    def __post_init__(self) -> None:
        kind = RelationKind(self.kind)
        if not self.sources or not self.targets:
            raise ValueError("a relation needs at least one source and target")
        if any(not value for value in (*self.sources, *self.targets)):
            raise ValueError("relation object IDs must be non-empty")
        sources = tuple(sorted(set(self.sources)))
        targets = tuple(sorted(set(self.targets)))
        if kind in {RelationKind.SAME_MEANING, RelationKind.REFUTES}:
            if len(sources) != 1 or len(targets) != 1:
                raise ValueError(f"{kind.value} is a binary relation in Core V0")
        if kind is RelationKind.SAME_MEANING and targets[0] < sources[0]:
            sources, targets = targets, sources
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "sources", sources)
        object.__setattr__(self, "targets", targets)

    @property
    def id(self) -> str:
        return _content_id(
            {
                "kind": self.kind.value,
                "sources": self.sources,
                "targets": self.targets,
            },
            prefix="relation",
        )


@dataclass(frozen=True)
class Support:
    """An independently revocable provenance/evidence dependency."""

    source_ref: str
    source_digest: str
    assumptions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_ref or not self.source_digest:
            raise ValueError("support source_ref and source_digest are required")
        if any(not value for value in self.assumptions):
            raise ValueError("support assumptions must be non-empty strings")
        object.__setattr__(self, "assumptions", tuple(sorted(set(self.assumptions))))

    @property
    def id(self) -> str:
        return _content_id(
            {
                "source_ref": self.source_ref,
                "source_digest": self.source_digest,
                "assumptions": self.assumptions,
            },
            prefix="support",
        )


@dataclass(frozen=True)
class EvidenceReceipt:
    """A digest-bound result emitted by an external verifier adapter.

    The receipt records authority; this data container does not itself replay
    the verifier or authenticate who produced the receipt.
    """

    subject_id: str
    subject_kind: str
    verifier: str
    boundary: str
    support_ids: tuple[str, ...]
    payload: Any
    evidence_digest: str
    outcome: Status

    def __post_init__(self) -> None:
        if not self.subject_id or not self.verifier or not self.boundary:
            raise ValueError("receipt subject, verifier, and boundary are required")
        if self.subject_kind not in {"object", "relation", "unknown"}:
            raise ValueError("receipt subject_kind must be object, relation, or unknown")
        object.__setattr__(self, "support_ids", tuple(sorted(set(self.support_ids))))
        object.__setattr__(self, "outcome", Status(self.outcome))
        _check_canonical_value(self.payload, "evidence payload")
        object.__setattr__(self, "payload", _freeze(self.payload))

    @classmethod
    def for_candidate(
        cls,
        candidate: Object | Relation | Unknown,
        *,
        verifier: str,
        support_ids: Iterable[str],
        boundary: str,
        payload: Any,
        outcome: Status = Status.WARRANTED,
    ) -> "EvidenceReceipt":
        subject_kind = (
            "object"
            if isinstance(candidate, Object)
            else "relation"
            if isinstance(candidate, Relation)
            else "unknown"
        )
        return cls(
            subject_id=candidate.id,
            subject_kind=subject_kind,
            verifier=verifier,
            boundary=boundary,
            support_ids=tuple(support_ids),
            payload=payload,
            evidence_digest=_canonical_digest(payload),
            outcome=outcome,
        )


@dataclass(frozen=True)
class Warrant:
    subject_id: str
    subject_kind: str
    status: Status
    support_ids: tuple[str, ...] = ()
    parent_warrant_ids: tuple[str, ...] = ()
    verifier: str = ""
    evidence_digest: str = ""
    boundary: str = ""
    rule_id: str = ""

    def __post_init__(self) -> None:
        if not self.subject_id or self.subject_kind not in {"object", "relation", "unknown"}:
            raise ValueError("warrant must name an object, relation, or unknown subject")
        object.__setattr__(self, "status", Status(self.status))
        object.__setattr__(self, "support_ids", tuple(sorted(set(self.support_ids))))
        object.__setattr__(
            self, "parent_warrant_ids", tuple(sorted(set(self.parent_warrant_ids)))
        )
        if self.status in {Status.WARRANTED, Status.REJECTED} and not (
            self.support_ids or self.parent_warrant_ids
        ):
            raise ValueError("a positive or negative warrant needs support or parent lineage")
        if self.rule_id and not self.parent_warrant_ids:
            raise ValueError("a derived warrant needs parent warrants")

    @property
    def id(self) -> str:
        return _content_id(
            {
                "subject_id": self.subject_id,
                "subject_kind": self.subject_kind,
                "status": self.status.value,
                "support_ids": self.support_ids,
                "parent_warrant_ids": self.parent_warrant_ids,
                "verifier": self.verifier,
                "evidence_digest": self.evidence_digest,
                "boundary": self.boundary,
                "rule_id": self.rule_id,
            },
            prefix="warrant",
        )


def verify(candidate: Object | Relation | Unknown, evidence: EvidenceReceipt) -> Warrant:
    """Bind a candidate to an independently produced verifier receipt."""

    if candidate.id != evidence.subject_id:
        raise ValueError("receipt subject does not match candidate")
    expected_kind = (
        "object"
        if isinstance(candidate, Object)
        else "relation"
        if isinstance(candidate, Relation)
        else "unknown"
    )
    if expected_kind != evidence.subject_kind:
        raise ValueError("receipt subject kind does not match candidate")
    if evidence.outcome not in {Status.WARRANTED, Status.REJECTED}:
        raise ValueError("receipt outcome must be WARRANTED or REJECTED")
    if _canonical_digest(evidence.payload) != evidence.evidence_digest:
        raise ValueError("evidence digest does not match receipt payload")
    if not evidence.support_ids:
        raise ValueError("external verifier receipt must cite at least one support")
    return Warrant(
        subject_id=candidate.id,
        subject_kind=expected_kind,
        status=evidence.outcome,
        support_ids=evidence.support_ids,
        verifier=evidence.verifier,
        evidence_digest=evidence.evidence_digest,
        boundary=evidence.boundary,
    )


@dataclass(frozen=True)
class GraphDelta:
    added_objects: tuple[str, ...] = ()
    added_relations: tuple[str, ...] = ()
    added_warrants: tuple[str, ...] = ()
    invalidated_warrants: tuple[str, ...] = ()


@dataclass(frozen=True)
class QueryResult:
    object_id: str
    status: Status
    relations: tuple[Relation, ...]
    warrants: tuple[Warrant, ...]


_IMPLIES_TRANSITIVE = "core-v0:implies-transitive@1"
_SAME_TRANSITIVE = "core-v0:same-meaning-transitive@1"
_SAME_SUBSTITUTION = "core-v0:same-meaning-substitution@1"
_MODUS_PONENS = "core-v0:modus-ponens@1"


class CoreGraph:
    """Mutable graph whose authority comes only from admitted warrants."""

    FORMAT = "mathgraph-core-v0"

    def __init__(
        self,
        *,
        grammars: Iterable[Grammar] = (),
        objects: Iterable[Object] = (),
        relations: Iterable[Relation] = (),
        unknowns: Iterable[Unknown] = (),
        supports: Iterable[Support] = (),
        warrants: Iterable[Warrant] = (),
        revoked_support_ids: Iterable[str] = (),
    ) -> None:
        self.grammars: dict[str, Grammar] = {}
        self.objects: dict[str, Object] = {}
        self.relations: dict[str, Relation] = {}
        self.unknowns: dict[str, Unknown] = {}
        self.supports: dict[str, Support] = {}
        self.warrants: dict[str, Warrant] = {}
        self.revoked_support_ids = set(revoked_support_ids)
        for grammar in grammars:
            self.add_grammar(grammar)
        for obj in objects:
            self.add_candidate(obj)
        for relation in relations:
            self.add_candidate(relation)
        for unknown in unknowns:
            self.add_unknown(unknown)
        for support in supports:
            self.add_support(support)
        for warrant in warrants:
            self.admit(warrant)

    def add_grammar(self, grammar: Grammar) -> None:
        existing = self.grammars.get(grammar.id)
        if existing is not None and existing != grammar:
            raise ValueError("grammar id collision")
        self.grammars[grammar.id] = grammar

    def add_candidate(self, candidate: Object | Relation) -> None:
        if isinstance(candidate, Object):
            if candidate.grammar_id not in self.grammars:
                raise ValueError("object refers to an unknown grammar")
            self.objects[candidate.id] = candidate
            return
        if not isinstance(candidate, Relation):
            raise TypeError("candidate must be an Object or Relation")
        missing = (set(candidate.sources) | set(candidate.targets)) - self.objects.keys()
        if missing:
            raise ValueError(f"relation refers to unknown objects: {sorted(missing)}")
        self.relations[candidate.id] = candidate

    def add_support(self, support: Support) -> None:
        self.supports[support.id] = support

    def add_unknown(self, unknown: Unknown) -> None:
        if unknown.grammar_id not in self.grammars:
            raise ValueError("unknown residual refers to an unknown grammar")
        self.unknowns[unknown.id] = unknown

    def admit(self, warrant: Warrant) -> GraphDelta:
        subjects = (
            self.objects
            if warrant.subject_kind == "object"
            else self.relations
            if warrant.subject_kind == "relation"
            else self.unknowns
        )
        if warrant.subject_id not in subjects:
            raise ValueError("warrant subject is not present as a candidate")
        if set(warrant.support_ids) - self.supports.keys():
            raise ValueError("warrant refers to unknown support")
        if set(warrant.parent_warrant_ids) - self.warrants.keys():
            raise ValueError("warrant refers to unknown parent warrant")
        if warrant.rule_id:
            if warrant.status is not Status.WARRANTED:
                raise ValueError("Core V0 derivation rules only produce WARRANTED results")
        elif warrant.status in {Status.WARRANTED, Status.REJECTED} and not warrant.support_ids:
            raise ValueError("externally verified warrants require direct support")
        if warrant.id in self.warrants:
            return GraphDelta()
        self.warrants[warrant.id] = warrant
        return GraphDelta(added_warrants=(warrant.id,))

    def _effective_warrant_status(self, warrant: Warrant) -> Status:
        if warrant.status not in {Status.WARRANTED, Status.REJECTED}:
            return warrant.status
        if set(warrant.support_ids) & self.revoked_support_ids:
            return Status.REVOKED
        if any(
            self._effective_warrant_status(self.warrants[parent]) is not Status.WARRANTED
            for parent in warrant.parent_warrant_ids
        ):
            return Status.REVOKED
        return warrant.status

    def status_of(self, subject_id: str) -> Status:
        if (
            subject_id not in self.objects
            and subject_id not in self.relations
            and subject_id not in self.unknowns
        ):
            raise KeyError(subject_id)
        attached = [w for w in self.warrants.values() if w.subject_id == subject_id]
        effective = [self._effective_warrant_status(w) for w in attached]
        if Status.WARRANTED in effective and Status.REJECTED in effective:
            return Status.CONFLICTED
        if Status.WARRANTED in effective:
            return Status.WARRANTED
        if Status.REJECTED in effective:
            return Status.REJECTED
        if Status.REVOKED in effective:
            return Status.REVOKED
        if Status.SUPERSEDED in effective:
            return Status.SUPERSEDED
        if attached:
            return effective[-1]
        if subject_id in self.unknowns or subject_id in self.objects:
            return Status.UNKNOWN
        return Status.CANDIDATE

    def _active_warrants(self, status: Status = Status.WARRANTED) -> tuple[Warrant, ...]:
        return tuple(
            warrant
            for warrant in self.warrants.values()
            if self._effective_warrant_status(warrant) is status
        )

    def _active_relations(self, kind: RelationKind | None = None) -> tuple[Relation, ...]:
        live_ids = {
            warrant.subject_id for warrant in self._active_warrants(Status.WARRANTED)
        }
        return tuple(
            relation
            for relation in self.relations.values()
            if relation.id in live_ids and (kind is None or relation.kind is kind)
        )

    def close(self) -> GraphDelta:
        """Close finite simple paths over externally warranted base relations.

        Derived warrants are retained as proof lineage, but never fed back as
        new premises. This makes closure finite even when the relation graph
        contains cycles and keeps each derived warrant tied to a concrete path.
        """

        old_relation_ids = set(self.relations)
        old_warrant_ids = set(self.warrants)
        base_warrants = tuple(
            warrant
            for warrant in self._active_warrants(Status.WARRANTED)
            if not warrant.rule_id
        )
        base_warrant_ids: dict[str, tuple[str, ...]] = {}
        for warrant in base_warrants:
            base_warrant_ids.setdefault(warrant.subject_id, ())
            base_warrant_ids[warrant.subject_id] += (warrant.id,)
        base_relations = {
            relation.id: relation
            for relation in self.relations.values()
            if relation.id in base_warrant_ids
        }
        equivalences = [
            relation
            for relation in base_relations.values()
            if relation.kind is RelationKind.SAME_MEANING
        ]
        equivalence_adjacency: dict[str, list[tuple[str, str]]] = {
            obj_id: [] for obj_id in self.objects
        }
        for relation in equivalences:
            left, right = relation.sources[0], relation.targets[0]
            equivalence_adjacency[left].append((right, relation.id))
            equivalence_adjacency[right].append((left, relation.id))
        for neighbors in equivalence_adjacency.values():
            neighbors.sort()

        # A shortest witnessed equality path is sufficient for substitution;
        # revocation reruns closure and can select another still-live path.
        for start in sorted(equivalence_adjacency):
            for target in sorted(equivalence_adjacency):
                path = self._shortest_path(start, target, equivalence_adjacency)
                if path is None or len(path) < 2:
                    continue
                relation = Relation(RelationKind.SAME_MEANING, (start,), (target,))
                self._derive(relation, _SAME_TRANSITIVE, path, base_warrant_ids)

        expanded: dict[str, list[tuple[str, str, tuple[str, ...]]]] = {
            obj_id: [] for obj_id in self.objects
        }
        for relation in base_relations.values():
            if relation.kind is not RelationKind.IMPLIES:
                continue
            if len(relation.sources) != 1 or len(relation.targets) != 1:
                continue
            original_source, original_target = relation.sources[0], relation.targets[0]
            source_aliases = sorted(equivalence_adjacency)
            target_aliases = source_aliases
            for source in source_aliases:
                source_path = self._shortest_path(
                    source, original_source, equivalence_adjacency
                )
                if source_path is None:
                    continue
                for target in target_aliases:
                    target_path = self._shortest_path(
                        original_target, target, equivalence_adjacency
                    )
                    if target_path is None or source == target:
                        continue
                    route = tuple(dict.fromkeys((*source_path, relation.id, *target_path)))
                    expanded[source].append((target, relation.id, route))
        for edges in expanded.values():
            edges.sort(key=lambda edge: (edge[0], edge[2]))

        for source in sorted(expanded):
            self._close_implication_paths(source, expanded, base_warrant_ids)

        self._close_object_consequences(
            tuple(w for w in base_warrants if w.subject_kind == "object")
        )

        return GraphDelta(
            added_relations=tuple(sorted(set(self.relations) - old_relation_ids)),
            added_warrants=tuple(sorted(set(self.warrants) - old_warrant_ids)),
        )

    def _close_object_consequences(self, seed_warrants: tuple[Warrant, ...]) -> None:
        implications = [
            relation
            for relation in self._active_relations(RelationKind.IMPLIES)
            if len(relation.sources) == 1 and len(relation.targets) == 1
        ]
        adjacency: dict[str, list[tuple[str, str]]] = {
            object_id: [] for object_id in self.objects
        }
        for relation in implications:
            adjacency[relation.sources[0]].append((relation.targets[0], relation.id))
        for rows in adjacency.values():
            rows.sort()
        warrant_options: dict[str, tuple[str, ...]] = {}
        for relation in implications:
            warrant_options[relation.id] = tuple(
                sorted(self._warrant_ids_for(relation.id))
            )

        for seed in seed_warrants:
            start = seed.subject_id

            def visit(
                node: str,
                visited: frozenset[str],
                route: tuple[str, ...],
            ) -> None:
                for target, relation_id in adjacency.get(node, ()):
                    if target in visited:
                        continue
                    next_route = (*route, relation_id)
                    choices = [warrant_options[edge_id] for edge_id in next_route]
                    if all(choices):
                        for selected in product(*choices):
                            parents = tuple(sorted({seed.id, *selected}))
                            warrant = Warrant(
                                subject_id=target,
                                subject_kind="object",
                                status=Status.WARRANTED,
                                parent_warrant_ids=parents,
                                evidence_digest=_canonical_digest(
                                    {
                                        "rule": _MODUS_PONENS,
                                        "route_relations": next_route,
                                        "seed_warrant": seed.id,
                                        "parents_by_relation": selected,
                                    }
                                ),
                                boundary="mathgraph-core-v0/relation-algebra",
                                rule_id=_MODUS_PONENS,
                            )
                            if warrant.id not in self.warrants:
                                self.admit(warrant)
                    visit(target, visited | {target}, next_route)

            visit(start, frozenset({start}), ())

    @staticmethod
    def _shortest_path(
        start: str,
        target: str,
        adjacency: Mapping[str, list[tuple[str, str]]],
    ) -> tuple[str, ...] | None:
        if start == target:
            return ()
        queue: list[tuple[str, tuple[str, ...], frozenset[str]]] = [
            (start, (), frozenset({start}))
        ]
        cursor = 0
        while cursor < len(queue):
            node, path, visited = queue[cursor]
            cursor += 1
            for neighbor, relation_id in adjacency.get(node, ()):
                if neighbor in visited:
                    continue
                next_path = (*path, relation_id)
                if neighbor == target:
                    return next_path
                queue.append((neighbor, next_path, visited | {neighbor}))
        return None

    def _close_implication_paths(
        self,
        start: str,
        adjacency: Mapping[str, list[tuple[str, str, tuple[str, ...]]]],
        base_warrant_ids: Mapping[str, tuple[str, ...]],
    ) -> None:
        def visit(
            node: str,
            visited: frozenset[str],
            route_relation_ids: tuple[str, ...],
            route_edges: int,
        ) -> None:
            for target, _edge_id, edge_support_path in adjacency.get(node, ()):
                if target in visited:
                    continue
                next_route = (*route_relation_ids, *edge_support_path)
                next_edges = route_edges + 1
                relation = Relation(RelationKind.IMPLIES, (start,), (target,))
                if next_edges >= 2 or relation.id not in base_warrant_ids:
                    if start != target:
                        self._derive(
                            relation,
                            _SAME_SUBSTITUTION
                            if any(
                                self.relations[item].kind is RelationKind.SAME_MEANING
                                for item in next_route
                            )
                            else _IMPLIES_TRANSITIVE,
                            next_route,
                            base_warrant_ids,
                        )
                visit(target, visited | {target}, next_route, next_edges)

        visit(start, frozenset({start}), (), 0)

    def _derive(
        self,
        relation: Relation,
        rule_id: str,
        route_relation_ids: tuple[str, ...],
        base_warrant_ids: Mapping[str, tuple[str, ...]],
    ) -> None:
        if not route_relation_ids:
            return
        unique_route_ids = tuple(dict.fromkeys(route_relation_ids))
        alternatives = [base_warrant_ids.get(relation_id, ()) for relation_id in unique_route_ids]
        if any(not options for options in alternatives):
            return
        self.add_candidate(relation)
        for chosen in product(*alternatives):
            parents = tuple(sorted(set(chosen)))
            if not parents:
                continue
            evidence_digest = _canonical_digest(
                {
                    "rule": rule_id,
                    "route_relations": route_relation_ids,
                    "parents_by_relation": chosen,
                }
            )
            warrant = Warrant(
                subject_id=relation.id,
                subject_kind="relation",
                status=Status.WARRANTED,
                parent_warrant_ids=parents,
                evidence_digest=evidence_digest,
                boundary="mathgraph-core-v0/relation-algebra",
                rule_id=rule_id,
            )
            self.admit(warrant)

    def _warrant_ids_for(self, relation_id: str) -> set[str]:
        return {
            warrant.id
            for warrant in self._active_warrants(Status.WARRANTED)
            if warrant.subject_id == relation_id
        }

    def _alias_parent_warrants(
        self,
        sources: set[str],
        targets: set[str],
        equivalences: Iterable[Relation],
    ) -> set[str]:
        ids: set[str] = set()
        used = set(sources) | set(targets)
        for relation in equivalences:
            if relation.sources[0] in used or relation.targets[0] in used:
                ids |= self._warrant_ids_for(relation.id)
        return ids

    def revoke(self, support_id: str) -> GraphDelta:
        if support_id not in self.supports:
            raise KeyError(support_id)
        before = {w.id for w in self._active_warrants(Status.WARRANTED)}
        self.revoked_support_ids.add(support_id)
        self.close()
        after = {w.id for w in self._active_warrants(Status.WARRANTED)}
        return GraphDelta(invalidated_warrants=tuple(sorted(before - after)))

    def query(self, object_id: str) -> QueryResult:
        if object_id not in self.objects:
            raise KeyError(object_id)
        self.close()
        outgoing = tuple(
            sorted(
                (
                    relation
                    for relation in self._active_relations()
                    if object_id in relation.sources
                ),
                key=lambda relation: relation.id,
            )
        )
        relevant_ids = {relation.id for relation in outgoing}
        warrants = tuple(
            sorted(
                (
                    warrant
                    for warrant in self._active_warrants(Status.WARRANTED)
                    if warrant.subject_id in relevant_ids
                    or warrant.subject_id == object_id
                ),
                key=lambda warrant: warrant.id,
            )
        )
        return QueryResult(object_id, self.status_of(object_id), outgoing, warrants)

    def to_mg(self) -> bytes:
        document = {
            "format": self.FORMAT,
            "grammars": [
                {
                    "id": item.id,
                    "grammar_id": item.grammar_id,
                    "version": item.version,
                    "definition_digest": item.definition_digest,
                }
                for item in sorted(self.grammars.values(), key=lambda value: value.id)
            ],
            "objects": [
                {"id": item.id, **item.identity_payload}
                for item in sorted(self.objects.values(), key=lambda value: value.id)
            ],
            "relations": [
                {
                    "id": item.id,
                    "kind": item.kind.value,
                    "sources": item.sources,
                    "targets": item.targets,
                }
                for item in sorted(self.relations.values(), key=lambda value: value.id)
            ],
            "unknowns": [
                {
                    "id": item.id,
                    "grammar_id": item.grammar_id,
                    "surface_digest": item.surface_digest,
                    "reason": item.reason,
                    "status": item.status.value,
                }
                for item in sorted(self.unknowns.values(), key=lambda value: value.id)
            ],
            "supports": [
                {
                    "id": item.id,
                    "source_ref": item.source_ref,
                    "source_digest": item.source_digest,
                    "assumptions": item.assumptions,
                    "status": (
                        Status.REVOKED.value
                        if item.id in self.revoked_support_ids
                        else Status.WARRANTED.value
                    ),
                }
                for item in sorted(self.supports.values(), key=lambda value: value.id)
            ],
            "warrants": [
                {
                    "id": item.id,
                    "subject_id": item.subject_id,
                    "subject_kind": item.subject_kind,
                    "status": item.status.value,
                    "support_ids": item.support_ids,
                    "parent_warrant_ids": item.parent_warrant_ids,
                    "verifier": item.verifier,
                    "evidence_digest": item.evidence_digest,
                    "boundary": item.boundary,
                    "rule_id": item.rule_id,
                }
                for item in sorted(self.warrants.values(), key=lambda value: value.id)
            ],
        }
        return _canonical_bytes(document)

    @classmethod
    def from_mg(cls, encoded: bytes) -> "CoreGraph":
        try:
            document = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid .mg document") from exc
        if document.get("format") != cls.FORMAT:
            raise ValueError("unsupported .mg format")
        if _canonical_bytes(document) != encoded:
            raise ValueError(".mg document is not canonically encoded")
        grammars = [
            Grammar(row["grammar_id"], row["version"], row["definition_digest"])
            for row in document["grammars"]
        ]
        grammar_by_id = {grammar.id: grammar for grammar in grammars}
        if any(row["id"] not in grammar_by_id for row in document["grammars"]):
            raise ValueError("grammar identity mismatch")
        objects = [
            Object(row["grammar_id"], row["semantic_type"], row["normal_form"])
            for row in document["objects"]
        ]
        if any(row["id"] != item.id for row, item in zip(document["objects"], objects)):
            raise ValueError("object identity mismatch")
        relations = [
            Relation(RelationKind(row["kind"]), tuple(row["sources"]), tuple(row["targets"]))
            for row in document["relations"]
        ]
        if any(row["id"] != item.id for row, item in zip(document["relations"], relations)):
            raise ValueError("relation identity mismatch")
        unknowns = [
            Unknown(
                grammar_id=row["grammar_id"],
                surface_digest=row["surface_digest"],
                reason=row["reason"],
                status=Status(row["status"]),
            )
            for row in document["unknowns"]
        ]
        if any(row["id"] != item.id for row, item in zip(document["unknowns"], unknowns)):
            raise ValueError("unknown identity mismatch")
        supports = [
            Support(row["source_ref"], row["source_digest"], tuple(row["assumptions"]))
            for row in document["supports"]
        ]
        if any(row["id"] != item.id for row, item in zip(document["supports"], supports)):
            raise ValueError("support identity mismatch")
        warrants = [
            Warrant(
                subject_id=row["subject_id"],
                subject_kind=row["subject_kind"],
                status=Status(row["status"]),
                support_ids=tuple(row["support_ids"]),
                parent_warrant_ids=tuple(row["parent_warrant_ids"]),
                verifier=row["verifier"],
                evidence_digest=row["evidence_digest"],
                boundary=row["boundary"],
                rule_id=row["rule_id"],
            )
            for row in document["warrants"]
        ]
        if any(row["id"] != item.id for row, item in zip(document["warrants"], warrants)):
            raise ValueError("warrant identity mismatch")
        revoked = [
            row["id"] for row in document["supports"] if row["status"] == Status.REVOKED.value
        ]
        graph = cls(
            grammars=grammars,
            objects=objects,
            relations=relations,
            unknowns=unknowns,
            supports=supports,
            warrants=warrants,
            revoked_support_ids=revoked,
        )
        if graph.to_mg() != encoded:
            raise ValueError(".mg document is not a valid canonical graph")
        return graph
