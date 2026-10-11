"""Strict, dependency-free JSON decoding primitives."""

from __future__ import annotations

import json
import math
from typing import Any, IO


class DuplicateKeyError(ValueError):
    """Raised when a JSON object repeats a member name."""


class NonFiniteNumberError(ValueError):
    """Raised when JSON input contains a non-finite numeric value."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise NonFiniteNumberError(f"non-finite JSON number: {value}")
    return parsed


def _reject_constant(value: str) -> None:
    raise NonFiniteNumberError(f"non-finite JSON number: {value}")


def strict_json_loads(document: str | bytes | bytearray) -> Any:
    """Decode JSON while rejecting duplicate keys and non-finite numbers."""

    return json.loads(
        document,
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
        parse_float=_finite_float,
    )


def strict_json_load(handle: IO[str] | IO[bytes]) -> Any:
    """Decode strict JSON from an open text or binary file handle."""

    return strict_json_loads(handle.read())


__all__ = [
    "DuplicateKeyError",
    "NonFiniteNumberError",
    "strict_json_load",
    "strict_json_loads",
]
