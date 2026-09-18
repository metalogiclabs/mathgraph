from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from itertools import permutations
import json
from typing import Any, Mapping, Sequence

from .manifest import derive_dev_seed


FAMILY_IDS = ("extensional", "compositional", "reachability", "constraint_order")
INTERVENTIONS = (
    "edge_or_relation_deletion",
    "protected_order_reversal_perturbation",
    "scope_change",
    "constraint_change",
)

_PATTERN_TRIPLES: tuple[tuple[int, int, int], ...] = (
    (0, 0, 0),
    (0, 0, 1),
    (0, 1, 1),
    (0, 1, 0),
)


def _stable(value: Any) -> Any:
    if value is None or type(value) in (str, int, bool, float):
        return [type(value).__name__, value]
    if isinstance(value, Mapping):
        rows = [[_stable(k), _stable(v)] for k, v in value.items()]
        rows.sort(key=lambda row: json.dumps(row[0], sort_keys=True, separators=(",", ":")))
        return ["dict", rows]
    if isinstance(value, (tuple, list, set, frozenset)):
        rows = [_stable(v) for v in value]
        if isinstance(value, (set, frozenset)):
            rows.sort(key=lambda row: json.dumps(row, sort_keys=True, separators=(",", ":")))
        return [type(value).__name__, rows]
    if hasattr(value, "__dict__"):
        return [type(value).__name__, _stable(vars(value))]
    raise ValueError(f"unsupported value for canonical digest: {type(value).__name__}")


def digest(value: Any) -> str:
    payload = json.dumps(_stable(value), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def _eq_signature(values: Sequence[str]) -> tuple[int, int, int]:
    if len(values) != 3:
        raise ValueError("B capability requires exactly three local observations")
    a, b, c = tuple(str(v) for v in values)
    return (int(a == b), int(b == c), int(a == c))


SIGNATURE_CLASSES: tuple[tuple[int, int, int], ...] = tuple(
    _eq_signature(tuple(str(bit) for bit in pattern)) for pattern in _PATTERN_TRIPLES
)
if len(set(SIGNATURE_CLASSES)) != 4:
    raise AssertionError("equality-pattern carrier must contain four distinct classes")


@dataclass(frozen=True)
class BWorld:
    world_index: int
    seed_digest: str
    baseline_patterns: tuple[int, int, int, int]

    @property
    def world_digest(self) -> str:
        return digest(("abgp-b-equality-world-v1", self.world_index, self.seed_digest, self.baseline_patterns))


def make_world(world_index: int, channel: str = "primary") -> BWorld:
    if type(world_index) is not int or world_index < 0:
        raise ValueError("world_index must be a nonnegative integer")
    seed = derive_dev_seed(
        "B", f"independent-latent-world|{channel}", world_index, "abgp-b-equality-world-v1"
    )
    order = tuple(
        sorted(range(4), key=lambda p: sha256(f"{seed}|pattern|{p}".encode("utf-8")).hexdigest())
    )
    return BWorld(world_index=world_index, seed_digest=seed, baseline_patterns=order)


def _patterns_for(world: BWorld, intervention: str) -> tuple[int, int, int, int]:
    base = world.baseline_patterns
    if intervention == "baseline":
        return base
    if intervention == "edge_or_relation_deletion":
        return (base[1], base[0], base[2], base[3])
    if intervention == "protected_order_reversal_perturbation":
        return tuple(3 - p for p in base)  # type: ignore[return-value]
    if intervention == "scope_change":
        return (base[2], base[1], base[0], base[3])
    if intervention == "constraint_change":
        return tuple((p + 1) % 4 for p in base)  # type: ignore[return-value]
    raise ValueError(f"unknown B intervention: {intervention}")


_FAMILY_META: dict[str, dict[str, Any]] = {
    "extensional": {
        "primitive_count": 3,
        "primitive_arities": (3,),
        "serialization_schema": "extensional-independent-rows-v1",
        "inference_route": "group_rows_by_action_then_position",
    },
    "compositional": {
        "primitive_count": 4,
        "primitive_arities": (1, 2),
        "serialization_schema": "compositional-independent-tree-v1",
        "inference_route": "unfold_action_terms_then_bind_positions",
    },
    "reachability": {
        "primitive_count": 5,
        "primitive_arities": (2, 3),
        "serialization_schema": "reachability-independent-hypergraph-v1",
        "inference_route": "follow_action_position_value_hyperedges",
    },
    "constraint_order": {
        "primitive_count": 6,
        "primitive_arities": (1, 3, 4),
        "serialization_schema": "constraint-independent-set-v1",
        "inference_route": "solve_local_holds_constraints",
    },
}


@dataclass(frozen=True)
class GeneratedGrammar:
    family_id: str
    world_index: int
    role: str
    seed_digest: str
    surface_symbols: tuple[str, ...]
    primitives: tuple[str, ...]
    primitive_arities: tuple[int, ...]
    serialization_schema: str
    inference_route: str
    action_tokens: tuple[str, str, str, str]
    position_tokens: tuple[str, str, str]
    value_tokens: tuple[str, str]

    @property
    def grammar_digest(self) -> str:
        return digest(
            (
                "generated-grammar-v1",
                self.family_id,
                self.world_index,
                self.role,
                self.seed_digest,
                self.surface_symbols,
                self.primitives,
                self.primitive_arities,
                self.serialization_schema,
                self.inference_route,
            )
        )

    def encode(self, world: BWorld, intervention: str) -> Any:
        patterns = _patterns_for(world, intervention)
        triples = {
            self.action_tokens[slot]: tuple(
                self.value_tokens[bit] for bit in _PATTERN_TRIPLES[patterns[slot]]
            )
            for slot in range(4)
        }
        if self.family_id == "extensional":
            rows = []
            for action in self.action_tokens:
                for position, value in zip(self.position_tokens, triples[action]):
                    rows.append((self.primitives[0], action, position, value))
            return tuple(rows)
        if self.family_id == "compositional":
            return (
                self.primitives[0],
                tuple(
                    (
                        action,
                        tuple(
                            (self.primitives[1], position, value)
                            for position, value in zip(self.position_tokens, triples[action])
                        ),
                    )
                    for action in self.action_tokens
                ),
            )
        if self.family_id == "reachability":
            arcs = tuple(
                (self.primitives[0], action, position, value)
                for action in self.action_tokens
                for position, value in zip(self.position_tokens, triples[action])
            )
            return {
                "root": self.primitives[1],
                "action_nodes": self.action_tokens,
                "position_nodes": self.position_tokens,
                "value_nodes": self.value_tokens,
                "arcs": arcs,
            }
        if self.family_id == "constraint_order":
            return frozenset(
                (
                    self.primitives[0],
                    action,
                    position,
                    value,
                    self.primitives[1],
                )
                for action in self.action_tokens
                for position, value in zip(self.position_tokens, triples[action])
            )
        raise AssertionError("unreachable grammar family")

    def decode(self, representation: Any) -> dict[str, tuple[str, str, str]]:
        rows: list[tuple[str, str, str]] = []
        if self.family_id == "extensional":
            for row in tuple(representation):
                if len(row) != 4 or row[0] != self.primitives[0]:
                    raise ValueError("invalid extensional representation")
                rows.append((str(row[1]), str(row[2]), str(row[3])))
        elif self.family_id == "compositional":
            if not isinstance(representation, tuple) or len(representation) != 2 or representation[0] != self.primitives[0]:
                raise ValueError("invalid compositional representation")
            for action, fragments in representation[1]:
                for fragment in fragments:
                    if len(fragment) != 3 or fragment[0] != self.primitives[1]:
                        raise ValueError("invalid compositional fragment")
                    rows.append((str(action), str(fragment[1]), str(fragment[2])))
        elif self.family_id == "reachability":
            if not isinstance(representation, dict) or representation.get("root") != self.primitives[1]:
                raise ValueError("invalid reachability representation")
            for row in representation.get("arcs", ()):
                if len(row) != 4 or row[0] != self.primitives[0]:
                    raise ValueError("invalid reachability arc")
                rows.append((str(row[1]), str(row[2]), str(row[3])))
        elif self.family_id == "constraint_order":
            for row in representation:
                if len(row) != 5 or row[0] != self.primitives[0] or row[4] != self.primitives[1]:
                    raise ValueError("invalid constraint representation")
                rows.append((str(row[1]), str(row[2]), str(row[3])))
        else:
            raise AssertionError("unreachable grammar family")

        by_action: dict[str, dict[str, str]] = {action: {} for action in self.action_tokens}
        for action, position, value in rows:
            if action not in by_action or position not in self.position_tokens or value not in self.value_tokens:
                raise ValueError("representation contains out-of-grammar symbol")
            if position in by_action[action]:
                raise ValueError("duplicate action-position observation")
            by_action[action][position] = value
        result: dict[str, tuple[str, str, str]] = {}
        for action in self.action_tokens:
            if set(by_action[action]) != set(self.position_tokens):
                raise ValueError("incomplete action observation")
            result[action] = tuple(by_action[action][position] for position in self.position_tokens)  # type: ignore[assignment]
        return result

    def protected_order(self, world: BWorld, intervention: str) -> tuple[str, str, str, str]:
        patterns = _patterns_for(world, intervention)
        slots = sorted(range(4), key=lambda slot: patterns[slot])
        return tuple(self.action_tokens[slot] for slot in slots)  # type: ignore[return-value]


def make_grammar(family_id: str, world_index: int, role: str) -> GeneratedGrammar:
    if family_id not in FAMILY_IDS:
        raise ValueError(f"unknown B grammar family: {family_id}")
    if not role:
        raise ValueError("grammar role is required")
    seed = derive_dev_seed(
        "B", f"independent-grammar|{family_id}|{role}", world_index, "abgp-b-independent-grammar-v1"
    )
    prefix = f"{family_id[:2]}_{seed[:12]}"
    actions = tuple(f"{prefix}_a{i}" for i in range(4))
    positions = tuple(f"{prefix}_p{i}" for i in range(3))
    values = tuple(f"{prefix}_v{i}" for i in range(2))
    meta = _FAMILY_META[family_id]
    primitives = tuple(f"{prefix}_op{i}" for i in range(int(meta["primitive_count"])))
    surfaces = tuple(actions + positions + values)
    return GeneratedGrammar(
        family_id=family_id,
        world_index=world_index,
        role=role,
        seed_digest=seed,
        surface_symbols=surfaces,
        primitives=primitives,
        primitive_arities=tuple(meta["primitive_arities"]),
        serialization_schema=str(meta["serialization_schema"]),
        inference_route=str(meta["inference_route"]),
        action_tokens=actions,  # type: ignore[arg-type]
        position_tokens=positions,  # type: ignore[arg-type]
        value_tokens=values,  # type: ignore[arg-type]
    )


def _signature_map(decoded: Mapping[str, Sequence[str]]) -> dict[str, tuple[int, int, int]]:
    return {str(action): _eq_signature(values) for action, values in decoded.items()}


def behavioral_signatures(decoded: Mapping[str, Sequence[str]]) -> tuple[tuple[int, int, int], ...]:
    return tuple(sorted(_signature_map(decoded).values()))


@dataclass(frozen=True)
class EqualityCapability:
    rank_by_signature: tuple[tuple[tuple[int, int, int], int], ...]

    @property
    def mapping(self) -> dict[tuple[int, int, int], int]:
        return dict(self.rank_by_signature)

    @property
    def capability_digest(self) -> str:
        return digest(("equality-pattern-capability-v1", self.rank_by_signature))

    def order(self, decoded: Mapping[str, Sequence[str]]) -> tuple[str, ...]:
        signatures = _signature_map(decoded)
        ranks = self.mapping
        if set(signatures.values()) != set(SIGNATURE_CLASSES):
            raise ValueError("target representation does not contain the complete equality-pattern carrier")
        return tuple(sorted(signatures, key=lambda action: (ranks[signatures[action]], action)))


def _candidate_capabilities() -> tuple[EqualityCapability, ...]:
    result = []
    for rank_assignment in permutations(range(4)):
        result.append(
            EqualityCapability(
                tuple((signature, rank) for signature, rank in zip(SIGNATURE_CLASSES, rank_assignment))
            )
        )
    return tuple(result)


def learn_capability(
    decoded_source: Mapping[str, Sequence[str]],
    protected_source_order: Sequence[str],
) -> tuple[EqualityCapability, int, int]:
    signatures = _signature_map(decoded_source)
    order = tuple(str(action) for action in protected_source_order)
    if set(order) != set(signatures) or len(order) != 4:
        raise ValueError("source protected order must cover exactly the represented actions")
    candidates = _candidate_capabilities()
    survivors = tuple(
        candidate
        for candidate in candidates
        if all(candidate.mapping[signatures[action]] == rank for rank, action in enumerate(order))
    )
    if len(survivors) != 1:
        raise ValueError(f"source acquisition did not identify a unique behavioral class: {len(survivors)}")
    return survivors[0], len(candidates), len(survivors)


def _wrong_class(capability: EqualityCapability) -> EqualityCapability:
    return EqualityCapability(
        tuple((signature, (rank + 1) % 4) for signature, rank in capability.rank_by_signature)
    )


def _old_bisimulation_partition(decoded: Mapping[str, Sequence[str]]) -> tuple[tuple[str, ...], ...]:
    # Frozen old language sees an action with three terminal observations, but
    # cannot observe token identity across positions. Every action is therefore
    # bisimilar in this old transition language.
    return (tuple(sorted(str(action) for action in decoded)),)


def _old_bisimulation_bayes_order(decoded: Mapping[str, Sequence[str]]) -> tuple[str, ...]:
    # Exact uniform posterior over the 4! orders inside the single old-bisim class.
    # Under all-four 0/1 utility every order ties, so deterministic lexical tie-break.
    return tuple(sorted(str(action) for action in decoded))


def _grammar_independence(source: GeneratedGrammar, target: GeneratedGrammar) -> bool:
    return (
        source.family_id != target.family_id
        and set(source.surface_symbols).isdisjoint(target.surface_symbols)
        and set(source.primitives).isdisjoint(target.primitives)
        and len(source.primitives) != len(target.primitives)
        and source.primitive_arities != target.primitive_arities
        and source.serialization_schema != target.serialization_schema
        and source.inference_route != target.inference_route
        and source.seed_digest != target.seed_digest
    )


def run_b_direction(acquisition_family: str, transfer_family: str, world_index: int) -> dict[str, Any]:
    if acquisition_family == transfer_family:
        raise ValueError("B requires an ordered cross-grammar direction")
    direction = f"{acquisition_family}->{transfer_family}"
    world = make_world(world_index, channel=f"primary|{direction}")
    source = make_grammar(acquisition_family, world_index, f"{direction}|source")
    target = make_grammar(transfer_family, world_index, f"{direction}|target")
    if not _grammar_independence(source, target):
        raise AssertionError("generated source/target grammars failed independence contract")

    source_representation = source.encode(world, "baseline")
    source_decoded = source.decode(source_representation)
    source_order = source.protected_order(world, "baseline")
    capability, candidate_count, survivor_count = learn_capability(source_decoded, source_order)

    intervention_results = []
    target_digests = []
    target_baseline_decoded: dict[str, tuple[str, str, str]] | None = None
    for intervention in INTERVENTIONS:
        representation = target.encode(world, intervention)
        decoded = target.decode(representation)
        if target_baseline_decoded is None:
            target_baseline_decoded = decoded
        predicted = capability.order(decoded)
        expected = target.protected_order(world, intervention)
        target_digests.append(digest(representation))
        intervention_results.append(
            {
                "intervention": intervention,
                "predicted_order": list(predicted),
                "protected_order": list(expected),
                "agreement": predicted == expected,
            }
        )
    treatment_success = int(all(row["agreement"] for row in intervention_results))

    wrong = _wrong_class(capability)
    wrong_agreements = []
    old_agreements = []
    for intervention in INTERVENTIONS:
        decoded = target.decode(target.encode(world, intervention))
        expected = target.protected_order(world, intervention)
        wrong_agreements.append(wrong.order(decoded) == expected)
        old_agreements.append(_old_bisimulation_bayes_order(decoded) == expected)
    wrong_success = int(all(wrong_agreements))
    old_success = int(all(old_agreements))

    shuffled_world = make_world(world_index, channel=f"shuffled|{direction}")
    # Preserve source observations and rank marginals while breaking their coupling
    # using an independently seeded, guaranteed non-identity cyclic permutation.
    shift = 1 + (int(shuffled_world.seed_digest[:8], 16) % 3)
    shuffled_order = source_order[shift:] + source_order[:shift]
    shuffled_capability, _, _ = learn_capability(source_decoded, shuffled_order)
    shuffled_agreements = []
    for intervention in INTERVENTIONS:
        decoded = target.decode(target.encode(world, intervention))
        expected = target.protected_order(world, intervention)
        shuffled_agreements.append(shuffled_capability.order(decoded) == expected)
    shuffled_success = int(all(shuffled_agreements))

    assert target_baseline_decoded is not None
    partition = _old_bisimulation_partition(target_baseline_decoded)
    signatures = _signature_map(target_baseline_decoded)
    protected = target.protected_order(world, "baseline")
    protected_rank = {action: rank for rank, action in enumerate(protected)}
    separation = any(
        signatures[left] != signatures[right] and protected_rank[left] != protected_rank[right]
        for i, left in enumerate(target.action_tokens)
        for right in target.action_tokens[i + 1 :]
    )

    return {
        "schema": "abgp.executed-b-direction.v1",
        "mode": "DEV_MECHANISM_ONLY",
        "acquisition_family": acquisition_family,
        "transfer_family": transfer_family,
        "world_index": world_index,
        "latent_world_digest": world.world_digest,
        "source_grammar_digest": source.grammar_digest,
        "target_grammar_digest": target.grammar_digest,
        "source_representation_digest": digest(source_representation),
        "target_representation_digests": target_digests,
        "source_target_surface_disjoint": set(source.surface_symbols).isdisjoint(target.surface_symbols),
        "no_primitive_dictionary": (
            set(source.primitives).isdisjoint(target.primitives)
            and len(source.primitives) != len(target.primitives)
        ),
        "grammar_independence": _grammar_independence(source, target),
        "candidate_capability_count": candidate_count,
        "surviving_capability_count": survivor_count,
        "retained_capability_digest": capability.capability_digest,
        "treatment_success": treatment_success,
        "wrong_class_success": wrong_success,
        "shuffled_coupling_success": shuffled_success,
        "old_bisimulation_bayes_success": old_success,
        "old_bisimulation_class_count": len(partition),
        "bisimulation_separation_witness": separation,
        "intervention_results": intervention_results,
        "control_execution": {
            "wrong_class_candidate": wrong.capability_digest,
            "shuffled_source_world_digest": shuffled_world.world_digest,
            "shuffled_capability_digest": shuffled_capability.capability_digest,
            "old_bisimulation_partition": [list(group) for group in partition],
            "old_control_information_boundary": (
                "same raw target representation; frozen old transition language omits cross-position token co-reference"
            ),
        },
        "confirmatory_namespace_used": False,
    }


def run_b_batch(worlds_per_direction: int) -> list[dict[str, Any]]:
    if type(worlds_per_direction) is not int or worlds_per_direction <= 0:
        raise ValueError("worlds_per_direction must be positive")
    return [
        run_b_direction(source, target, world_index)
        for source, target in permutations(FAMILY_IDS, 2)
        for world_index in range(worlds_per_direction)
    ]
