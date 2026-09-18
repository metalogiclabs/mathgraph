from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .manifest import derive_dev_seed


@dataclass(frozen=True)
class ProtectedAction:
    action_id: str


@dataclass(frozen=True)
class ComparativeCell:
    cell_id: str
    action_relevant: bool
    value: int


@dataclass(frozen=True)
class DevWorld:
    arm: str
    world_index: int
    seed_digest: str
    actions: tuple[ProtectedAction, ...]
    optimal_action_id: str
    comparative_cells: tuple[ComparativeCell, ...]


def _int_digest(text: str) -> int:
    return int(sha256(text.encode("utf-8")).hexdigest(), 16)


def make_dev_world(arm: str, world_index: int, generator_version: str) -> DevWorld:
    seed = derive_dev_seed(arm, "world", world_index, generator_version)
    actions = tuple(ProtectedAction(f"{arm}-a{i}") for i in range(4))
    hidden = int(seed[:16], 16) % len(actions)
    cells = tuple(
        ComparativeCell(
            cell_id=f"{arm}-c{i:02d}",
            action_relevant=i < 10,
            value=_int_digest(f"{seed}|cell|{i}") % 7,
        )
        for i in range(20)
    )
    return DevWorld(
        arm=arm,
        world_index=world_index,
        seed_digest=seed,
        actions=actions,
        optimal_action_id=actions[hidden].action_id,
        comparative_cells=cells,
    )


def deterministic_order(seed_digest: str, label: str, values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        sorted(
            values,
            key=lambda value: sha256(
                f"{seed_digest}|{label}|{value}".encode("utf-8")
            ).hexdigest(),
        )
    )
