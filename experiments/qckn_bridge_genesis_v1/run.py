from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
REALITYGRAPH_ROOT = Path(os.environ.get("REALITYGRAPH_BUS_ROOT", "_vendor/realitygraph_bus"))
CROSS_REP_SOURCE_ROOT = Path(os.environ.get("CROSS_REP_SOURCE_ROOT", "_vendor/cross_representation_source"))
sys.path.insert(0, str(REALITYGRAPH_ROOT))

from realitygraph.flash_bus import (  # type: ignore
    BridgeCertificate,
    DomainContract,
    EvidenceEvent,
    GlobalFlashBus,
)

from experiments.qckn_cross_representation_flash_v1.run import (
    _load_source,
    cold_prefix,
    incremental_macro_search,
)

REALITYGRAPH_BUS_COMMIT = "021ffaac9baec0257f0eda1961d58e1360fb6ae4"
CROSS_REP_SOURCE_COMMIT = "feb55aad0ab80fb9c51110367c3cc34869764dd0"
CROSS_REP_SOURCE_ARTIFACT = 10265656833
CROSS_REP_SOURCE_ARTIFACT_DIGEST = "sha256:86e7dc456daae4da807b2b6cac87a2659c2dfe88c526dab6607565ef17e8b7d9"

SOURCE_DOMAIN = "crossrep_source"
DEST_DOMAIN = "opaque"
SOURCE_KIND = "developmental-interface"
DEST_KIND = "compiled-interface"
BRIDGE_AUTHORITY = "bridge-genesis-v1"
BRIDGE_VERIFIER = "complete-behavioural-bijection"
ARRIVAL_AFTER_COLD_DEPTH = 6


def _digest(value, prefix="bridge-genesis-v1:"):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(prefix.encode() + raw).hexdigest()


@dataclass(frozen=True)
class TargetInterface:
    interface_id: str
    signatures: tuple[tuple[str, tuple[int, ...]], ...]

    @property
    def signature_map(self):
        return dict(self.signatures)

    @property
    def fingerprint(self):
        return _digest(
            {
                "interface_id": self.interface_id,
                "signatures": [[k, list(v)] for k, v in self.signatures],
            },
            prefix="target-interface:",
        )


@dataclass(frozen=True)
class DiscoveryResult:
    admitted: bool
    target_interface_id: str | None
    mapping: tuple[tuple[str, str], ...]
    behavior_probe_calls: int
    complete_probe_basis: bool
    unique_target: bool
    unique_bijection: bool
    rejected_interfaces: tuple[str, ...]
    certificate_id: str | None


def source_signatures(mod):
    return {
        role: tuple(mod.behavior(role, case) for case in mod.PROBE_CASES)
        for role in mod.SOURCE
    }


def exact_target_interface(mod):
    rows = []
    for token in mod.TARGET:
        role = mod.TARGET_ROLE[token]
        rows.append((token, tuple(mod.behavior(role, case) for case in mod.PROBE_CASES)))
    return TargetInterface("opaque-exact-v1", tuple(rows))


def mismatch_target_interface(mod):
    base = dict(exact_target_interface(mod).signatures)
    row = list(base["kp1"])
    row[-1] = row[-1] + 7
    base["kp1"] = tuple(row)
    return TargetInterface("opaque-mismatch-v1", tuple(sorted(base.items())))


def ambiguous_target_interface(mod):
    base = dict(exact_target_interface(mod).signatures)
    base["kp1"] = base["rv4"]  # EXTEND disappears; PAIR now has two surface realizers.
    return TargetInterface("opaque-ambiguous-v1", tuple(sorted(base.items())))


def interface_fingerprint(signatures):
    return _digest(
        [[k, list(v)] for k, v in sorted(signatures.items())],
        prefix="source-interface:",
    )


def discover_one(source, target: TargetInterface, probe_indices):
    tmap = target.signature_map
    matches = {}
    calls = 0
    for role, ssig in sorted(source.items()):
        candidates = []
        for token, tsig in sorted(tmap.items()):
            equal = True
            for i in probe_indices:
                calls += 1
                if ssig[i] != tsig[i]:
                    equal = False
            if equal:
                candidates.append(token)
        matches[role] = tuple(candidates)

    unique = (
        all(len(v) == 1 for v in matches.values())
        and len({v[0] for v in matches.values()}) == len(matches)
    )
    mapping = tuple(sorted((role, vals[0]) for role, vals in matches.items())) if unique else ()
    return unique, mapping, calls, matches


def independent_attack(source, target: TargetInterface, mapping, probe_count):
    """Certify the proposed bridge against the complete frozen matrix.

    Mapped pairs must agree on every probe. Every nonmapped source/target pair
    must have at least one separating probe, proving uniqueness of the bijection.
    """
    if probe_count <= 0:
        raise ValueError("empty probe basis")
    tmap = target.signature_map
    mapped = dict(mapping)
    calls = 0
    positive = 0
    negative_separators = 0

    if set(mapped) != set(source):
        return False, calls, positive, negative_separators
    if len(set(mapped.values())) != len(mapped):
        return False, calls, positive, negative_separators

    for role, ssig in sorted(source.items()):
        for token, tsig in sorted(tmap.items()):
            mismatches = 0
            for i in range(probe_count):
                calls += 1
                if ssig[i] != tsig[i]:
                    mismatches += 1
            if mapped[role] == token:
                if mismatches:
                    return False, calls, positive, negative_separators
                positive += probe_count
            else:
                if not mismatches:
                    return False, calls, positive, negative_separators
                negative_separators += 1

    return True, calls, positive, negative_separators


def discover_bridge(mod, portfolio, *, probe_count=None):
    source = source_signatures(mod)
    full_probe_count = len(mod.PROBE_CASES)
    if probe_count is None:
        probe_count = full_probe_count
    probe_indices = tuple(range(probe_count))
    complete = probe_count == full_probe_count

    accepted = []
    rejected = []
    total_calls = 0
    attacks = {}

    for target in portfolio:
        unique, mapping, calls, _ = discover_one(source, target, probe_indices)
        total_calls += calls
        if not unique or not complete:
            rejected.append(target.interface_id)
            continue
        ok, attack_calls, positives, negatives = independent_attack(
            source, target, mapping, full_probe_count
        )
        total_calls += attack_calls
        attacks[target.interface_id] = {
            "attack_calls": attack_calls,
            "positive_probe_equalities": positives,
            "negative_pair_separators": negatives,
        }
        if ok:
            accepted.append((target, mapping))
        else:
            rejected.append(target.interface_id)

    unique_target = len(accepted) == 1
    if not unique_target:
        return DiscoveryResult(
            False,
            None,
            (),
            total_calls,
            complete,
            False,
            False,
            tuple(sorted(set(rejected) | {x.interface_id for x, _ in accepted})),
            None,
        ), attacks

    target, mapping = accepted[0]
    certificate_id = _digest(
        {
            "source_fingerprint": interface_fingerprint(source),
            "target_fingerprint": target.fingerprint,
            "mapping": mapping,
            "probe_cases": list(mod.PROBE_CASES),
        },
        prefix="bridge-certificate:",
    )
    return DiscoveryResult(
        True,
        target.interface_id,
        mapping,
        total_calls,
        complete,
        True,
        True,
        tuple(sorted(rejected)),
        certificate_id,
    ), attacks


def make_bus(source_key, dest_key):
    return GlobalFlashBus(
        domain_contracts=(
            DomainContract(SOURCE_DOMAIN, "crossrep-source-v1", "crossrep-source-verifier"),
            DomainContract(DEST_DOMAIN, "opaque-target-v1", "opaque-target-verifier"),
        ),
        bridge_contract=DomainContract(
            "bridge", BRIDGE_AUTHORITY, BRIDGE_VERIFIER
        ),
    )


def source_event(source_key):
    return EvidenceEvent(
        event_id="crossrep:learned-procedure",
        domain=SOURCE_DOMAIN,
        consequence_kind=SOURCE_KIND,
        consequence_key=source_key,
        authority_snapshot="crossrep-source-v1",
        verifier_id="crossrep-source-verifier",
        provenance=(
            f"commit:{CROSS_REP_SOURCE_COMMIT};"
            f"artifact:{CROSS_REP_SOURCE_ARTIFACT};"
            f"digest:{CROSS_REP_SOURCE_ARTIFACT_DIGEST}"
        ),
    )


def bridge_from_discovery(result: DiscoveryResult, source_key, dest_key):
    if not result.admitted or result.certificate_id is None:
        raise ValueError("cannot materialize uncertified bridge")
    return BridgeCertificate(
        bridge_id="bridge:genesis:crossrep->opaque:v1",
        source_domain=SOURCE_DOMAIN,
        source_kind=SOURCE_KIND,
        source_key=source_key,
        destination_domain=DEST_DOMAIN,
        destination_kind=DEST_KIND,
        destination_key=dest_key,
        bridge_authority_snapshot=BRIDGE_AUTHORITY,
        bridge_verifier_id=BRIDGE_VERIFIER,
        certificate_id=result.certificate_id,
    )


def compiled_macro(mod, result: DiscoveryResult):
    mapping = dict(result.mapping)
    return tuple(mapping[role] for role in mod.SOURCE_D2)


def run_arm(mode: str):
    mod = _load_source()
    source = source_signatures(mod)
    src_key = "iface:" + interface_fingerprint(source)
    exact = exact_target_interface(mod)
    dest_key = "iface:" + exact.fingerprint

    # Target work starts before either source event routing or bridge discovery.
    prefix = cold_prefix(mod, ARRIVAL_AFTER_COLD_DEPTH)
    assert prefix["correct"] is False
    assert prefix["verifier_calls"] == 35290

    cold = mod.search()
    bus = make_bus(src_key, dest_key)
    first_delta = bus.admit_event(source_event(src_key))
    assert first_delta.cross_domain_edges == ()

    portfolio = (exact, mismatch_target_interface(mod), ambiguous_target_interface(mod))
    discovery = None
    attacks = {}
    edge_count = 0
    suffix_calls = None
    final_calls = cold["verifier_calls"]
    status = "COLD_COMPLETE"

    if mode == "GLOBAL":
        discovery, attacks = discover_bridge(mod, portfolio)
        if discovery.admitted:
            bridge = bridge_from_discovery(discovery, src_key, dest_key)
            edges = bus.admit_bridge(bridge)
            edge_count = len(edges)
            if edge_count == 1:
                macro = compiled_macro(mod, discovery)
                suffix = incremental_macro_search(mod, macro, adapter_calls=0)
                suffix_calls = suffix["verifier_calls"]
                final_calls = prefix["verifier_calls"] + suffix_calls
                status = "RESOLVED_BY_DISCOVERED_BRIDGE"

    elif mode == "WITHHOLD":
        discovery, attacks = discover_bridge(mod, portfolio)
        # Exact certificate exists but is deliberately withheld from the bus.

    elif mode == "INCOMPLETE":
        discovery, attacks = discover_bridge(mod, portfolio, probe_count=1)

    elif mode == "NO_EXACT_TARGET":
        discovery, attacks = discover_bridge(
            mod, (mismatch_target_interface(mod), ambiguous_target_interface(mod))
        )

    elif mode == "AMBIGUOUS_ONLY":
        # Duplicate the exact interface under a second opaque identity. Even
        # though each supports a bijection, destination selection is not unique.
        twin = TargetInterface("opaque-exact-twin-v1", exact.signatures)
        discovery, attacks = discover_bridge(mod, (exact, twin))

    elif mode == "RESTART":
        # Restart after source event but before bridge discovery.
        snapshot = {
            "source_event_id": "crossrep:learned-procedure",
            "target_prefix_calls": prefix["verifier_calls"],
            "source_key": src_key,
            "dest_key": dest_key,
        }
        raw = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
        restored = json.loads(raw)
        if json.dumps(restored, sort_keys=True, separators=(",", ":")) != raw:
            raise AssertionError("bridge-genesis restart snapshot not exact")

        bus = make_bus(restored["source_key"], restored["dest_key"])
        bus.admit_event(source_event(restored["source_key"]))
        discovery, attacks = discover_bridge(mod, portfolio)
        if discovery.admitted:
            edges = bus.admit_bridge(
                bridge_from_discovery(discovery, restored["source_key"], restored["dest_key"])
            )
            edge_count = len(edges)
            macro = compiled_macro(mod, discovery)
            suffix = incremental_macro_search(mod, macro, adapter_calls=0)
            suffix_calls = suffix["verifier_calls"]
            final_calls = restored["target_prefix_calls"] + suffix_calls
            status = "RESOLVED_BY_DISCOVERED_BRIDGE"

    else:
        raise ValueError(mode)

    if discovery is None:
        discovery_payload = None
        bridge_probes = 0
    else:
        discovery_payload = {
            "admitted": discovery.admitted,
            "target_interface_id": discovery.target_interface_id,
            "mapping": [list(x) for x in discovery.mapping],
            "behavior_probe_calls": discovery.behavior_probe_calls,
            "complete_probe_basis": discovery.complete_probe_basis,
            "unique_target": discovery.unique_target,
            "unique_bijection": discovery.unique_bijection,
            "rejected_interfaces": list(discovery.rejected_interfaces),
            "certificate_id": discovery.certificate_id,
        }
        bridge_probes = discovery.behavior_probe_calls

    payload = {
        "mode": mode,
        "source_and_target_surface_names_disjoint": set(mod.SOURCE).isdisjoint(mod.TARGET),
        "target_cold_prefix_calls": prefix["verifier_calls"],
        "target_cold_full_calls": cold["verifier_calls"],
        "bridge_search_started_after_target_prefix": True,
        "source_event_had_zero_edges_before_genesis": True,
        "discovery": discovery_payload,
        "attack_details": attacks,
        "edge_count": edge_count,
        "target_suffix_calls_after_bridge": suffix_calls,
        "target_final_verifier_calls": final_calls,
        "target_calls_avoided": cold["verifier_calls"] - final_calls,
        "bridge_behavior_probe_calls": bridge_probes,
        "status": status,
        "active_bus_edges": [
            [
                e.source_event_id,
                e.destination_domain,
                e.destination_kind,
                e.destination_key,
                e.bridge_id,
            ]
            for e in bus.cross_domain_edges()
        ],
    }
    payload["digest"] = _digest(payload, prefix="bridge-arm:")
    return payload


def run():
    global_arm = run_arm("GLOBAL")
    withheld = run_arm("WITHHOLD")
    incomplete = run_arm("INCOMPLETE")
    no_exact = run_arm("NO_EXACT_TARGET")
    ambiguous = run_arm("AMBIGUOUS_ONLY")
    restart = run_arm("RESTART")

    d = global_arm["discovery"]
    gates = {
        "target_started_before_bridge_search": (
            global_arm["target_cold_prefix_calls"] == 35290
            and global_arm["bridge_search_started_after_target_prefix"]
        ),
        "source_event_initially_has_no_edge": global_arm["source_event_had_zero_edges_before_genesis"],
        "surface_names_disjoint": global_arm["source_and_target_surface_names_disjoint"],
        "unique_bridge_discovered": (
            d is not None
            and d["admitted"]
            and d["target_interface_id"] == "opaque-exact-v1"
            and d["unique_target"]
            and d["unique_bijection"]
        ),
        "complete_mapping_has_six_roles": d is not None and len(d["mapping"]) == 6,
        "decoy_interfaces_rejected": (
            d is not None
            and set(d["rejected_interfaces"]) == {
                "opaque-ambiguous-v1",
                "opaque-mismatch-v1",
            }
        ),
        "bridge_materializes_only_after_discovery": global_arm["edge_count"] == 1,
        "discovered_bridge_resolves_live_target": (
            global_arm["status"] == "RESOLVED_BY_DISCOVERED_BRIDGE"
            and global_arm["target_suffix_calls_after_bridge"] == 96
            and global_arm["target_final_verifier_calls"] == 35386
            and global_arm["target_calls_avoided"] == 187422
        ),
        "bridge_search_is_fully_charged": global_arm["bridge_behavior_probe_calls"] == 864,
        "withholding_certificate_restores_cold": (
            withheld["discovery"]["admitted"]
            and withheld["edge_count"] == 0
            and withheld["target_final_verifier_calls"] == 222808
        ),
        "incomplete_probe_basis_cannot_admit": (
            not incomplete["discovery"]["admitted"]
            and incomplete["edge_count"] == 0
            and incomplete["target_final_verifier_calls"] == 222808
        ),
        "no_exact_target_cannot_admit": (
            not no_exact["discovery"]["admitted"]
            and no_exact["edge_count"] == 0
        ),
        "ambiguous_destination_cannot_admit": (
            not ambiguous["discovery"]["admitted"]
            and ambiguous["edge_count"] == 0
        ),
        "restart_reproduces_exact_target_outcome": (
            restart["target_final_verifier_calls"] == global_arm["target_final_verifier_calls"]
            and restart["target_calls_avoided"] == global_arm["target_calls_avoided"]
            and restart["active_bus_edges"] == global_arm["active_bus_edges"]
            and restart["discovery"]["certificate_id"] == global_arm["discovery"]["certificate_id"]
        ),
    }
    gates["pass"] = all(gates.values())

    result = {
        "schema": "mathgraph.qckn.bridge-genesis.v1",
        "source_authority": {
            "cross_representation_commit": CROSS_REP_SOURCE_COMMIT,
            "artifact_id": CROSS_REP_SOURCE_ARTIFACT,
            "artifact_digest": CROSS_REP_SOURCE_ARTIFACT_DIGEST,
            "global_bus_commit": REALITYGRAPH_BUS_COMMIT,
        },
        "global": global_arm,
        "withheld_certificate_control": withheld,
        "incomplete_probe_control": incomplete,
        "no_exact_target_control": no_exact,
        "ambiguous_destination_control": ambiguous,
        "restart_control": restart,
        "gates": gates,
        "scientific_verdict": (
            "PASS_VERIFIED_BRIDGE_GENESIS"
            if gates["pass"]
            else "FAIL_BRIDGE_GENESIS_V1"
        ),
        "boundary": (
            "Bounded finite bridge genesis over a declared portfolio of opaque target interfaces and a complete "
            "six-case behavioural probe basis. The bridge is not predeclared: a source event is already present "
            "and the destination target is already live before discovery. Admission requires a unique complete "
            "behavioural bijection plus an independent exhaustive attack. This does not establish open-ended "
            "semantic analogy discovery, natural-language ontology matching, or arbitrary cross-domain transfer."
        ),
    }
    result["digest_sha256"] = _digest(result, prefix="bridge-result:")
    return result


def main():
    r = run()
    (ROOT / "result.json").write_text(json.dumps(r, indent=2, sort_keys=True) + "\n")
    print("BRIDGE_GENESIS_V1=" + r["scientific_verdict"])
    print("DISCOVERY=" + json.dumps(r["global"]["discovery"], sort_keys=True))
    print("EDGE=" + json.dumps(r["global"]["active_bus_edges"], sort_keys=True))
    print("TARGET=" + json.dumps({
        "prefix": r["global"]["target_cold_prefix_calls"],
        "suffix": r["global"]["target_suffix_calls_after_bridge"],
        "final": r["global"]["target_final_verifier_calls"],
        "avoided": r["global"]["target_calls_avoided"],
    }, sort_keys=True))
    print("CONTROLS=" + json.dumps({
        "withheld": r["withheld_certificate_control"]["target_final_verifier_calls"],
        "incomplete_admitted": r["incomplete_probe_control"]["discovery"]["admitted"],
        "no_exact_admitted": r["no_exact_target_control"]["discovery"]["admitted"],
        "ambiguous_admitted": r["ambiguous_destination_control"]["discovery"]["admitted"],
    }, sort_keys=True))
    print("DIGEST_SHA256=" + r["digest_sha256"])
    if not r["gates"]["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
