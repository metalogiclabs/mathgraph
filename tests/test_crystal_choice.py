from __future__ import annotations

import hashlib
import json
from pathlib import Path
import urllib.request

from mathgraph.crystal import Boundary, Hyperedge, find_quotient_falsifiers


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


def test_prism_mdp_source_has_coavailable_choices_at_same_state():
    src = _fetch("prism_mdp_mutual3")
    assert "mdp" in src
    assert "[] p1=0 -> (p1'=0);" in src
    assert "[] p1=0 -> (p1'=1);" in src


def test_resolver_quantifier_is_consequential_but_not_new_world_state():
    # Exact hosted PRISM gate on the pinned source gives:
    #   Pmin [F p1=1] = 0
    #   Pmax [F p1=1] = 1
    # The underlying state and available effects are identical.  What changes
    # is the resolver quantifier in the protected query boundary.
    representation_without_resolver = {
        "min": ("same-state", "same-effects"),
        "max": ("same-state", "same-effects"),
    }
    protected = {
        "min": ("reach-p1=1", "0.0"),
        "max": ("reach-p1=1", "1.0"),
    }
    witnesses = find_quotient_falsifiers(
        representation_without_resolver, protected
    )
    assert len(witnesses) == 1

    min_boundary = Boundary(
        "reach-p1=1",
        (("resolver", "min"),),
    )
    max_boundary = Boundary(
        "reach-p1=1",
        (("resolver", "max"),),
    )
    assert min_boundary.id != max_boundary.id

    # No new PRISM/scheduler-specific state coordinate is required. The same
    # two coavailable deterministic effects remain in the crystal; the
    # protected boundary determines how the external verifier resolves them.
    effects = (
        Hyperedge("p1=0", "p1=0", "choice"),
        Hyperedge("p1=0", "p1=1", "choice"),
    )
    assert effects[0].source == effects[1].source == "p1=0"
    assert {e.target for e in effects} == {"p1=0", "p1=1"}
