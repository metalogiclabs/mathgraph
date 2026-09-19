from __future__ import annotations

import hashlib
import itertools
import json
import os
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
REALITYGRAPH_ROOT = Path(os.environ.get("REALITYGRAPH_BUS_ROOT", "_vendor/realitygraph_bus"))
CROSS_REP_SOURCE_ROOT = Path(os.environ.get("CROSS_REP_SOURCE_ROOT", "_vendor/cross_representation_source"))
sys.path.insert(0, str(REALITYGRAPH_ROOT))

from realitygraph.flash_bus import (
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

SOURCE_DOMAIN = "crossrep_source"
DEST_DOMAIN = "opaque"
SOURCE_KIND = "developmental-interface"
DEST_KIND = "compiled-interface"
BRIDGE_AUTHORITY = "probe-interface-genesis-v1"
BRIDGE_VERIFIER = "independent-complete-interface-attack"
ARRIVAL_AFTER_COLD_DEPTH = 6


def _digest(value, prefix="probe-interface-genesis-v1:"):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(prefix.encode() + raw).hexdigest()


@dataclass(frozen=True)
class ProbeTerm:
    name: str
    case: str
    size: int
    parent: str | None
    constructor: str


@dataclass(frozen=True)
class Discovery:
    proposed: bool
    mapping: tuple[tuple[str, str], ...]
    selected_probes: tuple[str, ...]
    synthesized_probes: tuple[str, ...]
    unused_generated_probes: tuple[str, ...]
    developmental_execution_evaluations: int
    hypothesis_counts: tuple[int, ...]
    probe_scores: tuple[tuple[str, int, int], ...]
    certificate_id: str | None
    attack_execution_evaluations: int
    attack_comparison_checks: int
    attack_passed: bool
    obstruction: str | None


def source_signatures(mod):
    return {
        role: tuple(mod.behavior(role, case) for case in mod.PROBE_CASES)
        for role in mod.SOURCE
    }


def target_signatures(mod, mode: str):
    exact = {
        token: tuple(
            mod.behavior(mod.TARGET_ROLE[token], case)
            for case in mod.PROBE_CASES
        )
        for token in mod.TARGET
    }
    if mode == "EXACT":
        return exact
    if mode == "MISMATCH":
        rows = dict(exact)
        v = list(rows["kp1"])
        v[-1] += 7
        rows["kp1"] = tuple(v)
        return rows
    if mode == "AMBIGUOUS":
        rows = dict(exact)
        rows["kp1"] = rows["rv4"]
        return rows
    raise ValueError(mode)


def initial_probe_terms():
    return {
        "empty": ProbeTerm("empty", "empty", 1, None, "primitive"),
        "one": ProbeTerm("one", "one", 1, None, "primitive"),
    }


def generated_frontier(selected: set[str]):
    out = {}
    if "one" in selected:
        out["two"] = ProbeTerm("two", "two", 2, "one", "count2")
        out["useful"] = ProbeTerm("useful", "useful", 2, "one", "advance")
    if "useful" in selected:
        out["opened"] = ProbeTerm("opened", "opened", 3, "useful", "open")
    if "opened" in selected:
        out["temporal"] = ProbeTerm("temporal", "temporal", 4, "opened", "temporalize")
    return out


def all_mappings(mod):
    return [
        dict(zip(mod.SOURCE, perm))
        for perm in itertools.permutations(mod.TARGET)
    ]


def observed_vector(mod, target, case: str):
    i = mod.PROBE_CASES.index(case)
    return tuple(target[token][i] for token in mod.TARGET)


def predicted_vector(mod, source, mapping, case: str):
    i = mod.PROBE_CASES.index(case)
    inverse = {token: role for role, token in mapping.items()}
    return tuple(source[inverse[token]][i] for token in mod.TARGET)


def filter_hypotheses(mod, source, target, hypotheses, cases):
    observed = {case: observed_vector(mod, target, case) for case in cases}
    out = []
    for mapping in hypotheses:
        if all(predicted_vector(mod, source, mapping, case) == observed[case] for case in cases):
            out.append(mapping)
    return out


def score_probe(mod, source, hypotheses, term: ProbeTerm):
    groups = {}
    for mapping in hypotheses:
        vector = predicted_vector(mod, source, mapping, term.case)
        groups[vector] = groups.get(vector, 0) + 1
    sizes = sorted(groups.values(), reverse=True)
    worst = sizes[0] if sizes else 0
    collision_mass = sum(n * n for n in sizes)
    return worst, collision_mass


def choose_probe(mod, source, hypotheses, candidates):
    scored = []
    for term in candidates:
        worst, collision_mass = score_probe(mod, source, hypotheses, term)
        scored.append((worst, collision_mass, term.size, term.name, term))
    scored.sort()
    return scored[0][-1], tuple((row[3], row[0], row[1]) for row in scored)


def executable_probe_cost(mod, terms):
    # Charge one source-role and one destination-token execution per selected probe.
    return len(terms) * (len(mod.SOURCE) + len(mod.TARGET))


def independent_attack(mod, source, target, mapping):
    if not mapping:
        return False, 0, 0
    execution_evals = 0
    comparisons = 0
    for case in mod.PROBE_CASES:
        i = mod.PROBE_CASES.index(case)
        source_values = {}
        target_values = {}
        for role in mod.SOURCE:
            execution_evals += 1
            source_values[role] = source[role][i]
        for token in mod.TARGET:
            execution_evals += 1
            target_values[token] = target[token][i]

        for role in mod.SOURCE:
            for token in mod.TARGET:
                comparisons += 1
                eq = source_values[role] == target_values[token]
                if mapping[role] == token:
                    if not eq:
                        return False, execution_evals, comparisons
                elif all(
                    source[role][j] == target[token][j]
                    for j in range(len(mod.PROBE_CASES))
                ):
                    return False, execution_evals, comparisons
    return True, execution_evals, comparisons


def adaptive_discovery(mod, target_mode: str, grammar_mode: str = "FULL"):
    source = source_signatures(mod)
    target = target_signatures(mod, target_mode)
    hypotheses = all_mappings(mod)
    selected = ["empty", "one"]
    synthesized = []
    generated_seen = set()
    probe_scores = []

    hypotheses = filter_hypotheses(mod, source, target, hypotheses, selected)
    counts = [len(hypotheses)]

    if grammar_mode == "STATIC":
        pass
    elif grammar_mode == "SHAM":
        frontier = generated_frontier(set(selected))
        term = frontier["two"]
        generated_seen.add(term.name)
        selected.append(term.case)
        synthesized.append(term.name)
        hypotheses = filter_hypotheses(mod, source, target, hypotheses, [term.case])
        counts.append(len(hypotheses))
    elif grammar_mode == "FULL":
        while len(hypotheses) > 1:
            frontier = generated_frontier(set(selected))
            candidates = [
                term for name, term in frontier.items()
                if name not in selected and name not in generated_seen
            ]
            if not candidates:
                break

            chosen, scores = choose_probe(mod, source, hypotheses, candidates)
            probe_scores.extend(scores)
            generated_seen.update(term.name for term in candidates)
            selected.append(chosen.case)
            synthesized.append(chosen.name)
            hypotheses = filter_hypotheses(
                mod, source, target, hypotheses, [chosen.case]
            )
            counts.append(len(hypotheses))
            if not hypotheses:
                break
    else:
        raise ValueError(grammar_mode)

    proposed = len(hypotheses) == 1
    mapping = tuple(sorted(hypotheses[0].items())) if proposed else ()
    selected_terms = [ProbeTerm(x, x, 1 if x in {"empty", "one"} else 2, None, "selected") for x in selected]
    developmental_evals = executable_probe_cost(mod, selected_terms)

    attack_passed = False
    attack_evals = 0
    attack_checks = 0
    certificate = None
    obstruction = None

    if proposed:
        attack_passed, attack_evals, attack_checks = independent_attack(
            mod, source, target, dict(mapping)
        )
        if attack_passed:
            certificate = _digest(
                {
                    "source": source,
                    "target_mode": target_mode,
                    "mapping": mapping,
                    "selected_probes": selected,
                    "full_probe_basis": list(mod.PROBE_CASES),
                },
                prefix="probe-genesis-certificate:",
            )
        else:
            obstruction = "INDEPENDENT_ATTACK_FAILED"
    elif not hypotheses:
        obstruction = "NO_BRIDGE_HYPOTHESIS_SURVIVES"
    else:
        obstruction = "OBSERVATION_LANGUAGE_INSUFFICIENT"

    return Discovery(
        proposed=proposed and attack_passed,
        mapping=mapping,
        selected_probes=tuple(selected),
        synthesized_probes=tuple(synthesized),
        unused_generated_probes=tuple(sorted(generated_seen - set(synthesized))),
        developmental_execution_evaluations=developmental_evals,
        hypothesis_counts=tuple(counts),
        probe_scores=tuple(probe_scores),
        certificate_id=certificate,
        attack_execution_evaluations=attack_evals,
        attack_comparison_checks=attack_checks,
        attack_passed=attack_passed,
        obstruction=obstruction,
    )


def bus():
    return GlobalFlashBus(
        domain_contracts=(
            DomainContract(SOURCE_DOMAIN, "crossrep-source-v1", "crossrep-source-verifier"),
            DomainContract(DEST_DOMAIN, "opaque-target-v1", "opaque-target-verifier"),
        ),
        bridge_contract=DomainContract("bridge", BRIDGE_AUTHORITY, BRIDGE_VERIFIER),
    )


def source_event(source_key):
    return EvidenceEvent(
        event_id="crossrep:procedure",
        domain=SOURCE_DOMAIN,
        consequence_kind=SOURCE_KIND,
        consequence_key=source_key,
        authority_snapshot="crossrep-source-v1",
        verifier_id="crossrep-source-verifier",
        provenance=f"commit:{CROSS_REP_SOURCE_COMMIT}",
    )


def run_arm(target_mode: str, grammar_mode: str, admit_certificate: bool = True, restart: bool = False):
    mod = _load_source()
    source = source_signatures(mod)
    source_key = "iface:" + _digest(source, "source:")
    target = target_signatures(mod, target_mode)
    target_key = "iface:" + _digest(target, "target:")

    prefix = cold_prefix(mod, ARRIVAL_AFTER_COLD_DEPTH)
    cold = mod.search()
    assert prefix["verifier_calls"] == 35290
    assert cold["verifier_calls"] == 222808

    b = bus()
    first = b.admit_event(source_event(source_key))
    assert first.cross_domain_edges == ()

    discovery = adaptive_discovery(mod, target_mode, grammar_mode)

    if restart:
        snap = {
            "prefix": prefix["verifier_calls"],
            "source_key": source_key,
            "target_key": target_key,
            "target_mode": target_mode,
            "grammar_mode": grammar_mode,
            "discovery": {
                "selected": list(discovery.selected_probes),
                "synthesized": list(discovery.synthesized_probes),
                "hypothesis_counts": list(discovery.hypothesis_counts),
            },
        }
        raw = json.dumps(snap, sort_keys=True, separators=(",", ":"))
        restored = json.loads(raw)
        if json.dumps(restored, sort_keys=True, separators=(",", ":")) != raw:
            raise AssertionError("probe-genesis restart is not exact")
        b = bus()
        b.admit_event(source_event(restored["source_key"]))
        discovery = adaptive_discovery(
            mod, restored["target_mode"], restored["grammar_mode"]
        )

    edge_count = 0
    suffix_calls = None
    final_calls = cold["verifier_calls"]
    status = "COLD_COMPLETE"

    if discovery.proposed and admit_certificate and discovery.certificate_id:
        bridge = BridgeCertificate(
            bridge_id="bridge:probe-genesis:crossrep->opaque:v1",
            source_domain=SOURCE_DOMAIN,
            source_kind=SOURCE_KIND,
            source_key=source_key,
            destination_domain=DEST_DOMAIN,
            destination_kind=DEST_KIND,
            destination_key=target_key,
            bridge_authority_snapshot=BRIDGE_AUTHORITY,
            bridge_verifier_id=BRIDGE_VERIFIER,
            certificate_id=discovery.certificate_id,
        )
        edges = b.admit_bridge(bridge)
        edge_count = len(edges)
        if edge_count == 1:
            macro = tuple(dict(discovery.mapping)[role] for role in mod.SOURCE_D2)
            suffix = incremental_macro_search(mod, macro, adapter_calls=0)
            suffix_calls = suffix["verifier_calls"]
            final_calls = prefix["verifier_calls"] + suffix_calls
            status = "RESOLVED_BY_PROBE_GENESIS_BRIDGE"

    payload = {
        "target_mode": target_mode,
        "grammar_mode": grammar_mode,
        "target_prefix_calls": prefix["verifier_calls"],
        "target_cold_calls": cold["verifier_calls"],
        "source_event_initial_edges": 0,
        "discovery": {
            "proposed": discovery.proposed,
            "mapping": [list(x) for x in discovery.mapping],
            "selected_probes": list(discovery.selected_probes),
            "synthesized_probes": list(discovery.synthesized_probes),
            "unused_generated_probes": list(discovery.unused_generated_probes),
            "developmental_execution_evaluations": discovery.developmental_execution_evaluations,
            "hypothesis_counts": list(discovery.hypothesis_counts),
            "probe_scores": [list(x) for x in discovery.probe_scores],
            "certificate_id": discovery.certificate_id,
            "attack_execution_evaluations": discovery.attack_execution_evaluations,
            "attack_comparison_checks": discovery.attack_comparison_checks,
            "attack_passed": discovery.attack_passed,
            "obstruction": discovery.obstruction,
        },
        "bridge_authority_execution_evaluations": (
            discovery.developmental_execution_evaluations
            + discovery.attack_execution_evaluations
        ),
        "edge_count": edge_count,
        "target_suffix_calls": suffix_calls,
        "target_final_calls": final_calls,
        "target_calls_avoided": cold["verifier_calls"] - final_calls,
        "status": status,
        "active_edges": [
            [
                e.source_event_id,
                e.destination_domain,
                e.destination_kind,
                e.bridge_id,
            ]
            for e in b.cross_domain_edges()
        ],
    }
    payload["digest"] = _digest(payload, "probe-arm:")
    return payload


def run():
    global_arm = run_arm("EXACT", "FULL")
    static = run_arm("EXACT", "STATIC")
    sham_grammar = run_arm("EXACT", "SHAM")
    mismatch = run_arm("MISMATCH", "FULL")
    ambiguous = run_arm("AMBIGUOUS", "FULL")
    withheld = run_arm("EXACT", "FULL", admit_certificate=False)
    restart = run_arm("EXACT", "FULL", restart=True)

    d = global_arm["discovery"]
    gates = {
        "target_live_before_probe_genesis": global_arm["target_prefix_calls"] == 35290,
        "source_event_initially_unbridged": global_arm["source_event_initial_edges"] == 0,
        "initial_observation_language_insufficient": (
            d["hypothesis_counts"][0] == 24
        ),
        "probe_genesis_selects_useful_then_opened": (
            d["synthesized_probes"] == ["useful", "opened"]
            and d["selected_probes"] == ["empty", "one", "useful", "opened"]
        ),
        "hypothesis_curve_24_2_1": d["hypothesis_counts"] == [24, 2, 1],
        "low_information_two_probe_not_selected": "two" in d["unused_generated_probes"],
        "unique_mapping_proposed": d["proposed"] and len(d["mapping"]) == 6,
        "independent_full_attack_passes": (
            d["attack_passed"]
            and d["attack_execution_evaluations"] == 72
            and d["attack_comparison_checks"] == 216
        ),
        "developmental_probe_evaluations_48": d["developmental_execution_evaluations"] == 48,
        "bridge_total_execution_evaluations_120": (
            global_arm["bridge_authority_execution_evaluations"] == 120
        ),
        "bridge_admission_resolves_live_target": (
            global_arm["edge_count"] == 1
            and global_arm["target_suffix_calls"] == 96
            and global_arm["target_final_calls"] == 35386
            and global_arm["target_calls_avoided"] == 187422
        ),
        "static_language_stays_ambiguous": (
            not static["discovery"]["proposed"]
            and static["discovery"]["hypothesis_counts"] == [24]
            and static["target_final_calls"] == 222808
        ),
        "sham_grammar_stays_ambiguous": (
            not sham_grammar["discovery"]["proposed"]
            and sham_grammar["discovery"]["hypothesis_counts"] == [24, 6]
            and sham_grammar["target_final_calls"] == 222808
        ),
        "mismatch_is_rejected_by_heldout_attack": (
            not mismatch["discovery"]["proposed"]
            and mismatch["discovery"]["obstruction"] == "INDEPENDENT_ATTACK_FAILED"
            and mismatch["target_final_calls"] == 222808
        ),
        "ambiguous_target_generates_obstruction": (
            not ambiguous["discovery"]["proposed"]
            and ambiguous["discovery"]["obstruction"] == "NO_BRIDGE_HYPOTHESIS_SURVIVES"
            and ambiguous["target_final_calls"] == 222808
        ),
        "withheld_certificate_restores_cold": (
            withheld["discovery"]["proposed"]
            and withheld["edge_count"] == 0
            and withheld["target_final_calls"] == 222808
        ),
        "restart_exact_bridge_outcome": (
            restart["discovery"]["certificate_id"] == d["certificate_id"]
            and restart["active_edges"] == global_arm["active_edges"]
            and restart["target_final_calls"] == global_arm["target_final_calls"]
        ),
    }
    gates["pass"] = all(gates.values())

    result = {
        "schema": "mathgraph.qckn.probe-interface-genesis.v1",
        "global": global_arm,
        "static_language_control": static,
        "sham_grammar_control": sham_grammar,
        "mismatch_target_control": mismatch,
        "ambiguous_target_control": ambiguous,
        "withheld_certificate_control": withheld,
        "restart_control": restart,
        "gates": gates,
        "scientific_verdict": (
            "PASS_VERIFIED_PROBE_INTERFACE_GENESIS"
            if gates["pass"]
            else "FAIL_PROBE_INTERFACE_GENESIS_V1"
        ),
        "boundary": (
            "Bounded finite active probe genesis over one source and one opaque destination. "
            "The probe grammar is supplied, but the useful probes are not selected in advance. "
            "The runtime starts from an insufficient two-probe observation language, scores generated "
            "probe terms by worst-case bridge-hypothesis reduction, synthesizes the useful probes, and "
            "requires a separate complete six-case attack before bridge admission. This does not establish "
            "open-ended invention of probe grammars, natural-language semantic discovery, or arbitrary domain matching."
        ),
    }
    result["digest_sha256"] = _digest(result, "probe-result:")
    return result


def main():
    r = run()
    (ROOT / "result.json").write_text(json.dumps(r, indent=2, sort_keys=True) + "\n")
    print("PROBE_INTERFACE_GENESIS_V1=" + r["scientific_verdict"])
    print("DISCOVERY=" + json.dumps(r["global"]["discovery"], sort_keys=True))
    print("TARGET=" + json.dumps({
        "prefix": r["global"]["target_prefix_calls"],
        "suffix": r["global"]["target_suffix_calls"],
        "final": r["global"]["target_final_calls"],
        "avoided": r["global"]["target_calls_avoided"],
    }, sort_keys=True))
    print("BRIDGE_AUTHORITY_EXECUTIONS=" + str(r["global"]["bridge_authority_execution_evaluations"]))
    print("CONTROLS=" + json.dumps({
        "static": r["static_language_control"]["discovery"]["hypothesis_counts"],
        "sham": r["sham_grammar_control"]["discovery"]["hypothesis_counts"],
        "mismatch": r["mismatch_target_control"]["discovery"]["obstruction"],
        "ambiguous": r["ambiguous_target_control"]["discovery"]["obstruction"],
        "withheld_final": r["withheld_certificate_control"]["target_final_calls"],
    }, sort_keys=True))
    print("DIGEST_SHA256=" + r["digest_sha256"])
    if not r["gates"]["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
