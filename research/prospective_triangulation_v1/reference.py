"""Conventional hand-coded source-aware checker (no MathGraph compiler import).

The independently expressed C/ACSL truth table is given precisely the same
finite inputs and native observations as the MathGraph contract side.
"""


def reference_output(case: str, row: tuple[int, ...]) -> tuple[int, ...]:
    if case == "conditional_reset":
        a, b = row
        if b:
            a = 0
        return a, b
    if case == "vector_addition":
        length = row[0]
        first = list(row[1:4])
        second = list(row[4:7])
        for position in range(length):
            first[position] = first[position] + second[position]
        return tuple(first + second)
    if case == "search_replace":
        length, *values = row
        arr = values[:3]
        old_value, new_value = values[3:]
        for position in range(length):
            if arr[position] == old_value:
                arr[position] = new_value
        return tuple(arr)
    raise ValueError(case)


def conventional_verdict(case: str, row: tuple[int, ...], c: tuple[int, ...],
                         rust: tuple[int, ...]) -> str:
    known = reference_output(case, row)
    if c != known:
        return "SOURCE_CONTRACT_DISAGREEMENT"
    if rust != known:
        return "DEMONSTRATED_DEFECT"
    return "WARRANTED_BOUNDED_MATCH"
