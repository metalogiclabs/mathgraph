#!/usr/bin/env python3
"""Exhaustive rank-two semisimple control for index-two character patching.

All models are ordinary complex representations of G=(Z/2Z)^d, encoded
as direct sums of two sign characters.  The kernels of nonzero linear
forms eta are normal index-two subgroups.  Compatibility checks equality
of traces on EVERY pairwise kernel intersection.  Globalization checks
all 2-dimensional semisimple representations of G.

This tests deliberately FINITE analogues; it does NOT refute or check
IndexTwoPatch.main, which requires infinitely many distinct eta.
"""
from itertools import combinations, combinations_with_replacement

def dot(a, b):
    return (a & b).bit_count() & 1

def trace(weights, g):
    return sum(1 if dot(a, g) == 0 else -1 for a in weights)

def ker(rank, eta):
    return tuple(g for g in range(1 << rank) if dot(eta, g) == 0)

def local_models(rank, eta):
    points = ker(rank, eta)
    choices = {}
    for weights in combinations_with_replacement(range(1 << rank), 2):
        k = tuple(trace(weights, g) for g in points)
        choices.setdefault(k, weights)
    return [(pat, weights) for pat, weights in sorted(choices.items())]

def compatible(rank, a, weights, b, other):
    return all(trace(weights, g) == trace(other, g)
               for g in range(1 << rank)
               if dot(a, g) == 0 and dot(b, g) == 0)

def all_global_models(rank):
    return tuple(combinations_with_replacement(range(1 << rank), 2))

def globalizes(rank, assignments):
    return any(all(all(trace(weights, g) == trace(candidate, g)
                       for g in ker(rank, eta))
                   for eta, weights in assignments)
               for candidate in all_global_models(rank))

def census(rank, count):
    all_signs = tuple(range(1, 1 << rank))
    models = {eta: local_models(rank, eta) for eta in all_signs}
    global_models = all_global_models(rank)
    global_masks = {
        eta: tuple(sum(1 << j for j, ws in enumerate(global_models)
                       if all(trace(ws, g) == pat[t] for t, g in enumerate(ker(rank, eta))))
                   for pat, _ in models[eta])
        for eta in all_signs
    }
    totals = [0, 0]
    witness = None
    for signs in combinations(all_signs, count):
        def recurse(i, chosen, mask):
            nonlocal witness
            if i == len(signs):
                totals[0] += 1
                if mask == 0:
                    totals[1] += 1
                    if witness is None:
                        witness = tuple(zip(signs, chosen))
                return
            eta = signs[i]
            for j, (_, weights) in enumerate(models[eta]):
                if all(compatible(rank, old_eta, old_weights, eta, weights)
                       for old_eta, old_weights in zip(signs[:i], chosen)):
                    recurse(i + 1, chosen + [weights], mask & global_masks[eta][j])
        recurse(0, [], (1 << len(global_models)) - 1)
    return tuple(totals), witness

def main():
    expected = {
        3: (1946, 686),
        4: (1596, 336),
        5: (924, 168),
        6: (280, 28),
        7: (36, 0),
    }
    for k, expected_result in expected.items():
        actual, witness = census(3, k)
        assert actual == expected_result, (k, actual, expected_result)
        print("rank=3 rep_dim=2 sign_characters=%d compatible=%d nongluable=%d" %
              (k, actual[0], actual[1]))
        if k == 6:
            assert witness is not None
            assert all(compatible(3, a, wa, b, wb)
                       for (a, wa), (b, wb) in combinations(witness, 2))
            assert not globalizes(3, witness)
            print("six_char_witness=%s" % (witness,))
            # Inflate the six local assignments to G=(C2)^4.
            # None of the nine unused new characters can be appended.
            for eta_new in range(7, 16):
                extensions = [weights for _, weights in local_models(4, eta_new)
                              if all(compatible(4, a, ws, eta_new, weights)
                                     for a, ws in witness)]
                assert not extensions, (eta_new, extensions)
            print("no_compatible_seventh_character_even_after_rank4_extension=9/9")
    print("PASS: rank-two finite patching obstruction and seventh-character controls")

if __name__ == "__main__":
    main()
