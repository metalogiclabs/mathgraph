"""Runtime provenance for declared stochastic inputs and their descendants.

A ledger proves graph properties of executed tracked operations, not statistical
independence of a PRNG or absence of arbitrary hidden Python globals. Fixed
protocol constants are distinct from sampled objects; provenance completeness
and the sampling model remain separately reviewable obligations.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Callable, Mapping, Sequence


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


@dataclass(frozen=True)
class Tracked:
    node_id: str
    value: Any
    ledger_token: object


class Ledger:
    def __init__(self) -> None:
        self._token = object()
        self._nodes: dict[str, dict[str, Any]] = {}

    def _check(self, values: Sequence[Tracked]) -> None:
        for value in values:
            if not isinstance(value, Tracked) or value.ledger_token is not self._token or value.node_id not in self._nodes:
                raise ValueError('untracked or foreign dependency')
            if self._nodes[value.node_id]['value_digest'] != _digest(value.value):
                raise ValueError('tracked value mutated after construction')

    def _put(self, name: str, kind: str, value: Any, parents: Sequence[Tracked]) -> Tracked:
        if not isinstance(name, str) or not name or name in self._nodes:
            raise ValueError('each executed event needs a unique nonempty name')
        self._check(parents)
        self._nodes[name] = {'kind': kind, 'parents': [v.node_id for v in parents], 'value_digest': _digest(value)}
        return Tracked(name, value, self._token)

    def fixed(self, name: str, value: Any) -> Tracked:
        return self._put(name, 'fixed_protocol', value, ())

    def sample(self, name: str, draw: Callable[[], Any], *, parents: Sequence[Tracked] = ()) -> Tracked:
        self._check(parents)
        if name in self._nodes:
            raise ValueError('duplicate draw event')
        # Draw occurs HERE, not retroactively inferred from final seed strings.
        return self._put(name, 'sampled', draw(), parents)

    def apply(self, name: str, operation: Callable[..., Any], *parents: Tracked) -> Tracked:
        if not parents:
            raise ValueError('derived operations must declare their inputs')
        self._check(parents)
        return self._put(name, 'derived', operation(*(p.value for p in parents)), parents)

    def audit(self, episode_outputs: Mapping[str, Sequence[Tracked]]) -> dict[str, Any]:
        if not episode_outputs:
            raise ValueError('no episodes to audit')
        def ancestry(node: str) -> set[str]:
            row = self._nodes[node]
            roots = {node} if row['kind'] == 'sampled' else set()
            for parent in row['parents']:
                roots |= ancestry(parent)
            return roots
        roots: dict[str, set[str]] = {}
        for episode, outputs in episode_outputs.items():
            if not outputs:
                raise ValueError('missing episode provenance')
            self._check(outputs)
            roots[episode] = set().union(*(ancestry(v.node_id) for v in outputs))
            if not roots[episode]:
                raise ValueError('episode has no declared sampled ancestor')
        owners: dict[str, list[str]] = {}
        for episode, nodes in roots.items():
            for node in nodes:
                owners.setdefault(node, []).append(episode)
        shared = {node: sorted(eps) for node, eps in owners.items() if len(eps) > 1}
        clusters: list[set[str]] = [{e} for e in roots]
        for eps in shared.values():
            merge = set(eps)
            overlap = [c for c in clusters if c & merge]
            clusters = [c for c in clusters if not c & merge]
            clusters.append(set.union(merge, *overlap))
        graph = json.loads(json.dumps(self._nodes, sort_keys=True))
        return {'structurally_disjoint_random_ancestors': not shared,
                'shared_sampled_ancestors': shared,
                'independent_cluster_count': len(clusters),
                'candidate_clusters': sorted(sorted(c) for c in clusters),
                'sampled_ancestors_by_episode': {e: sorted(v) for e, v in roots.items()},
                'graph': graph, 'graph_sha256': _digest(graph),
                'statistical_independence_proved': False,
                'scope': 'executed declared-dependency DAG; sampling law and untracked globals not certified'}
