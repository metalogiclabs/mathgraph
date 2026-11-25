"""Frozen numeric-identity probe; supplied RFC contract, no intent inference."""
import hashlib
import random
import struct

MINIMUM = -(2**64)
MAXIMUM = 2**64 - 1
BUDGET = 1000
SEEDS = (2601126, 2601127, 2601128, 2601129, 2601130)


def head(major, argument):
    if type(argument) is not int or not 0 <= argument <= MAXIMUM:
        raise ValueError("argument outside core integer range")
    prefix = major << 5
    if argument < 24:
        return bytes([prefix | argument])
    for width, additional in ((1, 24), (2, 25), (4, 26), (8, 27)):
        if argument < 1 << (width * 8):
            return bytes([prefix | additional]) + argument.to_bytes(width, "big")
    raise AssertionError("unreachable")


def encode(value):
    if type(value) is int:
        return head(0, value) if value >= 0 else head(1, -1 - value)
    if type(value) is list:
        return head(4, len(value)) + b"".join(encode(x) for x in value)
    if type(value) is dict:
        return head(5, len(value)) + b"".join(encode(k) + encode(v) for k, v in value.items())
    raise TypeError("frozen grammar supports only integers, lists and integer-key maps")


def reference(raw):
    """Separate struct-based reader; never invokes a target decoder."""
    def read(at):
        first = raw[at]
        major, additional = first >> 5, first & 31
        at += 1
        if additional < 24:
            argument = additional
        else:
            width, fmt = {24: (1, ">B"), 25: (2, ">H"), 26: (4, ">I"), 27: (8, ">Q")}[additional]
            argument = struct.unpack_from(fmt, raw, at)[0]
            at += width
        if major == 0:
            return argument, at
        if major == 1:
            return -1 - argument, at
        if major == 4:
            values = []
            for _ in range(argument):
                value, at = read(at)
                values.append(value)
            return values, at
        if major == 5:
            values = {}
            for _ in range(argument):
                key, at = read(at)
                value, at = read(at)
                values[key] = value
            return values, at
        raise ValueError("unsupported major type")
    value, end = read(0)
    if end != len(raw):
        raise ValueError("unconsumed bytes")
    return value


def shaped(n, shape):
    return (n, [0, n, n, 1], {0: n, 1: 42})[shape]


def boundary_values():
    values = [2**53 + 1, -(2**53 + 1), 0, 1, -1, MINIMUM, MAXIMUM]
    for exponent in range(65):
        for delta in (-2, -1, 0, 1, 2):
            for n in (2**exponent + delta, -(2**exponent + delta)):
                if MINIMUM <= n <= MAXIMUM:
                    values.append(n)
    return list(dict.fromkeys(values))


def corpus(seed, budget=BUDGET):
    rng = random.Random(seed)
    values = boundary_values()
    for index in range(budget):
        n = values[index] if index < len(values) else rng.randint(MINIMUM, MAXIMUM)
        yield n, index % 3


def equal(actual, expected, strict=False):
    if type(expected) is int:
        return (not strict or type(actual) is int) and isinstance(actual, (int, float)) and actual == expected
    if type(expected) is list:
        return isinstance(actual, (list, tuple)) and len(actual) == len(expected) and all(equal(x, y, strict) for x, y in zip(actual, expected))
    if type(expected) is dict:
        return isinstance(actual, dict) and actual.keys() == expected.keys() and (not strict or all(type(k) is int for k in actual)) and all(equal(actual[k], expected[k], strict) for k in expected)
    return False


def observe(decoder, n, shape):
    expected = shaped(n, shape)
    raw = encode(expected)
    assert reference(raw) == expected
    try:
        actual = decoder(raw)
    except Exception as exc:
        return dict(n=str(n), shape=shape, hex=raw.hex(), status="REJECTED_INPUT", error=type(exc).__name__, message=str(exc)[:400])
    return dict(n=str(n), shape=shape, hex=raw.hex(), expected=repr(expected), observed=repr(actual),
                native_type=type(actual).__name__, exact=equal(actual, expected),
                strict_type=equal(actual, expected, strict=True),
                status="AGREEMENT" if equal(actual, expected) else "VALUE_DISCREPANCY")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()
