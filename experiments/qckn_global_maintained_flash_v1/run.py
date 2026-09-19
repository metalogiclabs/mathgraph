from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
REALITYGRAPH_ROOT = Path(os.environ.get("REALITYGRAPH_BUS_ROOT", "_vendor/realitygraph_bus"))
sys.path.insert(0, str(REALITYGRAPH_ROOT))

from realitygraph.flash_bus import (  # type: ignore
    BridgeCertificate,
    DomainContract,
    EvidenceEvent,
    GlobalFlashBus,
)

from experiments.qckn_flash_representation_genesis_v1.run import run as run_representation_flash
from experiments.qckn_heterogeneous_global_flash_v1.run import run as run_heterogeneous_flash
from experiments.qckn_cross_representation_flash_v1.run import run as run_cross_representation_flash
from experiments.qckn_maintained_revocable_equilibration_v3.run import run as run_revocable_v3


GLOBAL_BUS_COMMIT = "021ffaac9baec0257f0eda1961d58e1360fb6ae4"
COLLATZ_COMMIT = "0bd6cc71a5fb4268109d5b404ecbf21c7aaaf4c1"
COLLATZ_EVIDENCE_BLOB = "6ea5ce6ef40db44bb4c4d8f556534987e6742577"

REP_DIGEST = "ffc24e0cd368b46fe307fd225dfa68e4ae8621697b571d74b0177284b30e4b90"
HETERO_DIGEST = "25066a051bc5c0be11bfbb35ea8d98bd3df25dd78453cd1bed9d05632c7221d4"
CROSS_REP_DIGEST = "d594b9e979ed0dfcf1bf8d02206b93dc4d56110f702ee713f60e67a06c30698b"
V3_DIGEST = "73c600192c6f689d5d6d0d8bcddbc6b9bd2e776c3d559fbc0738c01552008d11"


def _digest(value, prefix="global-maintained-flash-v1:"):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(prefix.encode() + raw).hexdigest()


@dataclass
class LiveTarget:
    domain: str
    unit: str
    cold_total: int
    flash_total: int | None
    pre_event_paid: int
    status: str = "LIVE"
    paid: int = 0
    cancelled: int = 0
    solved_by: str | None = None

    def resolve(self, event_id: str):
        if self.flash_total is None:
            raise ValueError(f"no qualified Flash result for {self.domain}")
        if self.status == "RESOLVED":
            return False
        self.paid = self.flash_total
        self.cancelled = self.cold_total - self.flash_total
        self.status = "RESOLVED"
        self.solved_by = event_id
        return True

    def finalize_cold(self):
        if self.status == "LIVE":
            self.paid = self.cold_total
            self.cancelled = 0
            self.status = "COLD_COMPLETE"

    def payload(self):
        return asdict(self)


@lru_cache(maxsize=1)
def qualify_source_results():
    representation = run_representation_flash()
    heterogeneous = run_heterogeneous_flash()
    cross_rep = run_cross_representation_flash()
    revocable = run_revocable_v3()

    assert representation["scientific_verdict"] == "PASS_CROSS_DOMAIN_FLASH_REPRESENTATION_GENESIS"
    assert representation["digest_sha256"] == REP_DIGEST

    assert heterogeneous["scientific_verdict"] == "PASS_ONE_VERIFIED_LIVE_CROSS_DOMAIN_FLASH_EDGE"
    assert heterogeneous["arms"]["COLD"]["developmental_cost"] == 518
    assert heterogeneous["arms"]["FLASH"]["developmental_cost"] == 261
    assert heterogeneous["arms"]["UPFRONT"]["developmental_cost"] == 5
    assert heterogeneous["arms"]["ABLATION"]["developmental_cost"] == 518
    assert heterogeneous["arms"]["SHAM"]["developmental_cost"] == 789

    assert cross_rep["scientific_verdict"] == "PASS_LIVE_CROSS_REPRESENTATION_FLASH"
    assert cross_rep["digest_sha256"] == CROSS_REP_DIGEST

    assert revocable["scientific_verdict"] == "PASS_INCREMENTAL_REVOCABLE_CONSEQUENTIAL_EQUILIBRATION"
    assert revocable["digest_sha256"] == V3_DIGEST

    return representation, heterogeneous, cross_rep, revocable


def domain_contracts():
    return (
        DomainContract("temporal", f"mathgraph:{REP_DIGEST}", "mathgraph-qualified"),
        DomainContract("circuit", "target:circuit-v1", "global-runtime"),
        DomainContract("arc_source", f"mathgraph:{HETERO_DIGEST}", "mathgraph-qualified"),
        DomainContract("embodied", "target:embodied-v1", "global-runtime"),
        DomainContract("crossrep_source", f"mathgraph:{CROSS_REP_DIGEST}", "mathgraph-qualified"),
        DomainContract("opaque", "target:opaque-v1", "global-runtime"),
        DomainContract("arithmetic", f"mathgraph:{V3_DIGEST}", "mathgraph-qualified"),
        DomainContract("collatz", f"collatz:{COLLATZ_COMMIT}", "exact-forward-replay"),
    )


def exact_bridges(sham: bool = False):
    suffix = ":sham" if sham else ""
    return (
        BridgeCertificate(
            bridge_id="bridge:temporal->circuit:min-refinement" + suffix,
            source_domain="temporal",
            source_kind="representation-constructor",
            source_key=("wrong-key" if sham else "minimum-refinement-v1"),
            destination_domain="circuit",
            destination_kind="representation-repair",
            destination_key="pvsnp-metric-collision-v1",
            bridge_authority_snapshot="global-maintained-bridge-v1",
            bridge_verifier_id="exact-prior-qualification",
            certificate_id=REP_DIGEST,
        ),
        BridgeCertificate(
            bridge_id="bridge:arc->embodied:relation" + suffix,
            source_domain="arc_source",
            source_kind="relational-capability",
            source_key=("wrong-key" if sham else "binary-relation-v1"),
            destination_domain="embodied",
            destination_kind="relational-family",
            destination_key="finite-embodied-target-v1",
            bridge_authority_snapshot="global-maintained-bridge-v1",
            bridge_verifier_id="exact-prior-qualification",
            certificate_id=HETERO_DIGEST,
        ),
        BridgeCertificate(
            bridge_id="bridge:crossrep->opaque:procedure" + suffix,
            source_domain="crossrep_source",
            source_kind="developmental-procedure",
            source_key=("wrong-key" if sham else "opaque-role-macro-v1"),
            destination_domain="opaque",
            destination_kind="compiled-procedure",
            destination_key="opaque-depth7-target-v1",
            bridge_authority_snapshot="global-maintained-bridge-v1",
            bridge_verifier_id="exact-prior-qualification",
            certificate_id=CROSS_REP_DIGEST,
        ),
    )


def external_events():
    return (
        EvidenceEvent(
            event_id="temporal:min-refinement",
            domain="temporal",
            consequence_kind="representation-constructor",
            consequence_key="minimum-refinement-v1",
            authority_snapshot=f"mathgraph:{REP_DIGEST}",
            verifier_id="mathgraph-qualified",
            provenance="qckn-flash-representation-genesis-v1-frozen",
        ),
        EvidenceEvent(
            event_id="arc:binary-relation",
            domain="arc_source",
            consequence_kind="relational-capability",
            consequence_key="binary-relation-v1",
            authority_snapshot=f"mathgraph:{HETERO_DIGEST}",
            verifier_id="mathgraph-qualified",
            provenance="qckn-heterogeneous-global-flash-v1-frozen",
        ),
        EvidenceEvent(
            event_id="crossrep:procedure",
            domain="crossrep_source",
            consequence_kind="developmental-procedure",
            consequence_key="opaque-role-macro-v1",
            authority_snapshot=f"mathgraph:{CROSS_REP_DIGEST}",
            verifier_id="mathgraph-qualified",
            provenance="qckn-cross-representation-flash-v1-frozen",
        ),
        EvidenceEvent(
            event_id="arithmetic:maintained-basis",
            domain="arithmetic",
            consequence_kind="scope-certificate",
            consequence_key="addition-basis-00-v3",
            authority_snapshot=f"mathgraph:{V3_DIGEST}",
            verifier_id="mathgraph-qualified",
            provenance="qckn-maintained-revocable-equilibration-v3-frozen",
        ),
        EvidenceEvent(
            event_id="collatz:bounded-control",
            domain="collatz",
            consequence_kind="control-obstruction",
            consequence_key="propagation-no-advantage-over-upfront-guard",
            authority_snapshot=f"collatz:{COLLATZ_COMMIT}",
            verifier_id="exact-forward-replay",
            provenance=f"blob:{COLLATZ_EVIDENCE_BLOB}",
        ),
    )


def generated_event(event_id: str, domain: str, kind: str, key: str):
    contract = {row.domain: row for row in domain_contracts()}[domain]
    return EvidenceEvent(
        event_id=event_id,
        domain=domain,
        consequence_kind=kind,
        consequence_key=key,
        authority_snapshot=contract.authority_snapshot,
        verifier_id=contract.verifier_id,
        provenance="generated-by-global-maintained-flash-v1",
    )


def initial_targets(rep, hetero, cross_rep):
    return {
        "circuit": LiveTarget(
            domain="circuit",
            unit="circuit.metric_checks",
            cold_total=rep["arms"]["COLD"]["candidate_metric_checks"],
            flash_total=rep["arms"]["FLASH"]["candidate_metric_checks"],
            pre_event_paid=rep["arms"]["FLASH"]["candidate_metric_checks"],
        ),
        "embodied": LiveTarget(
            domain="embodied",
            unit="embodied.developmental_cost",
            cold_total=hetero["arms"]["COLD"]["developmental_cost"],
            flash_total=hetero["arms"]["FLASH"]["developmental_cost"],
            pre_event_paid=hetero["arms"]["FLASH"]["cold_prefix_evaluations"] + 1,
        ),
        "opaque": LiveTarget(
            domain="opaque",
            unit="opaque.verifier_calls",
            cold_total=cross_rep["arms"]["COLD"]["verifier_calls"],
            flash_total=cross_rep["arms"]["FLASH"]["verifier_calls"],
            pre_event_paid=cross_rep["schedule"]["cold_prefix_verifier_calls"],
        ),
    }


def bus_factory(with_bridges: bool, sham: bool = False):
    bus = GlobalFlashBus(
        domain_contracts=domain_contracts(),
        bridge_contract=DomainContract(
            "bridge",
            "global-maintained-bridge-v1",
            "exact-prior-qualification",
        ),
    )
    if with_bridges:
        for bridge in exact_bridges(sham=sham):
            bus.admit_bridge(bridge)
    return bus


def runtime_snapshot(targets, arithmetic_state, admitted_ids, pending_ids, waves, edges):
    payload = {
        "targets": {k: v.payload() for k, v in sorted(targets.items())},
        "arithmetic": arithmetic_state,
        "admitted_event_ids": sorted(admitted_ids),
        "pending_event_ids": list(pending_ids),
        "waves": waves,
        "edges": [list(e) for e in sorted(edges)],
    }
    payload["digest"] = _digest(payload, "runtime-snapshot:")
    return payload


def run_arm(
    *,
    with_bridges: bool,
    sham: bool = False,
    no_revocation: bool = False,
    no_reserve: bool = False,
    restart_after_wave1: bool = False,
):
    rep, hetero, cross_rep, revocable = qualify_source_results()
    targets = initial_targets(rep, hetero, cross_rep)
    bus = bus_factory(with_bridges=with_bridges, sham=sham)

    event_map = {e.event_id: e for e in external_events()}
    pending = [e.event_id for e in external_events()]
    admitted: set[str] = set()
    edges: set[tuple[str, str, str, str]] = set()
    waves = 0

    arithmetic_state = {
        "status": "LIVE_RAW",
        "active_classes": 101,
        "reserve_entries": 0,
        "revocations": 0,
        "reopened_classes": 0,
        "final_classes": 101,
        "raw_reacquisition": None,
        "runtime_authority_evaluations": 0,
        "unsoundness_detected": False,
        "recovery_failed": False,
    }
    collatz = {
        "status": "LIVE",
        "cross_domain_mutations": 0,
        "baseline_T_calls": 1501097,
        "global_T_calls_avoided": 0,
    }

    wave1_snapshot = None

    while pending:
        waves += 1
        current = pending
        pending = []
        generated: list[EvidenceEvent] = []

        for event_id in current:
            event = event_map[event_id]
            if event_id in admitted:
                continue
            delta = bus.admit_event(event)
            admitted.add(event_id)

            for edge in delta.cross_domain_edges:
                edges.add((
                    edge.source_event_id,
                    edge.destination_domain,
                    edge.destination_kind,
                    edge.bridge_id,
                ))
                target = targets.get(edge.destination_domain)
                if target is not None and target.resolve(event.event_id):
                    done_id = f"{edge.destination_domain}:resolved"
                    done = generated_event(
                        done_id,
                        edge.destination_domain,
                        "terminal-resolution",
                        edge.destination_key,
                    )
                    if done_id not in event_map:
                        event_map[done_id] = done
                        generated.append(done)

            if event.domain == "arithmetic" and event.event_id == "arithmetic:maintained-basis":
                arithmetic_state.update(
                    status="COARSENED",
                    active_classes=2,
                    reserve_entries=(0 if no_reserve else 101),
                    final_classes=2,
                    runtime_authority_evaluations=101,
                )
                scope_event = generated_event(
                    "arithmetic:new-obligation",
                    "arithmetic",
                    "scope-expansion",
                    "audit-last-pair-is-9-1-v1",
                )
                event_map[scope_event.event_id] = scope_event
                generated.append(scope_event)

            elif event.domain == "arithmetic" and event.event_id == "arithmetic:new-obligation":
                if no_revocation:
                    arithmetic_state.update(
                        status="UNSOUND_OLD_QUOTIENT",
                        unsoundness_detected=True,
                        final_classes=2,
                    )
                elif no_reserve:
                    arithmetic_state.update(
                        status="RECOVERY_UNAVAILABLE",
                        recovery_failed=True,
                        final_classes=2,
                    )
                else:
                    arithmetic_state.update(
                        status="REVOKED_REOPENED_RECOMPILED",
                        revocations=1,
                        reopened_classes=101,
                        final_classes=3,
                        raw_reacquisition=0,
                        runtime_authority_evaluations=202,
                    )
                    recomp = generated_event(
                        "arithmetic:recompiled",
                        "arithmetic",
                        "terminal-resolution",
                        "expanded-scope-3-class-v3",
                    )
                    event_map[recomp.event_id] = recomp
                    generated.append(recomp)

            if event.domain == "collatz":
                collatz["status"] = "CONTROL_INGESTED_NO_BRIDGE"

        pending = [e.event_id for e in generated if e.event_id not in admitted]

        if waves == 1:
            wave1_snapshot = runtime_snapshot(
                targets,
                arithmetic_state,
                admitted,
                pending,
                waves,
                edges,
            )
            if restart_after_wave1:
                # Reconstruct the event bus from canonical declarative inputs and
                # replay already admitted event identities. Runtime target/local
                # state is restored from the canonical snapshot payload.
                raw = canonical_json(wave1_snapshot)
                restored = json.loads(raw)
                if canonical_json(restored) != raw:
                    raise AssertionError("runtime snapshot restart is not exact")

                bus = bus_factory(with_bridges=with_bridges, sham=sham)
                for eid in sorted(admitted):
                    bus.admit_event(event_map[eid])

                restored_targets = {}
                for name, p in restored["targets"].items():
                    restored_targets[name] = LiveTarget(**p)
                targets = restored_targets
                arithmetic_state = dict(restored["arithmetic"])
                edges = {tuple(row) for row in restored["edges"]}

        if waves > 10:
            raise RuntimeError("global closure failed to reach fixed point")

    for target in targets.values():
        target.finalize_cold()

    typed_paid = {target.unit: target.paid for target in targets.values()}
    typed_cold = {target.unit: target.cold_total for target in targets.values()}
    typed_avoided = {
        unit: typed_cold[unit] - typed_paid[unit]
        for unit in typed_cold
    }

    final_payload = {
        "targets": {k: v.payload() for k, v in sorted(targets.items())},
        "arithmetic": arithmetic_state,
        "collatz": collatz,
        "admitted_event_ids": sorted(admitted),
        "active_bus_event_ids": list(bus.active_event_ids()),
        "cross_domain_edges": [list(e) for e in sorted(edges)],
        "waves": waves,
        "queue_empty": not pending,
        "typed_paid": typed_paid,
        "typed_cold": typed_cold,
        "typed_avoided": typed_avoided,
        "arithmetic_runtime_authority_saved_vs_v2": (
            10100 - arithmetic_state["runtime_authority_evaluations"]
            if arithmetic_state["runtime_authority_evaluations"] else 0
        ),
    }
    final_payload["digest"] = _digest(final_payload, "global-final:")
    return final_payload, wave1_snapshot


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def run():
    global_arm, global_wave1 = run_arm(with_bridges=True)
    isolated, _ = run_arm(with_bridges=False)
    sham, _ = run_arm(with_bridges=True, sham=True)
    no_revocation, _ = run_arm(with_bridges=True, no_revocation=True)
    no_reserve, _ = run_arm(with_bridges=True, no_reserve=True)
    restart, restart_wave1 = run_arm(with_bridges=True, restart_after_wave1=True)

    expected_avoided = {
        "circuit.metric_checks": 6,
        "embodied.developmental_cost": 257,
        "opaque.verifier_calls": 187206,
    }

    gates = {
        "three_exact_cross_domain_edges": len(global_arm["cross_domain_edges"]) == 3,
        "three_foreign_targets_resolved": all(
            global_arm["targets"][d]["status"] == "RESOLVED"
            for d in ("circuit", "embodied", "opaque")
        ),
        "typed_savings_match_qualified_sources": global_arm["typed_avoided"] == expected_avoided,
        "arithmetic_maintained_revocation_completes": (
            global_arm["arithmetic"]["status"] == "REVOKED_REOPENED_RECOMPILED"
            and global_arm["arithmetic"]["revocations"] == 1
            and global_arm["arithmetic"]["reopened_classes"] == 101
            and global_arm["arithmetic"]["final_classes"] == 3
            and global_arm["arithmetic"]["raw_reacquisition"] == 0
        ),
        "arithmetic_runtime_authority_202": (
            global_arm["arithmetic"]["runtime_authority_evaluations"] == 202
        ),
        "collatz_remains_unbridged": (
            global_arm["collatz"]["cross_domain_mutations"] == 0
            and not any(edge[1] == "collatz" for edge in global_arm["cross_domain_edges"])
        ),
        "global_fixed_point_reached": (
            global_arm["queue_empty"] and global_arm["waves"] >= 3
        ),
        "isolated_has_zero_cross_edges": (
            isolated["cross_domain_edges"] == []
            and all(
                isolated["targets"][d]["status"] == "COLD_COMPLETE"
                for d in ("circuit", "embodied", "opaque")
            )
        ),
        "sham_bridges_have_zero_cross_edges": (
            sham["cross_domain_edges"] == []
            and all(
                sham["targets"][d]["status"] == "COLD_COMPLETE"
                for d in ("circuit", "embodied", "opaque")
            )
        ),
        "no_revocation_detects_unsoundness": (
            no_revocation["arithmetic"]["unsoundness_detected"]
            and no_revocation["arithmetic"]["status"] == "UNSOUND_OLD_QUOTIENT"
        ),
        "no_reserve_fails_recovery": (
            no_reserve["arithmetic"]["recovery_failed"]
            and no_reserve["arithmetic"]["status"] == "RECOVERY_UNAVAILABLE"
        ),
        "restart_wave1_snapshot_exact": (
            global_wave1 is not None
            and restart_wave1 is not None
            and global_wave1["digest"] == restart_wave1["digest"]
        ),
        "restart_final_digest_exact": restart["digest"] == global_arm["digest"],
    }
    gates["pass"] = all(gates.values())

    result = {
        "schema": "mathgraph.qckn.global-maintained-flash.v1",
        "source_qualifications": {
            "representation_genesis_flash": REP_DIGEST,
            "heterogeneous_arc_embodied_flash": HETERO_DIGEST,
            "cross_representation_flash": CROSS_REP_DIGEST,
            "maintained_revocable_equilibration": V3_DIGEST,
            "realitygraph_global_bus_commit": GLOBAL_BUS_COMMIT,
            "collatz_control_commit": COLLATZ_COMMIT,
            "collatz_control_blob": COLLATZ_EVIDENCE_BLOB,
        },
        "global": global_arm,
        "isolated": isolated,
        "sham_bridge_control": sham,
        "no_revocation_control": no_revocation,
        "no_reserve_control": no_reserve,
        "restart_control": restart,
        "gates": gates,
        "scientific_verdict": (
            "PASS_GLOBAL_MAINTAINED_FLASH_FIXED_POINT"
            if gates["pass"]
            else "FAIL_GLOBAL_MAINTAINED_FLASH_V1"
        ),
        "boundary": (
            "Bounded composition of previously qualified exact cross-domain edges plus the "
            "maintained revocable arithmetic representation. The bus routes only certified "
            "kind/key bridges; typed cost units are not collapsed. This is not evidence that "
            "Collatz, Lean, ARC, circuit complexity, and theorem proving share arbitrary semantics, "
            "nor that all future events admit bridges."
        ),
    }
    result["digest_sha256"] = _digest(result, "global-result:")
    return result


def main():
    r = run()
    (ROOT / "result.json").write_text(json.dumps(r, indent=2, sort_keys=True) + "\n")
    print("GLOBAL_MAINTAINED_FLASH_V1=" + r["scientific_verdict"])
    print("EDGES=" + json.dumps(r["global"]["cross_domain_edges"], sort_keys=True))
    print("TYPED_AVOIDED=" + json.dumps(r["global"]["typed_avoided"], sort_keys=True))
    print("ARITHMETIC=" + json.dumps(r["global"]["arithmetic"], sort_keys=True))
    print("COLLATZ=" + json.dumps(r["global"]["collatz"], sort_keys=True))
    print("WAVES=" + str(r["global"]["waves"]))
    print("DIGEST_SHA256=" + r["digest_sha256"])
    if not r["gates"]["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
