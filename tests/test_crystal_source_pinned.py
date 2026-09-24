from __future__ import annotations

import hashlib
import json
from pathlib import Path
import urllib.request

from mathgraph.crystal import (
    Hyperedge,
    action_quotient,
    find_quotient_falsifiers,
    greatest_viability_kernel,
    uncovered_failures,
)


PINS = json.loads(
    Path("evidence/crystal-v1-source-pins.json").read_text(encoding="utf-8")
)["sources"]


def _git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


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


def test_every_source_pin_matches_exact_git_blob():
    for name in PINS:
        assert _fetch(name)


def test_msi_real_quotient_witness_maps_without_new_fields():
    src = _fetch("msi_quotient")
    assert "k1 = (4, 0, 4, 0)" in src
    assert "k2 = (4, 4, 0, 0)" in src
    assert "finite_quotient_counterexample" in src

    k1 = (4, 0, 4, 0)
    k2 = (4, 4, 0, 0)

    def coarse(k):
        histogram = tuple(k.count(i) for i in range(5))
        multiplicity = 1
        import math
        for cls in k:
            multiplicity *= math.comb(4, cls)
        mean_numerator = sum(2 * cls - 4 for cls in k)
        return histogram, multiplicity, mean_numerator

    chi = (1, -1, 1, -1)

    def target(k):
        return sum(sign * (2 * cls - 4) for sign, cls in zip(chi, k))

    representation = {"k1": tuple(map(str, coarse(k1))), "k2": tuple(map(str, coarse(k2)))}
    protected = {"k1": (str(target(k1)),), "k2": (str(target(k2)),)}
    witnesses = find_quotient_falsifiers(representation, protected)
    assert coarse(k1) == coarse(k2) == ((2, 0, 0, 0, 2), 1, 0)
    assert (target(k1), target(k2)) == (16, 0)
    assert len(witnesses) == 1


def test_metatron_v5_real_hypergraph_and_cut_replay():
    src = _fetch("metatron_v5")
    assert "PATHS = (" in src
    assert "(1, (1, 2))" in src
    assert "set(mins) == {(0, 1), (1, 3), (2, 3)}" in src

    edges = [
        Hyperedge("q", "q", "0", frozenset({"0"})),
        Hyperedge("q", "q", "0", frozenset({"1"})),
        Hyperedge("q", "q", "1", frozenset({"1", "2"})),
        Hyperedge("q", "q", "1", frozenset({"3"})),
    ]
    caps = {"0", "1", "2", "3"}
    failures = ["0", "1"]

    assert uncovered_failures("q", failures, edges, caps) == ()
    for cap in caps:
        assert uncovered_failures("q", failures, edges, caps - {cap}) == ()

    pair_cuts = set()
    ordered = sorted(caps)
    for i, left in enumerate(ordered):
        for right in ordered[i + 1 :]:
            if uncovered_failures("q", failures, edges, caps - {left, right}):
                pair_cuts.add((int(left), int(right)))
    assert pair_cuts == {(0, 1), (1, 3), (2, 3)}

    residuals = uncovered_failures("q", failures, edges, {"0", "2"})
    assert [(r.failure_class, r.reason) for r in residuals] == [
        ("1", "no_live_supported_route")
    ]


def test_metatron_v7_real_stateful_viability_replay():
    src = _fetch("metatron_v7")
    assert 'STATES = (' in src
    assert '"ready",' in src
    assert 'return "depleted"' in src
    assert 'return "ready"' in src
    assert "[4,1,0,0]" in src.replace(" ", "")
    assert "[4,1,1]" in src.replace(" ", "")

    states = {"ready", "depleted", "unauthorized_ready", "unauthorized_depleted"}
    failures = ["0", "1"]
    one_shot = [
        Hyperedge("ready", "depleted", "0", frozenset({"0"})),
        Hyperedge("ready", "depleted", "1", frozenset({"0"})),
    ]
    replenished = [
        Hyperedge("ready", "ready", "0", frozenset({"0"})),
        Hyperedge("ready", "ready", "1", frozenset({"0"})),
    ]
    assert greatest_viability_kernel(states, failures, one_shot, {"0"}) == frozenset()
    assert greatest_viability_kernel(states, failures, replenished, {"0"}) == frozenset({"ready"})


def test_clc_real_certificate_identity_is_too_coarse_for_provenance():
    src = _fetch("clc_provenance")
    assert "CertificateProvenance Unit" in src
    assert "baselineLiveWarrant0" in src
    assert "baselineLiveWarrant3" in src
    assert "unit_certificate_identity_does_not_determine_warrant" in src

    # Exact CLC negative: the same Unit certificate identity can map to two
    # different live Metatron warrant indices. Certificate identity alone is
    # therefore an invalid quotient for provenance.
    representation = {"p0": ("Unit",), "p3": ("Unit",)}
    protected = {
        "p0": ("live-warrant", "0"),
        "p3": ("live-warrant", "3"),
    }
    witnesses = find_quotient_falsifiers(representation, protected)
    assert len(witnesses) == 1

    e0 = Hyperedge(
        "transport",
        "transport",
        "cert:Unit",
        frozenset({"warrant:0"}),
        evidence_refs=("CLC:Unit",),
    )
    e3 = Hyperedge(
        "transport",
        "transport",
        "cert:Unit",
        frozenset({"warrant:3"}),
        evidence_refs=("CLC:Unit",),
    )
    assert e0.id != e3.id


def test_arc_real_action_effect_quotient_replays_as_two_channels():
    src = _fetch("arc_generator_effects")
    assert 'A=(58,46); B=(58,11); C=(58,20); D=(58,22); E=(55,20)' in src
    assert 'KNOWN=[("A",A),("B",B),("C",C),("D",D),("E",E)]' in src
    assert PINS["arc_generator_effects"]["run"] == 35947695990

    # Exact qualified diagnostic at the pinned run: A/C/E leave source+panel
    # unchanged and act only on marker display; B/D change the source channel.
    induced = {
        ("canonical", "A"): "MARK",
        ("canonical", "B"): "SOURCE_TRANSFORM",
        ("canonical", "C"): "MARK",
        ("canonical", "D"): "SOURCE_TRANSFORM",
        ("canonical", "E"): "MARK",
    }
    classes = set(
        action_quotient(["A", "B", "C", "D", "E"], ["canonical"], induced).values()
    )
    assert classes == {("A", "C", "E"), ("B", "D")}


def test_arc_real_bd_dynamics_fit_same_transition_schema():
    src = _fetch("arc_bd_dynamics")
    assert 'OPS=[("B",B),("D",D)]' in src
    assert "paired_equivalence_checks" in src
    assert PINS["arc_bd_dynamics"]["run"] == 35947917695

    # Qualified result at the pinned run: q0={0,1}, qB={0,5}, qD={1,5};
    # B is a reset-to-qB operator and D a reset-to-qD operator.
    sources = ["q0", "qB", "qD"]
    induced = {}
    for source in sources:
        induced[(source, "B")] = "qB"
        induced[(source, "D")] = "qD"
    classes = set(action_quotient(["B", "D"], sources, induced).values())
    assert classes == {("B",), ("D",)}


def test_real_external_lean_capability_is_just_supported_transition_plus_residual():
    src = _fetch("lean_external_capability")
    assert 'START = "z2"' in src
    assert 'TERMINAL = "h1"' in src
    assert "DEPTH = 5" in src
    assert "BUDGET = 32" in src
    assert PINS["lean_external_capability"]["run"] == 35930875216

    # Hosted exact-run result: cold FAIL/32, learned-interface warm PASS/4,
    # kernel/elaborator-accepted witness q4-q0-q0-q0-q7. No Lean-specific
    # coordinate is needed in the crystal: a verified capability route exists
    # exactly when its learned-interface support is live.
    edge = Hyperedge(
        "z2",
        "h1",
        "synthesize",
        frozenset({"learned-interface"}),
        evidence_refs=(
            "github-run:35930875216",
            "lean-witness:q4-q0-q0-q0-q7",
        ),
    )
    assert uncovered_failures("z2", ["synthesize"], [edge], set())
    assert uncovered_failures(
        "z2", ["synthesize"], [edge], {"learned-interface"}
    ) == ()
