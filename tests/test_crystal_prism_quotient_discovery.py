from __future__ import annotations

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import urllib.request

from mathgraph.prism_adapter import (
    adapt_prism_imdp,
    reachability_state_extrema,
)
from mathgraph.prism_quotient_discovery import (
    discover_coarsest_reachability_quotient,
)


PINS = json.loads(
    Path("evidence/crystal-v1-source-pins.json").read_text(encoding="utf-8")
)["sources"]


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


def _adapt():
    pin = PINS["prism_uncertain_robot"]
    url = (
        "https://raw.githubusercontent.com/"
        f"{pin['repository']}/{pin['commit']}/{pin['path']}"
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "mathgraph-prism-quotient-discovery"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read()
    assert _git_blob_sha(data) == pin["blob_sha"]
    source_ref = (
        f"{pin['repository']}@{pin['commit']}:{pin['path']}"
        f"#gitblob={pin['blob_sha']}"
    )
    return adapt_prism_imdp(
        data.decode("utf-8"),
        delta="0.1",
        source_ref=source_ref,
    )


def test_exhaustive_discovery_finds_a_nontrivial_safe_quotient():
    adapted = _adapt()
    result = discover_coarsest_reachability_quotient(
        adapted.model,
        target_label="goal1",
    )

    assert result.tested_partitions == 52
    assert len(result.partition) < len(adapted.model.states)
    assert result.partition in result.coarsest_partitions
    assert result.coarser_partitions_rejected > 0


def test_discovered_quotient_preserves_every_state_protected_future():
    adapted = _adapt()
    result = discover_coarsest_reachability_quotient(
        adapted.model,
        target_label="goal1",
    )
    original = reachability_state_extrema(
        adapted.model,
        target_label="goal1",
    )
    reduced = reachability_state_extrema(
        result.quotient.model,
        target_label="goal1",
    )
    mapping = dict(result.state_map)

    for state in adapted.model.states:
        q = mapping[state]
        assert abs(original[state][0] - reduced[q][0]) < Decimal("1e-18")
        assert abs(original[state][1] - reduced[q][1]) < Decimal("1e-18")


def test_discovery_earns_dead_state_merge_but_rejects_s4_into_dead():
    adapted = _adapt()
    result = discover_coarsest_reachability_quotient(
        adapted.model,
        target_label="goal1",
    )
    mapping = dict(result.state_map)

    assert mapping["s2"] == mapping["s3"]
    assert mapping["s4"] != mapping["s2"]
    assert mapping["s5"] != mapping["s4"]
    assert mapping["s5"] != mapping["s2"]


def test_discovery_is_globally_coarsest_within_enumerated_boundary():
    adapted = _adapt()
    result = discover_coarsest_reachability_quotient(
        adapted.model,
        target_label="goal1",
    )

    min_classes = len(result.partition)
    assert all(
        len(partition) == min_classes
        for partition in result.coarsest_partitions
    )
    # Every target-respecting partition with fewer classes was tested and
    # rejected by the all-state protected-future preservation oracle.
    assert result.coarser_partitions_rejected > 0


def test_discovery_retains_exact_initial_prism_boundary():
    adapted = _adapt()
    result = discover_coarsest_reachability_quotient(
        adapted.model,
        target_label="goal1",
    )
    original = reachability_state_extrema(
        adapted.model,
        target_label="goal1",
    )
    reduced = reachability_state_extrema(
        result.quotient.model,
        target_label="goal1",
    )
    q0 = dict(result.state_map)["s0"]

    assert abs(original["s0"][0] - Decimal("0.4")) < Decimal("1e-12")
    assert abs(original["s0"][1] - Decimal("0.6")) < Decimal("1e-12")
    assert abs(reduced[q0][0] - original["s0"][0]) < Decimal("1e-18")
    assert abs(reduced[q0][1] - original["s0"][1]) < Decimal("1e-18")
