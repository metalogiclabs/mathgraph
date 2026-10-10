#!/usr/bin/env python3
"""Publish the exact qualified Resolve snapshot and deterministic kernel cases.

The pinned transport digest is the admission boundary, not the record's own
self-hash. This offline publisher neither authenticates new evidence nor reruns
JPL Lean. Runtime clients may select these precomputed cases only.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from mathgraph_check.living_warrants import canonical, verify_snapshot
from mathgraph_check.warrant_resolution import (
    Claim, Receipt, Route, compare_snapshots, resolve_graph,
)

RECORD_ID = "mg-living-warrant-openai-jpl-20261010"
SOURCE = ROOT / "evidence/living_warrant_openai_jpl_20261010.json"
TRANSPORT_SHA256 = "0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87"
SNAPSHOT_SHA256 = "b95297a081d513fb0ec145a776cc997eaed18109d6b2af39fa8e61f6d637af41"


def _admit_snapshot(raw: bytes) -> dict:
    if len(raw) != 5290 or sha256(raw).hexdigest() != TRANSPORT_SHA256:
        raise ValueError("SOURCE_BYTES_MISMATCH")
    snapshot = json.loads(raw)
    verify_snapshot(snapshot)
    if (snapshot["id"] != RECORD_ID
            or snapshot["snapshot_sha256"] != SNAPSHOT_SHA256
            or canonical(snapshot) + b"\n" != raw):
        raise ValueError("SOURCE_IDENTITY_MISMATCH")
    return snapshot


def _route_data(route: Route) -> dict:
    data = asdict(route)
    data["evidence"] = list(route.evidence)
    data["premises"] = list(route.premises)
    if data["relation"] is None:
        del data["relation"]
    return data


def _graph(claims, routes, receipts) -> dict:
    return {
        "claims": sorted((asdict(item) for item in claims), key=lambda item: item["id"]),
        "receipts": sorted((asdict(item) for item in receipts), key=lambda item: item["id"]),
        "routes": sorted((_route_data(item) for item in routes), key=canonical),
    }


def _scenario(id_, label, basis, claims, routes, receipts, withdrawn=()) -> dict:
    before = resolve_graph(claims, routes, receipts)
    after = resolve_graph(claims, routes, receipts, withdrawn=frozenset(withdrawn))
    return {
        "id": id_, "label": label, "basis": basis,
        "withdrawn_evidence": sorted(withdrawn),
        "states": dict(after.states),
        "resolutions": compare_snapshots(before.states, after.states),
        "active_routes": sorted((_route_data(route) for route in after.active_routes), key=canonical),
    }


def _published_record(snapshot: dict) -> dict:
    derivation = snapshot["derivation"]
    claims = [Claim(**item) for item in derivation["claims"]]
    receipts = [Receipt(**item) for item in derivation["receipts"]]
    routes = [Route(**item) for item in derivation["routes"]]
    graph = _graph(claims, routes, receipts)
    before = _scenario("modeled-before", "Modeled before publisher withdrawal",
                       "MODELED_BEFORE", claims, routes, receipts)
    before["description"] = snapshot["interpretation"]["simulated_before"]
    after = _scenario("published-after", "Published after publisher withdrawal",
                      "PUBLISHED_AFTER", claims, routes, receipts,
                      derivation["withdrawn_evidence"])
    after["baseline"] = "modeled-before"
    after["description"] = snapshot["interpretation"]["after"]
    if after["resolutions"] != snapshot["resolutions"]:
        raise ValueError("HISTORICAL_RESOLUTION_MISMATCH")
    scenarios = [before, after]
    for receipt in sorted(receipts, key=lambda item: item.id):
        scenario = _scenario(
            "withdraw-" + receipt.id, "Simulate withdrawal: " + receipt.id,
            "SIMULATION", claims, routes, receipts, (receipt.id,),
        )
        scenario["baseline"] = "modeled-before"
        scenario["description"] = (
            "Hypothetical single-dependency withdrawal from the modeled-before graph; "
            "not an additional historical event."
        )
        scenarios.append(scenario)
    return {
        "classification": "PUBLISHED_RECORD", "graph": graph,
        "default_scenario": "published-after",
        "scenarios": sorted(scenarios, key=lambda item: item["id"]),
    }


def _synthetic_conformance() -> dict:
    scope = "synthetic-conformance"
    claims = [Claim(name, "formal", scope) for name in "ABC"]
    receipts = [Receipt("r" + name, "formal", scope) for name in "ABC"]
    routes = [Route("A", ("rA",)), Route("B", ("rB",), ("A",)), Route("C", ("rC",))]
    alternative = routes + [Route("B", ("rB",), ("C",))]
    cycle = [Route("A", ("rA",), ("B",)), Route("B", ("rB",), ("A",))]
    scenarios = []
    for id_, label, case_claims, case_routes, case_receipts, withdrawn in (
        ("alternative-route", "Alternative support survives withdrawal", claims, alternative, receipts, ("rA",)),
        ("localized-invalidation", "Withdrawal changes only dependent support", claims, routes, receipts, ("rA",)),
        ("rootless-cycle", "A cycle without a qualified root stays UNKNOWN", claims[:2], cycle, receipts[:2], ()),
    ):
        scenario = _scenario(id_, label, "KERNEL_TEST", case_claims, case_routes, case_receipts, withdrawn)
        scenario["graph"] = _graph(case_claims, case_routes, case_receipts)
        scenario["description"] = "Synthetic kernel test, not a historical fact or newly verified mathematical claim."
        scenarios.append(scenario)
    return {
        "classification": "SYNTHETIC_CONFORMANCE", "purpose": "KERNEL_TESTS",
        "historical_fact": False,
        "description": "Synthetic kernel tests, not historical facts about OpenAI or JPL.",
        "scenarios": sorted(scenarios, key=lambda item: item["id"]),
    }


def build_scenarios(raw: bytes) -> dict:
    """Admit only the qualified snapshot; derive every status with the kernel."""
    snapshot = _admit_snapshot(raw)
    return {
        "schema": "mathgraph.resolve-scenarios.v1", "record_id": RECORD_ID,
        "transport_sha256": TRANSPORT_SHA256, "snapshot_sha256": SNAPSHOT_SHA256,
        "provenance": {
            "producer": {
                "repository": "metalogiclabs/mathgraph",
                "commit": "040456fc8862c79c8b384ce63846628274b678be",
                "run_id": "38025044631",
                "run_url": "https://github.com/metalogiclabs/mathgraph/actions/runs/38025044631",
            },
            "consumer": {
                "name": "RealityGraph", "repository": "heathsanchez/realitygraph",
                "commit": "9b3189a64825e2cb6ebc7b5c17f5f193bdf5cfe3",
                "run_id": "38025236380",
                "run_url": "https://github.com/heathsanchez/realitygraph/actions/runs/38025236380",
                "implementation_independent": True, "same_owner": True,
                "independently_owned_adoption": False, "reruns_jpl_lean_proof": False,
                "boundary": "Implementation-independent replay under the same owner; does not rerun the original JPL Lean proof.",
            },
            "integrity_boundary": "Pinned hashes detect byte substitution; self-hashes do not authenticate publishers or qualify new evidence.",
        },
        "maturity": {
            "lifecycle": "PUBLISHED_IMMUTABLE_SNAPSHOT",
            "research_maturity": "BOUNDED_REFERENCE_IMPLEMENTATION",
            "runtime_status": snapshot["interpretation"]["runtime_status"],
            "action_policy": "READ_ONLY_PRECOMPUTED_SELECTION",
        },
        "status_contract": {
            "states": "Raw kernel epistemic results at each claim's original kind and scope.",
            "resolutions": "Compared with the graph's no-withdrawal baseline (modeled-before for PUBLISHED_RECORD); STALE marks lost support, never theorem refutation.",
            "terminal_form_admission": "These warrant states do not accept new mathematical claims into the terminal-form kernel.",
        },
        "PUBLISHED_RECORD": _published_record(snapshot),
        "SYNTHETIC_CONFORMANCE": _synthetic_conformance(),
    }


def publish(source: Path = SOURCE, output_dir: Path = ROOT / "website", *, check: bool = False) -> None:
    """Write or byte-check all four artifacts after completing validation."""
    raw = source.read_bytes()
    scenarios = canonical(build_scenarios(raw)) + b"\n"
    evidence = output_dir / "public/evidence" / RECORD_ID
    artifacts = {
        output_dir / "src/data/resolve-record.json": raw,
        output_dir / "src/data/resolve-scenarios.json": scenarios,
        evidence / "record.json": raw,
        evidence / "scenarios.json": scenarios,
    }
    for path, content in artifacts.items():
        if check:
            if not path.is_file() or path.read_bytes() != content:
                raise ValueError("PUBLICATION_BYTES_MISMATCH: " + str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "website")
    parser.add_argument("--check", action="store_true", help="Compare existing files without writing")
    args = parser.parse_args()
    publish(args.source, args.output_dir, check=args.check)


if __name__ == "__main__":
    main()
