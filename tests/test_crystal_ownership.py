from __future__ import annotations

import hashlib
import json
from pathlib import Path
import urllib.request

from mathgraph.crystal import Boundary, ControlMap, find_quotient_falsifiers


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


def test_prism_games_source_is_exact_mixed_ownership_fixture():
    model = _fetch("prism_games_smg_example")
    props = _fetch("prism_games_smg_example_props")
    assert "smg" in model
    assert "player p1" in model
    assert "host, [send1], [send2]" in model
    assert "player p2" in model
    assert "client" in model
    assert "<<1>> Pmax=? [ F<=3 c=2 ]" in props


def test_same_boundary_and_effects_but_different_local_control_is_a_separator():
    # Exact hosted PRISM-games gate:
    # original ownership => 0.9775
    # host/client ownership swapped => 0.0
    # The protected query remains coalition <<1>>, Pmax, F<=3 c=2.
    boundary = Boundary(
        "Pmax[F<=3 c=2]",
        (("coalition", "p1"),),
    )

    representation_without_control = {
        "original": (boundary.id, "same-states", "same-effects"),
        "swapped": (boundary.id, "same-states", "same-effects"),
    }
    protected = {
        "original": ("reach-probability", "0.9775"),
        "swapped": ("reach-probability", "0.0"),
    }
    witnesses = find_quotient_falsifiers(
        representation_without_control, protected
    )
    assert len(witnesses) == 1

    original_control = ControlMap(
        (
            ("module:host", "p1"),
            ("action:send1", "p1"),
            ("action:send2", "p1"),
            ("module:client", "p2"),
        )
    )
    swapped_control = ControlMap(
        (
            ("module:host", "p2"),
            ("action:send1", "p2"),
            ("action:send2", "p2"),
            ("module:client", "p1"),
        )
    )

    assert original_control.id != swapped_control.id
    assert original_control.controller("module:host") == "p1"
    assert swapped_control.controller("module:host") == "p2"
    assert boundary.id == Boundary(
        "Pmax[F<=3 c=2]",
        (("coalition", "p1"),),
    ).id


def test_control_map_rejects_duplicate_choice_point():
    try:
        ControlMap((("choice:x", "p1"), ("choice:x", "p2")))
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate choice point should be rejected")
