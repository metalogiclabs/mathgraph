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
    compose_adapter_contracts,
    compose_lower_semantic_object,
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

OCCUPANCY_INTERFACE = "tla.critical-occupancy@1"


@dataclass(frozen=True, order=True)
class CriticalOccupancy:
    p1: bool
    p2: bool


def peterson_occupancy(state: PetersonState) -> CriticalOccupancy:
    return CriticalOccupancy(
        state.pc1 in ("cs", "a4"),
        state.pc2 in ("cs", "a4"),
    )


def lock_occupancy(state: LockState) -> CriticalOccupancy:
    return CriticalOccupancy(
        state.pc1 in ("cs", "l2"),
        state.pc2 in ("cs", "l2"),
    )


def peterson_state_object_v2(state: PetersonState) -> SemanticObject:
    base = peterson_state_object(state)
    return SemanticObject(
        base.type_id, base.contract_version, base.payload,
        base.interfaces + (OCCUPANCY_INTERFACE,),
    )


def lock_state_object_v2(state: LockState) -> SemanticObject:
    base = lock_state_object(state)
    return SemanticObject(
        base.type_id, base.contract_version, base.payload,
        base.interfaces + (OCCUPANCY_INTERFACE,),
    )


def occupancy_object(view: CriticalOccupancy) -> SemanticObject:
    return SemanticObject(
        "tla.critical-occupancy",
        1,
        canonical_bytes({"p1": view.p1, "p2": view.p2}),
        (OCCUPANCY_INTERFACE,),
    )


def _decode_lock_object(obj: SemanticObject) -> LockState:
    if obj.type_id != "tla.lock.state" or obj.contract_version != 1:
        raise ValueError("unsupported Lock semantic object")
    raw = json.loads(obj.payload.decode("utf-8"))
    return LockState(raw["pc"]["1"], raw["pc"]["2"], int(raw["lock"]))


def _lower_peterson_object_v2(obj: SemanticObject) -> SemanticObject:
    return lock_state_object_v2(lower_state(_decode_peterson_object(obj)))


def _lower_lock_occupancy(obj: SemanticObject) -> SemanticObject:
    return occupancy_object(lock_occupancy(_decode_lock_object(obj)))


PETERSON_TO_LOCK_OCCUPANCY_CONTRACT = AdapterContract(
    adapter_id="tla.peterson-to-lock",
    contract_version=2,
    source_space=f"tla.peterson@{SOURCE_COMMIT}",
    target_space=f"tla.lock@{SOURCE_COMMIT}",
    preserves_interfaces=(OCCUPANCY_INTERFACE,),
    assumption_refs=ADAPTER_CONTRACT.assumption_refs,
    evidence_refs=ADAPTER_CONTRACT.evidence_refs + (
        "qualified-observation:critical-occupancy",
    ),
)


LOCK_TO_OCCUPANCY_CONTRACT = AdapterContract(
    adapter_id="tla.lock-to-critical-occupancy",
    contract_version=1,
    source_space=f"tla.lock@{SOURCE_COMMIT}",
    target_space="mathgraph.tla.critical-occupancy@1",
    preserves_interfaces=(OCCUPANCY_INTERFACE,),
    assumption_refs=(
        f"git:{SOURCE_REPOSITORY}@{SOURCE_COMMIT}:{TARGET_PATH}:{TARGET_BLOB_SHA}",
    ),
    evidence_refs=("source-definition:Lock.lockcs",),
)


COMPOSED_OCCUPANCY_CONTRACT = compose_adapter_contracts(
    PETERSON_TO_LOCK_OCCUPANCY_CONTRACT,
    LOCK_TO_OCCUPANCY_CONTRACT,
    adapter_id="tla.peterson-to-critical-occupancy",
)


def lower_peterson_to_occupancy(
    obj: SemanticObject, requested_interface: str
) -> SemanticObject | UnknownTranslation:
    return compose_lower_semantic_object(
        obj,
        PETERSON_TO_LOCK_OCCUPANCY_CONTRACT,
        LOCK_TO_OCCUPANCY_CONTRACT,
        requested_interface,
        _lower_peterson_object_v2,
        _lower_lock_occupancy,
        adapter_id="tla.peterson-to-critical-occupancy",
    )


def composition_qualification_report() -> dict[str, object]:
    direct_mismatches = []
    staged_mismatches = []
    states = reachable_peterson_states()
    for state in states:
        source = peterson_state_object_v2(state)
        composed = lower_peterson_to_occupancy(source, OCCUPANCY_INTERFACE)
        if not isinstance(composed, SemanticObject):
            staged_mismatches.append((state, composed))
            continue
        direct = occupancy_object(peterson_occupancy(state))
        if composed != direct:
            direct_mismatches.append((state, composed.id, direct.id))

        middle = lower_semantic_object(
            source,
            PETERSON_TO_LOCK_OCCUPANCY_CONTRACT,
            OCCUPANCY_INTERFACE,
            _lower_peterson_object_v2,
        )
        assert isinstance(middle, SemanticObject)
        staged = lower_semantic_object(
            middle,
            LOCK_TO_OCCUPANCY_CONTRACT,
            OCCUPANCY_INTERFACE,
            _lower_lock_occupancy,
        )
        if staged != composed:
            staged_mismatches.append((state, staged, composed))

    control_probe = lower_peterson_to_occupancy(
        peterson_state_object_v2(PETERSON_INIT), CONTROL_INTERFACE
    )
    return {
        "reachable_states": len(states),
        "direct_mismatches": tuple(direct_mismatches),
        "staged_mismatches": tuple(staged_mismatches),
        "composed_contract_id": COMPOSED_OCCUPANCY_CONTRACT.id,
        "composed_interfaces": COMPOSED_OCCUPANCY_CONTRACT.preserves_interfaces,
        "control_probe": control_probe,
    }


def main() -> None:
    report = qualification_report()
    assert report["reachable_states"] == 42, report
    assert report["violations"] == (), report
    print("TLA_PETERSON_ADAPTER=PASS")
    for key, value in report.items():
        print(f"{key}={value}")

    composition = composition_qualification_report()
    assert composition["reachable_states"] == 42, composition
    assert composition["direct_mismatches"] == (), composition
    assert composition["staged_mismatches"] == (), composition
    assert composition["composed_interfaces"] == (OCCUPANCY_INTERFACE,), composition
    assert isinstance(composition["control_probe"], UnknownTranslation), composition
    print("TLA_ADAPTER_COMPOSITION=PASS")
    for key, value in composition.items():
        print(f"composition_{key}={value}")


if __name__ == "__main__":
    main()
