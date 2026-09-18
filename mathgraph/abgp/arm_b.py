from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from itertools import permutations
import json
from typing import Any, Sequence

from .dev_world import DevWorld, ProtectedAction
from .manifest import derive_dev_seed


_BASELINE = "baseline"
_INTERVENTIONS = (
    "edge_or_relation_deletion",
    "protected_order_reversal_perturbation",
    "scope_change",
    "constraint_change",
)


def _canonical_digest(value: Any) -> str:
    def stable(x: Any) -> Any:
        if x is None or type(x) in (str, int, bool, float):
            return [type(x).__name__, x]
        if isinstance(x, dict):
            rows = [[stable(k), stable(v)] for k, v in x.items()]
            return ["dict", sorted(rows, key=lambda row: json.dumps(row[0], sort_keys=True))]
        if isinstance(x, (tuple, list, set, frozenset)):
            rows = [stable(v) for v in x]
            if isinstance(x, (set, frozenset)):
                rows.sort(key=lambda row: json.dumps(row, sort_keys=True))
            return [type(x).__name__, rows]
        raise ValueError("unsupported B representation for canonical hashing")
    payload = json.dumps(stable(value), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def _base_order_from_hidden(hidden: int) -> tuple[int, ...]:
    slots = (0, 1, 2, 3)
    return slots[hidden:] + slots[:hidden]


def _apply_intervention(order: Sequence[int], intervention: str) -> tuple[int, ...]:
    base = tuple(int(x) for x in order)
    if intervention == _BASELINE:
        return base
    if intervention == "edge_or_relation_deletion":
        return base[:3]
    if intervention == "protected_order_reversal_perturbation":
        return tuple(reversed(base))
    if intervention == "scope_change":
        return tuple(base[::2] + base[1::2])
    if intervention == "constraint_change":
        return tuple(base[1:] + base[:1])
    raise ValueError(f"unknown B intervention: {intervention}")


def _hidden_slot(world: DevWorld) -> int:
    for index, action in enumerate(world.actions):
        if action.action_id == world.optimal_action_id:
            return index
    raise ValueError("B world optimal action missing from action carrier")


def _protected_order_slots(world: DevWorld, intervention: str) -> tuple[int, ...]:
    return _apply_intervention(_base_order_from_hidden(_hidden_slot(world)), intervention)


def _make_b_world(cell: str, world_index: int, *, channel: str = "primary") -> DevWorld:
    seed = derive_dev_seed("B", f"{cell}|{channel}", world_index, "abgp-b-latent-v2")
    actions = tuple(ProtectedAction(f"B-a{i}") for i in range(4))
    hidden = int(seed[:16], 16) % 4
    return DevWorld(
        arm="B",
        world_index=world_index,
        seed_digest=seed,
        actions=actions,
        optimal_action_id=actions[hidden].action_id,
        comparative_cells=(),
    )


@dataclass(frozen=True)
class GrammarAdapter:
    family_id: str
    surface_alphabet: tuple[str, ...]
    primitives: tuple[str, ...]
    primitive_arities: tuple[int, ...]
    serialization_schema: str
    inference_route: str
    slot_tokens: tuple[str, ...]
    translation_table: None = None

    def _surface_token(self, slot: int) -> str:
        return self.slot_tokens[int(slot)]

    def _slot_from_surface(self, token: str) -> int:
        try:
            return self.slot_tokens.index(token)
        except ValueError as exc:
            raise ValueError(f"token not in {self.family_id} surface carrier") from exc

    def represent(self, world: DevWorld, intervention: str) -> Any:
        return self.encode_order(_protected_order_slots(world, intervention), intervention)

    def encode_order(self, order: Sequence[int], intervention: str) -> Any:
        raise NotImplementedError

    def infer_order(self, representation: Any) -> tuple[int, ...]:
        raise NotImplementedError


class ExtensionalGrammar(GrammarAdapter):
    def __init__(self) -> None:
        super().__init__(
            family_id="extensional",
            surface_alphabet=("ex_q", "ex_r", "ex_s"),
            primitives=("ex_observes", "ex_actions", "ex_consequence"),
            primitive_arities=(3,),
            serialization_schema="extensional-row-v2",
            inference_route="ranked_extensional_rows",
            slot_tokens=("ex_s2", "ex_s0", "ex_s3", "ex_s1"),
        )

    def encode_order(self, order: Sequence[int], intervention: str) -> Any:
        return tuple(
            ("ex_consequence", rank, self._surface_token(slot), intervention)
            for rank, slot in enumerate(order)
        )

    def infer_order(self, representation: Any) -> tuple[int, ...]:
        rows = sorted(tuple(representation), key=lambda row: int(row[1]))
        return tuple(self._slot_from_surface(str(row[2])) for row in rows)


class CompositionalGrammar(GrammarAdapter):
    def __init__(self) -> None:
        super().__init__(
            family_id="compositional",
            surface_alphabet=("co_u", "co_v", "co_w", "co_z"),
            primitives=("co_seed", "co_swap", "co_mask", "co_fold"),
            primitive_arities=(1, 2),
            serialization_schema="compositional-prefix-v2",
            inference_route="compose_rank_fragments_then_reduce",
            slot_tokens=("co_z", "co_v", "co_u", "co_w"),
        )

    def encode_order(self, order: Sequence[int], intervention: str) -> Any:
        fragments = tuple(
            ("co_mask", rank, ("co_seed", self._surface_token(slot)))
            for rank, slot in enumerate(order)
        )
        return ("co_fold", intervention, fragments)

    def infer_order(self, representation: Any) -> tuple[int, ...]:
        if not isinstance(representation, tuple) or representation[0] != "co_fold":
            raise ValueError("invalid compositional representation")
        fragments = sorted(tuple(representation[2]), key=lambda row: int(row[1]))
        return tuple(self._slot_from_surface(str(row[2][1])) for row in fragments)


class ReachabilityGrammar(GrammarAdapter):
    def __init__(self) -> None:
        super().__init__(
            family_id="reachability",
            surface_alphabet=("gr_n", "gr_e", "gr_t", "gr_p", "gr_h"),
            primitives=("gr_node", "gr_edge", "gr_path", "gr_delete", "gr_reach"),
            primitive_arities=(2, 3),
            serialization_schema="reachability-adjacency-v2",
            inference_route="directed_chain_topological_recovery",
            slot_tokens=("gr_h", "gr_n", "gr_t", "gr_p"),
        )

    def encode_order(self, order: Sequence[int], intervention: str) -> Any:
        nodes = tuple(self._surface_token(slot) for slot in order)
        edges = tuple((nodes[i], nodes[i + 1], intervention) for i in range(len(nodes) - 1))
        return {"nodes": nodes, "edges": edges, "intervention": intervention}

    def infer_order(self, representation: Any) -> tuple[int, ...]:
        nodes = tuple(str(x) for x in representation["nodes"])
        edges = tuple((str(row[0]), str(row[1])) for row in representation["edges"])
        incoming = {node: 0 for node in nodes}
        outgoing: dict[str, str] = {}
        for left, right in edges:
            incoming[right] += 1
            outgoing[left] = right
        starts = [node for node in nodes if incoming[node] == 0]
        if len(starts) != 1:
            raise ValueError("reachability chain must have one source")
        ordered = [starts[0]]
        while ordered[-1] in outgoing:
            ordered.append(outgoing[ordered[-1]])
        if len(ordered) != len(nodes):
            raise ValueError("reachability chain did not cover all nodes")
        return tuple(self._slot_from_surface(token) for token in ordered)


class ConstraintOrderGrammar(GrammarAdapter):
    def __init__(self) -> None:
        super().__init__(
            family_id="constraint_order",
            surface_alphabet=("or_l", "or_d", "or_c", "or_x", "or_y", "or_k"),
            primitives=(
                "or_leq",
                "or_dom",
                "or_scope",
                "or_guard",
                "or_join",
                "or_project",
            ),
            primitive_arities=(1, 3, 4),
            serialization_schema="constraint-pairs-v2",
            inference_route="pairwise_dominance_score_then_sort",
            slot_tokens=("or_y", "or_k", "or_c", "or_x"),
        )

    def encode_order(self, order: Sequence[int], intervention: str) -> Any:
        tokens = tuple(self._surface_token(slot) for slot in order)
        return frozenset(
            ("or_dom", tokens[i], tokens[j], intervention)
            for i in range(len(tokens))
            for j in range(i + 1, len(tokens))
        )

    def infer_order(self, representation: Any) -> tuple[int, ...]:
        wins: dict[str, int] = {}
        losses: dict[str, int] = {}
        for row in representation:
            left = str(row[1])
            right = str(row[2])
            wins[left] = wins.get(left, 0) + 1
            wins.setdefault(right, 0)
            losses[right] = losses.get(right, 0) + 1
            losses.setdefault(left, 0)
        tokens = sorted(wins, key=lambda token: (-wins[token], losses[token], token))
        return tuple(self._slot_from_surface(token) for token in tokens)


def grammar_families() -> tuple[GrammarAdapter, ...]:
    return (
        ExtensionalGrammar(),
        CompositionalGrammar(),
        ReachabilityGrammar(),
        ConstraintOrderGrammar(),
    )


@dataclass(frozen=True)
class CapabilityOrder:
    base_order: tuple[int, ...]

    def predict(self, intervention: str) -> tuple[int, ...]:
        return _apply_intervention(self.base_order, intervention)

    @property
    def digest(self) -> str:
        return _canonical_digest(("capability-order-v1", self.base_order))


@dataclass(frozen=True)
class BRecord:
    acquisition_family: str
    transfer_family: str
    world_index: int
    seed_digest: str
    intervention_results: tuple[tuple[str, int], ...]
    treatment_success: int
    wrong_class_success: int
    shuffled_coupling_success: int
    bisimulation_bayes_success: int
    bisimulation_separation_witness: bool
    recovery_path_verified: bool
    acquired_capability_digest: str
    transfer_recovered_digest: str
    bisimulation_control_digest: str
    representation_digests: tuple[str, str]


def source_history_posterior(
    grammar: GrammarAdapter, observation: Any
) -> tuple[CapabilityOrder, ...]:
    """Exact uniform finite prior conditioned on the ACTUAL source observation.

    No hidden-world argument is accepted. These codecs reveal the full order;
    hence this ordinary control must match them rather than being blinded to an
    invented parity bit. This is not a greatest-bisimulation implementation.
    """
    compatible = []
    for hidden in range(4):
        candidate_order = _base_order_from_hidden(hidden)
        if grammar.encode_order(candidate_order, _BASELINE) == observation:
            compatible.append(CapabilityOrder(candidate_order))
    if not compatible:
        raise ValueError("source history has zero probability under the declared prior")
    return tuple(compatible)


def _source_history_control(
    grammar: GrammarAdapter, observation: Any
) -> tuple[CapabilityOrder, bool, str]:
    candidates = source_history_posterior(grammar, observation)
    # Every candidate induces a joint four-intervention policy. Uniform prior
    # and exact all-four loss: choose the most probable policy, ties lexical.
    counts: dict[tuple[tuple[int, ...], ...], int] = {}
    for candidate in candidates:
        vector = tuple(candidate.predict(i) for i in _INTERVENTIONS)
        counts[vector] = counts.get(vector, 0) + 1
    best = min(counts, key=lambda vector: (-counts[vector], vector))
    chosen = next(c for c in candidates if tuple(c.predict(i) for i in _INTERVENTIONS) == best)
    separation = len(counts) > 1
    evidence_digest = _canonical_digest(("exact-source-history-posterior-v1", tuple(c.base_order for c in candidates)))
    return chosen, separation, evidence_digest


def _wrong_class(capability: CapabilityOrder) -> CapabilityOrder:
    base = capability.base_order
    return CapabilityOrder(tuple(base[1:] + base[:1]))


def _record(acquisition: GrammarAdapter, transfer: GrammarAdapter, world_index: int) -> BRecord:
    cell = f"{acquisition.family_id}->{transfer.family_id}"
    world = _make_b_world(cell, world_index)

    acquisition_representation = acquisition.represent(world, _BASELINE)
    acquired_base = acquisition.infer_order(acquisition_representation)
    acquired = CapabilityOrder(acquired_base)
    acquisition_verified = acquired_base == _protected_order_slots(world, _BASELINE)

    results: list[tuple[str, int]] = []
    transfer_orders: list[tuple[int, ...]] = []
    target_orders: list[tuple[int, ...]] = []
    for intervention in _INTERVENTIONS:
        transfer_representation = transfer.represent(world, intervention)
        transfer_order = transfer.infer_order(transfer_representation)
        predicted_order = acquired.predict(intervention)
        target_order = _protected_order_slots(world, intervention)
        transfer_orders.append(transfer_order)
        target_orders.append(target_order)
        results.append(
            (
                intervention,
                int(predicted_order == transfer_order == target_order),
            )
        )

    wrong = _wrong_class(acquired)
    wrong_success = int(
        all(wrong.predict(intervention) == target for intervention, target in zip(_INTERVENTIONS, target_orders))
    )

    shuffled_world = _make_b_world(cell, world_index, channel="shuffled-coupling")
    shuffled_base = acquisition.infer_order(acquisition.represent(shuffled_world, _BASELINE))
    shuffled = CapabilityOrder(shuffled_base)
    shuffled_success = int(
        all(
            shuffled.predict(intervention) == target
            for intervention, target in zip(_INTERVENTIONS, target_orders)
        )
    )

    bisim, bisim_separation, bisim_digest = _source_history_control(acquisition, acquisition_representation)
    bisim_success = int(
        all(
            bisim.predict(intervention) == target
            for intervention, target in zip(_INTERVENTIONS, target_orders)
        )
    )

    treatment = int(all(ok for _, ok in results))
    transfer_digest = _canonical_digest(tuple(transfer_orders))
    recovery_verified = acquisition_verified and treatment == 1
    return BRecord(
        acquisition_family=acquisition.family_id,
        transfer_family=transfer.family_id,
        world_index=world_index,
        seed_digest=world.seed_digest,
        intervention_results=tuple(results),
        treatment_success=treatment,
        wrong_class_success=wrong_success,
        shuffled_coupling_success=shuffled_success,
        bisimulation_bayes_success=bisim_success,
        bisimulation_separation_witness=bisim_separation,
        recovery_path_verified=recovery_verified,
        acquired_capability_digest=acquired.digest,
        transfer_recovered_digest=transfer_digest,
        bisimulation_control_digest=bisim_digest,
        representation_digests=(
            _canonical_digest(acquisition_representation),
            _canonical_digest(transfer.represent(world, _INTERVENTIONS[0])),
        ),
    )


def generate_b_dev_records(worlds_per_direction: int) -> list[BRecord]:
    if worlds_per_direction <= 0:
        raise ValueError("B DEV worlds_per_direction must be positive")
    families = grammar_families()
    records: list[BRecord] = []
    for acquisition, transfer in permutations(families, 2):
        for world_index in range(worlds_per_direction):
            records.append(_record(acquisition, transfer, world_index))
    if len({record.seed_digest for record in records}) != len(records):
        raise ValueError("B ordered-direction world roots must be unique")
    return records
