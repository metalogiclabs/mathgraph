"""Source-pinned Peterson -> abstract Lock semantic adapter.

This is deliberately not a general TLA+ parser. It is a real, executable
lowering qualified against one exact external source/version and its declared
refinement boundary. The goal is to exercise MathGraph AdapterContract on a
non-identity source-language translation without overclaiming.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from collections import deque

from mathgraph.crystal import (
    AdapterContract,
    SemanticObject,
    UnknownTranslation,
    canonical_bytes,
    lower_semantic_object,
)


SOURCE_REPOSITORY = "tlaplus/Examples"
SOURCE_COMMIT = "c9e45d0e4695a8552d31105b93dff21456b7be69"
SOURCE_PATH = "specifications/locks_auxiliary_vars/Peterson.tla"
SOURCE_BLOB_SHA = "1c56470b957d680e7989d460c92738019a87a4b4"
TARGET_PATH = "specifications/locks_auxiliary_vars/Lock.tla"
TARGET_BLOB_SHA = "d8ce7721d26ab726bf9a1f163a16b186f01931eb"
CFG_BLOB_SHA = "ae8a5c6b21ea19334c8d019deb0a1ed5ea5c44f4"
TLC_EVIDENCE_RUN = "github-run:35961400825"

REFINEMENT_INTERFACE = "tla.refinement.lock-spec@1"
CONTROL_INTERFACE = "tla.control-state@1"
PETERSON_INTERNAL_INTERFACE = "tla.peterson.internal@1"


PET_LABELS = ("a0", "a1", "a2", "a3", "cs", "a4")
LOCK_LABELS = ("l0", "l1", "cs", "l2")


@dataclass(frozen=True, order=True)
class PetersonState:
    pc1: str
    pc2: str
    c1: bool
    c2: bool
    turn: int

    def __post_init__(self) -> None:
        if self.pc1 not in PET_LABELS or self.pc2 not in PET_LABELS:
            raise ValueError("invalid Peterson control label")
        if self.turn not in (1, 2):
            raise ValueError("Peterson turn must be 1 or 2")


@dataclass(frozen=True, order=True)
class LockState:
    pc1: str
    pc2: str
    lock: int

    def __post_init__(self) -> None:
        if self.pc1 not in LOCK_LABELS or self.pc2 not in LOCK_LABELS:
            raise ValueError("invalid Lock control label")
        if self.lock not in (0, 1):
            raise ValueError("Lock value must be 0 or 1")


def other(proc: int) -> int:
    if proc not in (1, 2):
        raise ValueError("process must be 1 or 2")
    return 2 if proc == 1 else 1


def pc_translation(label: str) -> str:
    if label == "a0":
        return "l0"
    if label in ("a1", "a2", "a3"):
        return "l1"
    if label == "cs":
        return "cs"
    if label == "a4":
        return "l2"
    raise ValueError(label)


def lock_translation(state: PetersonState) -> int:
    return 0 if state.pc1 in ("cs", "a4") or state.pc2 in ("cs", "a4") else 1


def lower_state(state: PetersonState) -> LockState:
    return LockState(
        pc_translation(state.pc1),
        pc_translation(state.pc2),
        lock_translation(state),
    )


PETERSON_INIT = PetersonState("a0", "a0", False, False, 1)
LOCK_INIT = LockState("l0", "l0", 1)


def _peterson_step(state: PetersonState, proc: int) -> PetersonState | None:
    pc = state.pc1 if proc == 1 else state.pc2
    other_pc = state.pc2 if proc == 1 else state.pc1
    own_c = state.c1 if proc == 1 else state.c2
    other_c = state.c2 if proc == 1 else state.c1

    next_pc = pc
    c1, c2, turn = state.c1, state.c2, state.turn

    if pc == "a0":
        next_pc = "a1"
    elif pc == "a1":
        next_pc = "a2"
        if proc == 1:
            c1 = True
        else:
            c2 = True
    elif pc == "a2":
        next_pc = "a3"
        turn = other(proc)
    elif pc == "a3":
        if other_c and turn != proc:
            return None
        next_pc = "cs"
    elif pc == "cs":
        next_pc = "a4"
    elif pc == "a4":
        next_pc = "a0"
        if proc == 1:
            c1 = False
        else:
            c2 = False
    else:
        raise AssertionError((pc, other_pc, own_c))

    if proc == 1:
        return PetersonState(next_pc, state.pc2, c1, c2, turn)
    return PetersonState(state.pc1, next_pc, c1, c2, turn)


def peterson_successors(state: PetersonState) -> tuple[PetersonState, ...]:
    out = []
    for proc in (1, 2):
        nxt = _peterson_step(state, proc)
        if nxt is not None:
            out.append(nxt)
    return tuple(sorted(set(out)))


def _lock_step(state: LockState, proc: int) -> LockState | None:
    pc = state.pc1 if proc == 1 else state.pc2
    next_pc = pc
    lock = state.lock

    if pc == "l0":
        next_pc = "l1"
    elif pc == "l1":
        if lock != 1:
            return None
        next_pc = "cs"
        lock = 0
    elif pc == "cs":
        next_pc = "l2"
    elif pc == "l2":
        next_pc = "l0"
        lock = 1
    else:
        raise AssertionError(pc)

    if proc == 1:
        return LockState(next_pc, state.pc2, lock)
    return LockState(state.pc1, next_pc, lock)


def lock_successors(state: LockState) -> tuple[LockState, ...]:
    out = []
    for proc in (1, 2):
        nxt = _lock_step(state, proc)
        if nxt is not None:
            out.append(nxt)
    return tuple(sorted(set(out)))


def reachable_peterson_states() -> tuple[PetersonState, ...]:
    seen = {PETERSON_INIT}
    queue = deque([PETERSON_INIT])
    while queue:
        state = queue.popleft()
        for nxt in peterson_successors(state):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return tuple(sorted(seen))


def peterson_state_object(state: PetersonState) -> SemanticObject:
    payload = canonical_bytes({
        "pc": {"1": state.pc1, "2": state.pc2},
        "c": {"1": state.c1, "2": state.c2},
        "turn": state.turn,
    })
    return SemanticObject(
        "tla.peterson.state",
        1,
        payload,
        (REFINEMENT_INTERFACE, CONTROL_INTERFACE, PETERSON_INTERNAL_INTERFACE),
    )


def lock_state_object(state: LockState) -> SemanticObject:
    payload = canonical_bytes({
        "pc": {"1": state.pc1, "2": state.pc2},
        "lock": state.lock,
    })
    return SemanticObject(
        "tla.lock.state",
        1,
        payload,
        (REFINEMENT_INTERFACE, CONTROL_INTERFACE),
    )


def _decode_peterson_object(obj: SemanticObject) -> PetersonState:
    if obj.type_id != "tla.peterson.state" or obj.contract_version != 1:
        raise ValueError("unsupported Peterson semantic object")
    raw = json.loads(obj.payload.decode("utf-8"))
    return PetersonState(
        raw["pc"]["1"],
        raw["pc"]["2"],
        bool(raw["c"]["1"]),
        bool(raw["c"]["2"]),
        int(raw["turn"]),
    )


def _lower_peterson_object(obj: SemanticObject) -> SemanticObject:
    return lock_state_object(lower_state(_decode_peterson_object(obj)))


ADAPTER_CONTRACT = AdapterContract(
    adapter_id="tla.peterson-to-lock",
    contract_version=1,
    source_space=f"tla.peterson@{SOURCE_COMMIT}",
    target_space=f"tla.lock@{SOURCE_COMMIT}",
    preserves_interfaces=(REFINEMENT_INTERFACE, CONTROL_INTERFACE),
    assumption_refs=(
        f"git:{SOURCE_REPOSITORY}@{SOURCE_COMMIT}:{SOURCE_PATH}:{SOURCE_BLOB_SHA}",
        f"git:{SOURCE_REPOSITORY}@{SOURCE_COMMIT}:{TARGET_PATH}:{TARGET_BLOB_SHA}",
        f"git:{SOURCE_REPOSITORY}@{SOURCE_COMMIT}:Peterson.cfg:{CFG_BLOB_SHA}",
    ),
    evidence_refs=(
        TLC_EVIDENCE_RUN,
        "source-theorem:Refinement==Spec=>L!Spec",
    ),
)


def lower_peterson_object(
    obj: SemanticObject,
    requested_interface: str,
) -> SemanticObject | UnknownTranslation:
    return lower_semantic_object(
        obj,
        ADAPTER_CONTRACT,
        requested_interface,
        _lower_peterson_object,
    )


def qualification_report() -> dict[str, object]:
    """Exhaustively check the finite refinement relation on reachable states."""

    reachable = reachable_peterson_states()
    violations = []
    concrete_transition_count = 0
    stutter_count = 0
    abstract_step_count = 0

    if lower_state(PETERSON_INIT) != LOCK_INIT:
        violations.append(("init", PETERSON_INIT, lower_state(PETERSON_INIT), LOCK_INIT))

    for state in reachable:
        abstract = lower_state(state)
        for nxt in peterson_successors(state):
            concrete_transition_count += 1
            abstract_nxt = lower_state(nxt)
            if abstract_nxt == abstract:
                stutter_count += 1
            elif abstract_nxt in lock_successors(abstract):
                abstract_step_count += 1
            else:
                violations.append(("step", state, nxt, abstract, abstract_nxt))

    return {
        "reachable_states": len(reachable),
        "concrete_transitions": concrete_transition_count,
        "abstract_steps": abstract_step_count,
        "abstract_stutters": stutter_count,
        "violations": tuple(violations),
        "adapter_contract_id": ADAPTER_CONTRACT.id,
    }


def main() -> None:
    report = qualification_report()
    assert report["reachable_states"] == 42, report
    assert report["violations"] == (), report
    print("TLA_PETERSON_ADAPTER=PASS")
    for key, value in report.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
