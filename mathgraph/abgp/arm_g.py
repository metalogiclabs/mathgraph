from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import floor

from .dev_world import make_dev_world


_DOSES = (0.0, 0.1, 0.25, 0.5, 1.0)


@dataclass(frozen=True)
class GRecord:
    world_index: int
    seed_digest: str
    dose: float
    relevance_computed_before_corruption: bool
    relevant_corruption_count: int
    irrelevant_corruption_count: int
    relevant_corruption_magnitude: float
    irrelevant_corruption_magnitude: float
    relevant_corrupted_cells: tuple[str, ...]
    irrelevant_corrupted_cells: tuple[str, ...]
    matched_corruption_pairs: tuple[tuple[str, str], ...]
    relevant_flip: int
    irrelevant_flip: int


def _canonical_pair(left: str, right: str) -> tuple[str, str]:
    return tuple(sorted((str(left), str(right))))  # type: ignore[return-value]


def _pair_rank(seed_digest: str, pair: tuple[str, str]) -> str:
    canonical = _canonical_pair(*pair)
    return sha256(
        f"{seed_digest}|g-matched-pair-v1|{canonical[0]}|{canonical[1]}".encode("utf-8")
    ).hexdigest()


def _ordered_matched_pairs(
    seed_digest: str,
    relevant_ids: tuple[str, ...],
    irrelevant_ids: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    if len(relevant_ids) != len(irrelevant_ids):
        raise ValueError("G relevance classes must have equal cardinality")
    # Pair membership is fixed before outcomes. Ranking depends only on an
    # unordered pair key, so exchanging the two class labels leaves pair
    # selection unchanged.
    pairs = tuple(zip(relevant_ids, irrelevant_ids))
    return tuple(sorted(pairs, key=lambda pair: _pair_rank(seed_digest, pair)))


def _records_for_world(world_index: int) -> list[GRecord]:
    world = make_dev_world("G", world_index, "abgp-g-dev-v1")
    relevant_ids = tuple(
        cell.cell_id for cell in world.comparative_cells if cell.action_relevant
    )
    irrelevant_ids = tuple(
        cell.cell_id for cell in world.comparative_cells if not cell.action_relevant
    )
    if len(relevant_ids) != 10 or len(irrelevant_ids) != 10:
        raise ValueError("G DEV world must expose exactly 10 cells per relevance class")

    ordered_pairs = _ordered_matched_pairs(world.seed_digest, relevant_ids, irrelevant_ids)
    m = len(ordered_pairs)
    records: list[GRecord] = []
    for dose in _DOSES:
        count = 0 if dose == 0 else floor(dose * m)
        if dose > 0 and count <= 0:
            raise ValueError("nonzero G dose must corrupt at least one matched pair")
        magnitude = 1.0
        selected_pairs = ordered_pairs[:count]
        relevant_selected = tuple(pair[0] for pair in selected_pairs)
        irrelevant_selected = tuple(pair[1] for pair in selected_pairs)

        # DEV planted-positive outcome path. The randomization validity audit is
        # separate: under its declared sharp null, the label-specific effect is
        # removed and the complete paired vector is checked for joint-swap
        # invariance. Do not use this planted alternative itself as a null proof.
        relevant_flip = int(count >= 5)
        irrelevant_flip = 0
        records.append(
            GRecord(
                world_index=world_index,
                seed_digest=world.seed_digest,
                dose=dose,
                relevance_computed_before_corruption=True,
                relevant_corruption_count=count,
                irrelevant_corruption_count=count,
                relevant_corruption_magnitude=magnitude,
                irrelevant_corruption_magnitude=magnitude,
                relevant_corrupted_cells=relevant_selected,
                irrelevant_corrupted_cells=irrelevant_selected,
                matched_corruption_pairs=selected_pairs,
                relevant_flip=relevant_flip,
                irrelevant_flip=irrelevant_flip,
            )
        )
    return records


def generate_g_dev_records(world_count: int) -> list[GRecord]:
    if world_count <= 0:
        raise ValueError("G DEV world count must be positive")
    records: list[GRecord] = []
    for world_index in range(world_count):
        records.extend(_records_for_world(world_index))
    return records
