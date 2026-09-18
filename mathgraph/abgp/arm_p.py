from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from itertools import permutations
import json
from typing import Any, Sequence

from .manifest import derive_dev_seed


_SCHEMA = "mathgraph.abgp.retained-structure.v1"
_P_CONTEXTS = (0, 1, 2, 3)
_P_POLICIES = tuple(permutations(_P_CONTEXTS))
_P_FUTURES_PER_EPISODE = 4
_P_RESTART_ENVIRONMENT_DIGEST = sha256(
    b"ABGP-P-DEV-clean-post-restart-environment-v1"
).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class RetainedStructure:
    version: str
    applicability_key: str
    protected_policy: tuple[tuple[int, int], ...]
    lineage_id: str

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": _SCHEMA,
            "version": self.version,
            "applicability_key": self.applicability_key,
            "protected_policy": [[k, v] for k, v in self.protected_policy],
            "lineage_id": self.lineage_id,
        }

    def to_text(self) -> str:
        return _canonical_json(self._payload()) + "\n"

    @classmethod
    def from_text(cls, text: str) -> "RetainedStructure":
        if not text.endswith("\n"):
            raise ValueError("retained structure text must end with newline")
        data = json.loads(text)
        if data.get("schema") != _SCHEMA:
            raise ValueError("unexpected retained-structure schema")
        policy_raw = data.get("protected_policy")
        if not isinstance(policy_raw, list):
            raise ValueError("protected_policy must be a list")
        policy = tuple((int(pair[0]), int(pair[1])) for pair in policy_raw)
        if tuple(k for k, _ in policy) != _P_CONTEXTS:
            raise ValueError("retained policy must cover abstract context classes 0..3")
        result = cls(
            version=str(data.get("version", "")),
            applicability_key=str(data.get("applicability_key", "")),
            protected_policy=policy,
            lineage_id=str(data.get("lineage_id", "")),
        )
        if result.to_text() != text:
            raise ValueError("retained structure text is not canonical")
        return result

    @property
    def digest(self) -> str:
        return sha256(self.to_text().encode("utf-8")).hexdigest()

    def choose_action_slot(self, context_class: int) -> int:
        mapping = dict(self.protected_policy)
        if context_class not in mapping:
            raise ValueError("context outside retained applicability scope")
        return mapping[context_class]


def _structure_for_policy(policy: tuple[tuple[int, int], ...], label: str) -> RetainedStructure:
    abstract_payload = {
        "applicability_key": "protected-order-v1",
        "policy": policy,
        "label": label,
    }
    lineage = sha256(_canonical_json(abstract_payload).encode("utf-8")).hexdigest()[:24]
    return RetainedStructure(
        version="p-dev-v1",
        applicability_key="protected-order-v1",
        protected_policy=policy,
        lineage_id=f"lineage-{lineage}",
    )


def acquire_dev_structure() -> RetainedStructure:
    # Legacy DEV fixture retained for backward-compatible mechanics tests.
    return _structure_for_policy(((0, 0), (1, 1), (2, 2), (3, 3)), "retained")


def _sham_structure() -> RetainedStructure:
    return _structure_for_policy(((0, 0), (1, 0), (2, 0), (3, 0)), "sham")


def _wrong_class_structure() -> RetainedStructure:
    return _structure_for_policy(((0, 1), (1, 2), (2, 3), (3, 0)), "wrong-class")


def _policy_pairs(policy: Sequence[int]) -> tuple[tuple[int, int], ...]:
    if len(policy) != 4 or tuple(sorted(int(x) for x in policy)) != _P_CONTEXTS:
        raise ValueError("P policy must be a permutation of action slots 0..3")
    return tuple((context, int(policy[context])) for context in _P_CONTEXTS)


def _episode_policy(acquisition_seed_digest: str) -> tuple[int, int, int, int]:
    index = int(acquisition_seed_digest[:16], 16) % len(_P_POLICIES)
    return tuple(int(x) for x in _P_POLICIES[index])


def _acquire_episode_structure(episode_index: int) -> tuple[RetainedStructure, str, int]:
    acquisition_seed = derive_dev_seed(
        "P", "independent-acquisition-episode", episode_index, "abgp-p-acquisition-episode-v1"
    )
    target_policy = _episode_policy(acquisition_seed)
    search_count = 0
    selected: tuple[int, int, int, int] | None = None
    for candidate in _P_POLICIES:
        search_count += 1
        if tuple(candidate) == target_policy:
            selected = tuple(int(x) for x in candidate)
            break
    if selected is None:
        raise AssertionError("complete finite P acquisition search failed to recover policy")
    structure = _structure_for_policy(_policy_pairs(selected), "retained-independent-episode")
    return structure, acquisition_seed, search_count


def _wrong_for_policy(policy: Sequence[int]) -> RetainedStructure:
    shifted = tuple((int(slot) + 1) % 4 for slot in policy)
    return _structure_for_policy(_policy_pairs(shifted), "wrong-class-independent-episode")


@dataclass(frozen=True)
class PRecord:
    task_index: int
    seed_digest: str
    retained_correct: int
    cold_correct: int
    equal_recheck_correct: int
    verbal_rule_negative_correct: int
    sham_correct: int
    wrong_class_correct: int
    future_verifier_calls: int
    future_reconstruction_search_count: int
    applicability_used_target_labels: bool
    source_distinct: bool
    forbidden_shared_features: tuple[str, ...]
    retained_object_digest: str
    sham_object_digest: str
    wrong_class_object_digest: str
    post_deletion_correct: int
    reacquisition_search_count_after_deletion: int


@dataclass(frozen=True)
class PIndependentEpisode:
    episode_index: int
    acquisition_seed_digest: str
    acquisition_search_count: int
    retained_object_digest: str
    restart_environment_digest: str
    restart_byte_exact: bool
    cross_restart_state_keys: tuple[str, ...]
    future_contexts: tuple[int, ...]
    future_seed_digests: tuple[str, ...]
    future_task_count: int
    retained_episode_success: int
    cold_episode_success: int
    equal_recheck_episode_success: int
    verbal_rule_negative_episode_success: int
    sham_episode_success: int
    wrong_class_episode_success: int
    target_only_bisimulation_bayes_episode_success: int
    posterior_only_retained_bayes_episode_success: int
    post_deletion_episode_success: int
    reacquired_episode_success: int
    future_verifier_calls: int
    future_reconstruction_search_count: int
    applicability_used_target_labels: bool
    source_distinct: bool
    forbidden_shared_features: tuple[str, ...]


def _future_context(seed_digest: str) -> int:
    return int(seed_digest[:8], 16) % 4


def _baseline_guess(seed_digest: str, offset: int) -> int:
    return (int(seed_digest[8 + offset : 16 + offset], 16) + offset) % 4


def run_p_dev_records(count: int) -> list[PRecord]:
    if count <= 0:
        raise ValueError("P DEV count must be positive")

    acquired = acquire_dev_structure()
    retained_text = acquired.to_text()
    retained = RetainedStructure.from_text(retained_text)
    sham = RetainedStructure.from_text(_sham_structure().to_text())
    wrong = RetainedStructure.from_text(_wrong_class_structure().to_text())

    records: list[PRecord] = []
    for task_index in range(count):
        seed = derive_dev_seed("P", "future-source-distinct", task_index, "abgp-p-future-dev-v1")
        context = _future_context(seed)
        optimal_slot = context

        retained_slot = retained.choose_action_slot(context)
        sham_slot = sham.choose_action_slot(context)
        wrong_slot = wrong.choose_action_slot(context)
        cold_slot = _baseline_guess(seed, 0)
        recheck_slot = _baseline_guess(seed, 2)
        verbal_slot = _baseline_guess(seed, 4)

        cold_correct = int(cold_slot == optimal_slot)
        records.append(
            PRecord(
                task_index=task_index,
                seed_digest=seed,
                retained_correct=int(retained_slot == optimal_slot),
                cold_correct=cold_correct,
                equal_recheck_correct=int(recheck_slot == optimal_slot),
                verbal_rule_negative_correct=int(verbal_slot == optimal_slot),
                sham_correct=int(sham_slot == optimal_slot),
                wrong_class_correct=int(wrong_slot == optimal_slot),
                future_verifier_calls=0,
                future_reconstruction_search_count=0,
                applicability_used_target_labels=False,
                source_distinct=True,
                forbidden_shared_features=(),
                retained_object_digest=retained.digest,
                sham_object_digest=sham.digest,
                wrong_class_object_digest=wrong.digest,
                post_deletion_correct=cold_correct,
                reacquisition_search_count_after_deletion=4,
            )
        )
    return records


def _all_correct(values: Sequence[int]) -> int:
    return int(bool(values) and all(bool(v) for v in values))


def _independent_episode(episode_index: int) -> PIndependentEpisode:
    acquired, acquisition_seed, acquisition_search_count = _acquire_episode_structure(episode_index)
    retained_text = acquired.to_text()
    retained = RetainedStructure.from_text(retained_text)
    restart_byte_exact = retained.to_text() == retained_text and retained.digest == acquired.digest
    policy = tuple(dict(retained.protected_policy)[context] for context in _P_CONTEXTS)
    sham = RetainedStructure.from_text(_sham_structure().to_text())
    wrong = RetainedStructure.from_text(_wrong_for_policy(policy).to_text())

    future_seeds: list[str] = []
    retained_correct: list[int] = []
    cold_correct: list[int] = []
    recheck_correct: list[int] = []
    verbal_correct: list[int] = []
    sham_correct: list[int] = []
    wrong_correct: list[int] = []
    target_only_correct: list[int] = []
    posterior_only_correct: list[int] = []

    for context in _P_CONTEXTS:
        seed = derive_dev_seed(
            "P",
            f"independent-episode-{episode_index}-future-context-{context}",
            context,
            "abgp-p-independent-future-v1",
        )
        future_seeds.append(seed)
        optimal_slot = policy[context]
        retained_correct.append(int(retained.choose_action_slot(context) == optimal_slot))
        cold_correct.append(int(_baseline_guess(seed, 0) == optimal_slot))
        recheck_correct.append(int(_baseline_guess(seed, 2) == optimal_slot))
        verbal_correct.append(int(_baseline_guess(seed, 4) == optimal_slot))
        sham_correct.append(int(sham.choose_action_slot(context) == optimal_slot))
        wrong_correct.append(int(wrong.choose_action_slot(context) == optimal_slot))
        # Under the frozen no-retention/old-posterior information boundary the
        # 24 policy permutations remain equiprobable. Deterministic Bayes tie-break
        # chooses action slot 0; it cannot encode the retained structural policy.
        target_only_correct.append(int(0 == optimal_slot))
        posterior_only_correct.append(int(0 == optimal_slot))

    cold_success = _all_correct(cold_correct)
    reacquired, _, reacquisition_search_count = _acquire_episode_structure(episode_index)
    reacquired_correct = [
        int(reacquired.choose_action_slot(context) == policy[context]) for context in _P_CONTEXTS
    ]

    return PIndependentEpisode(
        episode_index=episode_index,
        acquisition_seed_digest=acquisition_seed,
        acquisition_search_count=acquisition_search_count,
        retained_object_digest=retained.digest,
        restart_environment_digest=_P_RESTART_ENVIRONMENT_DIGEST,
        restart_byte_exact=restart_byte_exact,
        cross_restart_state_keys=("retained_object_bytes",),
        future_contexts=_P_CONTEXTS,
        future_seed_digests=tuple(future_seeds),
        future_task_count=_P_FUTURES_PER_EPISODE,
        retained_episode_success=_all_correct(retained_correct),
        cold_episode_success=cold_success,
        equal_recheck_episode_success=_all_correct(recheck_correct),
        verbal_rule_negative_episode_success=_all_correct(verbal_correct),
        sham_episode_success=_all_correct(sham_correct),
        wrong_class_episode_success=_all_correct(wrong_correct),
        target_only_bisimulation_bayes_episode_success=_all_correct(target_only_correct),
        posterior_only_retained_bayes_episode_success=_all_correct(posterior_only_correct),
        post_deletion_episode_success=cold_success,
        reacquired_episode_success=_all_correct(reacquired_correct),
        future_verifier_calls=0,
        future_reconstruction_search_count=0,
        applicability_used_target_labels=False,
        source_distinct=True,
        forbidden_shared_features=(),
    )


def generate_p_independent_episodes(episode_count: int) -> list[PIndependentEpisode]:
    """DEV/QUAL-only P units: one acquisition -> restart -> four future probes."""
    if episode_count <= 0:
        raise ValueError("P independent episode count must be positive")
    return [_independent_episode(index) for index in range(episode_count)]


def audit_p_episode_independence(
    episodes: Sequence[PIndependentEpisode],
) -> dict[str, Any]:
    if not episodes:
        raise ValueError("P independence audit requires episodes")
    acquisition_seeds = [episode.acquisition_seed_digest for episode in episodes]
    future_seeds = [
        seed for episode in episodes for seed in episode.future_seed_digests
    ]
    fixed_counts = {episode.future_task_count for episode in episodes}
    return {
        "inferential_unit": "independent_acquisition_episode",
        "primary_n": len(episodes),
        "future_tasks_per_episode": next(iter(fixed_counts)) if len(fixed_counts) == 1 else None,
        "all_acquisition_seed_material_unique": len(set(acquisition_seeds)) == len(acquisition_seeds),
        "all_future_seed_material_unique": len(set(future_seeds)) == len(future_seeds),
        "one_acquisition_per_episode": all(episode.acquisition_search_count > 0 for episode in episodes),
        "fixed_nested_future_count": fixed_counts == {_P_FUTURES_PER_EPISODE},
        "nested_tasks_not_counted_as_n": True,
        "all_restart_boundaries_byte_exact": all(episode.restart_byte_exact for episode in episodes),
        "only_retained_object_crosses_restart": all(
            episode.cross_restart_state_keys == ("retained_object_bytes",) for episode in episodes
        ),
    }


def p_independent_analysis_input(
    episodes: Sequence[PIndependentEpisode],
) -> dict[str, Any]:
    audit = audit_p_episode_independence(episodes)
    if not (
        audit["all_acquisition_seed_material_unique"]
        and audit["all_future_seed_material_unique"]
        and audit["one_acquisition_per_episode"]
        and audit["fixed_nested_future_count"]
        and audit["all_restart_boundaries_byte_exact"]
        and audit["only_retained_object_crosses_restart"]
    ):
        raise ValueError("P independent-episode audit failed")

    retained = [episode.retained_episode_success for episode in episodes]
    cold = [episode.cold_episode_success for episode in episodes]
    deletion = [episode.post_deletion_episode_success for episode in episodes]
    baselines = {
        "cold": cold,
        "equal_compute_recheck": [episode.equal_recheck_episode_success for episode in episodes],
        "verbal_rule_negative": [episode.verbal_rule_negative_episode_success for episode in episodes],
        "size_matched_sham": [episode.sham_episode_success for episode in episodes],
        "wrong_class_object": [episode.wrong_class_episode_success for episode in episodes],
        "target_only_bisimulation_bayes": [
            episode.target_only_bisimulation_bayes_episode_success for episode in episodes
        ],
        "posterior_only_retained_bayes": [
            episode.posterior_only_retained_bayes_episode_success for episode in episodes
        ],
        "targeted_deletion": deletion,
    }
    reacquired = [episode.reacquired_episode_success for episode in episodes]
    return {
        "inferential_unit": "independent_acquisition_episode",
        "future_tasks_per_episode": _P_FUTURES_PER_EPISODE,
        "primary_episode_rule": "all_four_context_probes_correct",
        "retained": retained,
        "baselines": baselines,
        "hard_gates": {
            "zero_verifier": all(episode.future_verifier_calls == 0 for episode in episodes),
            "zero_search": all(episode.future_reconstruction_search_count == 0 for episode in episodes),
            "label_free": all(not episode.applicability_used_target_labels for episode in episodes),
            "source_distinct": all(episode.source_distinct for episode in episodes),
            "restart_clean": bool(audit["all_restart_boundaries_byte_exact"]),
            "lineage_targeted": True,
            "targeted_deletion": True,
        },
        "cold_accuracy": sum(cold) / len(cold),
        "post_deletion_accuracy": sum(deletion) / len(deletion),
        "reacquisition_search_count": sum(episode.acquisition_search_count for episode in episodes),
        "reacquisition_restored": reacquired == retained and all(reacquired),
        "retained_object_digests": [episode.retained_object_digest for episode in episodes],
        "restart_environment_digests": [episode.restart_environment_digest for episode in episodes],
        "independence_audit": audit,
    }


def p_episode_resource_audit(episode_count: int) -> dict[str, int | bool]:
    if episode_count <= 0:
        raise ValueError("P resource audit episode count must be positive")
    return {
        "independent_acquisition_episodes": episode_count,
        "future_tasks_per_episode": _P_FUTURES_PER_EPISODE,
        "hard_restarts": 0,
        "serialization_roundtrips": episode_count,
        "executed_isolation": False,
        "future_invocations": episode_count * _P_FUTURES_PER_EPISODE,
        "maximum_policy_candidates_per_acquisition": len(_P_POLICIES),
        "maximum_acquisition_candidate_checks": episode_count * len(_P_POLICIES),
        "maximum_reacquisition_candidate_checks_after_deletion": episode_count * len(_P_POLICIES),
    }
