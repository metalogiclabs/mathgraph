from __future__ import annotations

import hashlib
import json
from pathlib import Path
import urllib.request

from mathgraph.crystal import ObservationMap, find_quotient_falsifiers


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


def test_prism_guess_source_exposes_only_s_not_hidden_h():
    model = _fetch("prism_pomdp_guess")
    props = _fetch("prism_pomdp_guess_props")
    assert "pomdp" in model
    assert "observables s endobservables" in model
    assert "h : [0..3]; // hidden var" in model
    assert "Pmax=? [ F \"correct\" ];" in props


def test_partial_observer_merges_hidden_states_full_observer_splits_them():
    underlying = ("s1-h1", "s1-h2", "s1-h3")

    partial = ObservationMap(
        tuple((state, "s=1") for state in underlying)
    )
    full = ObservationMap(
        tuple((state, state) for state in underlying)
    )

    assert partial.classes == {"s=1": underlying}
    assert set(full.classes) == set(underlying)
    assert partial.id != full.id


def test_observation_partition_is_consequential_under_protected_future():
    # Exact external PRISM gate at the pinned source gives max success 0.6
    # when h is hidden and 1.0 when the same dynamics are fully observable.
    representation = {
        "partial": ("same-underlying-dynamics", "same-effects"),
        "full": ("same-underlying-dynamics", "same-effects"),
    }
    protected = {
        "partial": ("Pmax(correct)", "0.6"),
        "full": ("Pmax(correct)", "1.0"),
    }
    witnesses = find_quotient_falsifiers(representation, protected)
    assert len(witnesses) == 1


def test_observation_map_rejects_duplicate_underlying_state():
    try:
        ObservationMap((("x", "a"), ("x", "b")))
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate observation state should be rejected")
