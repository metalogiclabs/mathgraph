from __future__ import annotations

import hashlib
import json
from pathlib import Path
import urllib.request

import pytest

from mathgraph.crystal import (
    IntervalDistributionEffect,
    IntervalOutcome,
    deterministic_effect,
    find_quotient_falsifiers,
)


PINS = json.loads(
    Path("evidence/crystal-v1-source-pins.json").read_text(encoding="utf-8")
)["sources"]


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _fetch(name: str) -> str:
    pin = PINS[name]
    url = (
        "https://raw.githubusercontent.com/"
        f"{pin['repository']}/{pin['commit']}/{pin['path']}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "mathgraph-crystal-gate"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
    assert _git_blob_sha(data) == pin["blob_sha"]
    return data.decode("utf-8")


def test_prism_source_contains_interval_valued_future():
    model = _fetch("prism_uncertain_robot")
    props = _fetch("prism_uncertain_robot_props")
    assert "[east] s=1 -> [0.8,0.9]:(s'=2) + [0.1,0.2]:(s'=1);" in model
    assert "const double p = 0.5-delta;" in model
    assert "const double q = 0.5+delta;" in model
    assert "Pmaxmin=? [ F \"goal1\" ];" in props
    assert "Pmaxmax=? [ F \"goal1\" ];" in props


def test_same_qualitative_support_can_hide_quantitative_separator():
    low = IntervalDistributionEffect(
        (
            IntervalOutcome("goal", "0.4", "0.4"),
            IntervalOutcome("other", "0.6", "0.6"),
        )
    )
    high = IntervalDistributionEffect(
        (
            IntervalOutcome("goal", "0.6", "0.6"),
            IntervalOutcome("other", "0.4", "0.4"),
        )
    )
    assert low.qualitative_support == high.qualitative_support == ("goal", "other")
    assert low.id != high.id

    witnesses = find_quotient_falsifiers(
        {
            "worst": low.qualitative_support,
            "best": high.qualitative_support,
        },
        {
            "worst": ("reachability", "0.4"),
            "best": ("reachability", "0.6"),
        },
    )
    assert len(witnesses) == 1


def test_prism_interval_effect_is_represented_without_prism_specific_fields():
    effect = IntervalDistributionEffect(
        (
            IntervalOutcome("s2", "0.8", "0.9"),
            IntervalOutcome("s1", "0.1", "0.2"),
        )
    )
    assert effect.qualitative_support == ("s1", "s2")
    assert effect.id.startswith("effect:")


def test_deterministic_transition_is_degenerate_interval_effect():
    effect = deterministic_effect("q1")
    assert effect.outcomes == (IntervalOutcome("q1", "1", "1"),)
    assert effect.qualitative_support == ("q1",)


def test_invalid_interval_distribution_is_rejected():
    with pytest.raises(ValueError):
        IntervalDistributionEffect(
            (
                IntervalOutcome("a", "0.8", "0.9"),
                IntervalOutcome("b", "0.3", "0.4"),
            )
        )
