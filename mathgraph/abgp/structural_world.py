from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Callable, Iterable, Sequence

Reducer = Callable[[Sequence[int]], int]


def _bits(values: Sequence[int]) -> tuple[int, ...]:
    result = tuple(int(v) for v in values)
    if not result or any(v not in (0, 1) for v in result):
        raise ValueError('expected a nonempty Boolean vector')
    return result


def reduce_const0(values: Sequence[int]) -> int:
    _bits(values)
    return 0


def reduce_const1(values: Sequence[int]) -> int:
    _bits(values)
    return 1


def reduce_first(values: Sequence[int]) -> int:
    return _bits(values)[0]


def reduce_last(values: Sequence[int]) -> int:
    return _bits(values)[-1]


def reduce_xor(values: Sequence[int]) -> int:
    out = 0
    for value in _bits(values):
        out ^= value
    return out


def reduce_xnor(values: Sequence[int]) -> int:
    return 1 - reduce_xor(values)


def reduce_or(values: Sequence[int]) -> int:
    return int(any(_bits(values)))


def reduce_and(values: Sequence[int]) -> int:
    return int(all(_bits(values)))


OLD_REDUCERS: dict[str, Reducer] = {
    'CONST0': reduce_const0,
    'CONST1': reduce_const1,
    'FIRST': reduce_first,
    'LAST': reduce_last,
}

CONSTRUCTION_REDUCERS: dict[str, Reducer] = {
    'XOR_REDUCE': reduce_xor,
    'XNOR_SHAM': reduce_xnor,
    'OR_REDUCE': reduce_or,
    'AND_REDUCE': reduce_and,
}


@dataclass(frozen=True)
class SourceRow:
    bits: tuple[int, ...]
    consequence: int


def balanced_xor_source_rows() -> tuple[SourceRow, ...]:
    return tuple(SourceRow(bits=tuple(bits), consequence=reduce_xor(bits)) for bits in product((0, 1), repeat=2))


def adequate_reducers(rows: Iterable[SourceRow], reducers: dict[str, Reducer]) -> tuple[str, ...]:
    material = tuple(rows)
    return tuple(
        name for name, reducer in reducers.items()
        if all(reducer(row.bits) == row.consequence for row in material)
    )


def empirical_old_bayes(rows: Iterable[SourceRow]) -> dict[int, tuple[int, int]]:
    counts = {0: [0, 0], 1: [0, 0]}
    for row in rows:
        counts[row.bits[0]][row.consequence] += 1
    return {state: tuple(values) for state, values in counts.items()}


def bayes_predict_from_old(table: dict[int, tuple[int, int]], vector: Sequence[int]) -> int:
    state = _bits(vector)[0]
    zeros, ones = table[state]
    return int(ones > zeros)


def apply_named_reducer(name: str, vector: Sequence[int]) -> int:
    if name in OLD_REDUCERS:
        return OLD_REDUCERS[name](vector)
    if name in CONSTRUCTION_REDUCERS:
        return CONSTRUCTION_REDUCERS[name](vector)
    raise ValueError(f'unknown reducer: {name}')
