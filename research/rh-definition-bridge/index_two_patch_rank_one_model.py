#!/usr/bin/env python3
"""Bounded countermodel/control for the index-two Galois patching interface.

Each group is G = (C2)^d. A nonzero binary vector eta denotes a sign
character G -> {+1,-1}; an r_i on ker(eta) is a rank-one character.
For each distinct eta subset, enumerate all restrictions and check the
pairwise intersection-trace condition. Record whether a single G-character
restricts to every r_i. This is a model check, NOT a proof of the full
infinite-family or higher-rank IndexTwoPatch.main theorem.
"""
from itertools import combinations, product


def dot(a: int, x: int) -> int:
    return (a & x).bit_count() & 1


def restriction(d: int, eta: int, lam: int) -> tuple[int, ...]:
    return tuple(dot(lam, x) for x in range(1 << d) if dot(eta, x) == 0)


def local_representatives(d: int, eta: int) -> list[int]:
    return list({restriction(d, eta, lam): lam for lam in range(1 << d)}.values())


def pairwise_agrees(d: int, a: int, lam_a: int, b: int, lam_b: int) -> bool:
    return all(dot(lam_a, x) == dot(lam_b, x)
               for x in range(1 << d)
               if dot(a, x) == 0 and dot(b, x) == 0)


def global_character_exists(d: int, data: list[tuple[int, int]]) -> bool:
    return any(all(restriction(d, a, lam) == restriction(d, a, x)
                   for a, lam in data)
               for x in range(1 << d))


def census(d: int, k: int) -> tuple[int, int, tuple | None]:
    good = bad = 0
    witness = None
    for etas in combinations(range(1, 1 << d), k):
        options = [local_representatives(d, a) for a in etas]
        for assignments in product(*options):
            if all(pairwise_agrees(d, etas[i], assignments[i], etas[j], assignments[j])
                   for i, j in combinations(range(k), 2)):
                good += 1
                if not global_character_exists(d, list(zip(etas, assignments))):
                    bad += 1
                    if witness is None:
                        witness = (etas, assignments)
    return good, bad, witness


def main() -> None:
    targets = {(2, 2): (12, 0), (2, 3): (8, 4),
               (3, 2): (168, 0), (3, 3): (336, 56),
               (3, 4): (280, 0), (3, 5): (168, 0)}
    for (d, k), expected in targets.items():
        compatible, not_gluable, witness = census(d, k)
        assert (compatible, not_gluable) == expected, (d, k, compatible, not_gluable)
        print(f"rank={d} sign_characters={k} pairwise_compatible={compatible} "
              f"no_global_character={not_gluable}")
        if d == 2 and k == 3:
            assert witness is not None
            print(f"minimal_finite_countermodel={witness}")
    print("PASS: finite-family countermodel and positive controls")


if __name__ == "__main__":
    main()
