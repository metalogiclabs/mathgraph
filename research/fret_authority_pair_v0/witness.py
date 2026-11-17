"""Constrained search for distinguishing finite traces, not arbitrary intent."""

from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class Witness:
    response_trace: tuple[int, ...]
    first_verdict: bool
    second_verdict: bool
    trials: int
    question: str


def find_future_distinction(first_window: tuple[int, int],
                            second_window: tuple[int, int], *, horizon: int,
                            trigger: str, response: str) -> Witness | None:
    """Find the sparsest complete-window response trace for a trigger at t=0.

    Exhaustive only within the finite two-window single-trigger Boolean grammar.
    This search does not infer the source owner's preferred semantics.
    """
    if not (1 <= horizon <= 12) or not trigger.strip() or not response.strip():
        raise ValueError("invalid bounded search space")
    for low, high in (first_window, second_window):
        if not (0 <= low <= high):
            raise ValueError("invalid future window")
    if horizon <= max(first_window[1], second_window[1]):
        raise ValueError("a full future window must be available")

    trials = 0
    for weight in range(horizon + 1):
        for active in combinations(range(horizon), weight):
            trials += 1
            trace = tuple(int(index in active) for index in range(horizon))
            a = any(trace[first_window[0]:first_window[1] + 1])
            b = any(trace[second_window[0]:second_window[1] + 1])
            if a == b:
                continue
            offset = next(index for index in active
                          if (first_window[0] <= index <= first_window[1]) !=
                          (second_window[0] <= index <= second_window[1]))
            question = (f"Does {response} at offset {offset} after {trigger} "
                        "count as satisfying the requirement?")
            return Witness(trace, a, b, trials, question)
    return None
