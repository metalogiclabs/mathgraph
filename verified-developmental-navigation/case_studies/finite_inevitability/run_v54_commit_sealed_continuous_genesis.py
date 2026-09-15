#!/usr/bin/env python3
"""V54 commit-sealed continuous capability-genesis census.

Can one continuously operating developer, with no task-specific repair family,
turn exact residuals into multiple retained capabilities and later reuse them
on future tasks, while task selection is route-neutral and every truth-bearing
step is exactly checked?

Finite exhaustive causal calibration only; not a natural external-task or
open-ended intelligence claim.

Declared world:
* X = 3 hidden states
* C = 3 binary continuations
* every 3x3 binary observation table (512)
* every initial one-continuation interface (3 per table)
* all 27 deterministic X->X maps as the one generic operator universe
* all 27 two-input partial transition obligations as the one task universe

Task order is frozen by the Git commit SHA, table index, and initial
continuation. The selector never receives route or retained state.

Generic developer for every task:
1. REUSE if retained generated capability already solves it.
2. Else exhaust every lawful one-operator extension under the current quotient.
3. Only if that complete class is inadequate, exhaust every one-coordinate
   interface refinement and every operator under it.
4. Otherwise return UNKNOWN.

Every retained state is serialized/deserialized before the next task.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

X = tuple(range(3))
C = tuple(range(3))
IDENTITY = tuple(X)
ALL_FUNCTIONS = tuple(itertools.product(X, repeat=len(X)))
TASK_UNIVERSE = tuple(
    ((x1, y1), (x2, y2))
    for x1 in X
    for x2 in X
    if x1 < x2
    for y1 in X
    for y2 in X
)


def canonical_hash(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def all_tables():
    for bits in itertools.product((0, 1), repeat=len(X) * len(C)):
        yield tuple(tuple(bits[i * len(C):(i + 1) * len(C)]) for i in X)


def profile(table, x, basis):
    return tuple(table[x][c] for c in basis)


def quotient_classes(table, basis):
    buckets = defaultdict(list)
    for x in X:
        buckets[profile(table, x, basis)].append(x)
    return tuple(sorted(tuple(v) for v in buckets.values()))


def class_id(classes):
    return {x: i for i, block in enumerate(classes) for x in block}


def quotient_congruent(table, basis, f):
    classes = quotient_classes(table, basis)
    cid = class_id(classes)
    return all(len({cid[f[x]] for x in block}) == 1 for block in classes)


def compose(f, g):
    return tuple(f[g[x]] for x in X)


@lru_cache(maxsize=None)
def _generated_monoid_cached(generator_key):
    seen = {IDENTITY, *generator_key}
    frontier = list(seen)
    while frontier:
        new_f = frontier.pop()
        current = tuple(seen)
        for g in current:
            for h in (compose(new_f, g), compose(g, new_f)):
                if h not in seen:
                    seen.add(h)
                    frontier.append(h)
    return frozenset(seen)


def generated_monoid(generators):
    return _generated_monoid_cached(tuple(sorted(set(generators))))


def task_satisfied(f, task):
    return all(f[x] == y for x, y in task)


def task_solved(generators, task):
    return any(task_satisfied(f, task) for f in generated_monoid(generators))


def mdl_key(f):
    return (sum(f[i] != i for i in X), f)


def serialize_state(basis, generators):
    return json.dumps(
        {"basis": list(basis), "generators": [list(g) for g in generators]},
        sort_keys=True,
        separators=(",", ":"),
    )


def deserialize_state(payload):
    row = json.loads(payload)
    return tuple(row["basis"]), tuple(tuple(g) for g in row["generators"])


def frozen_task_stream(seal, table_index, initial_continuation):
    tasks = list(TASK_UNIVERSE)
    digest = hashlib.sha256(
        f"{seal}:{table_index}:{initial_continuation}".encode()
    ).digest()
    random.Random(int.from_bytes(digest[:8], "big")).shuffle(tasks)
    return tuple(tasks)


@dataclass(frozen=True)
class Mutation:
    route: str
    basis_before: tuple[int, ...]
    basis_after: tuple[int, ...]
    generators_before: tuple[tuple[int, ...], ...]
    generators_after: tuple[tuple[int, ...], ...]
    selected_operator: tuple[int, ...] | None = None
    selected_continuation: int | None = None
    old_exact_lawful_candidates: int = 0
    new_exact_lawful_candidates: int = 0


def lawful_operator_extensions(table, basis, generators, task):
    before = generated_monoid(generators)
    candidates = []
    for f in ALL_FUNCTIONS:
        if f in before:
            continue
        if not quotient_congruent(table, basis, f):
            continue
        if not task_satisfied(f, task):
            continue
        after = generated_monoid(generators + (f,))
        if len(after) > len(before):
            candidates.append((mdl_key(f), -len(after), f, after))
    candidates.sort()
    return candidates


def develop_one(table, basis, generators, task):
    before = generated_monoid(generators)
    if any(task_satisfied(f, task) for f in before):
        return Mutation(
            "REUSE", basis, basis, generators, generators
        )

    direct = lawful_operator_extensions(table, basis, generators, task)
    if direct:
        f = direct[0][2]
        return Mutation(
            "EXPAND_OPERATOR",
            basis,
            basis,
            generators,
            generators + (f,),
            selected_operator=f,
            old_exact_lawful_candidates=len(direct),
            new_exact_lawful_candidates=len(direct),
        )

    refinements = []
    for c in C:
        if c in basis:
            continue
        b1 = tuple(sorted(basis + (c,)))
        exact = lawful_operator_extensions(table, b1, generators, task)
        if exact:
            f = exact[0][2]
            refinements.append(
                (c, mdl_key(f), -len(exact[0][3]), b1, f, len(exact))
            )
    refinements.sort()
    if refinements:
        c, _, _, b1, f, n_new = refinements[0]
        return Mutation(
            "EXPAND_INTERFACE_OPERATOR",
            basis,
            b1,
            generators,
            generators + (f,),
            selected_operator=f,
            selected_continuation=c,
            old_exact_lawful_candidates=0,
            new_exact_lawful_candidates=n_new,
        )

    return Mutation("UNKNOWN", basis, basis, generators, generators)


def verify_mutation(table, task, mutation):
    before = generated_monoid(mutation.generators_before)
    after = generated_monoid(mutation.generators_after)
    before_solved = any(task_satisfied(f, task) for f in before)
    after_solved = any(task_satisfied(f, task) for f in after)

    if mutation.route == "REUSE":
        return (
            before_solved
            and after_solved
            and mutation.generators_before == mutation.generators_after
        )

    if mutation.route == "EXPAND_OPERATOR":
        f = mutation.selected_operator
        return bool(
            not before_solved
            and after_solved
            and f is not None
            and quotient_congruent(table, mutation.basis_before, f)
            and task_satisfied(f, task)
            and len(after) > len(before)
            and mutation.basis_before == mutation.basis_after
        )

    if mutation.route == "EXPAND_INTERFACE_OPERATOR":
        f = mutation.selected_operator
        return bool(
            not before_solved
            and after_solved
            and f is not None
            and mutation.old_exact_lawful_candidates == 0
            and mutation.new_exact_lawful_candidates > 0
            and not quotient_congruent(table, mutation.basis_before, f)
            and quotient_congruent(table, mutation.basis_after, f)
            and len(quotient_classes(table, mutation.basis_after))
                > len(quotient_classes(table, mutation.basis_before))
            and task_satisfied(f, task)
            and len(after) > len(before)
        )

    if mutation.route == "UNKNOWN":
        return not before_solved and not after_solved

    return False


def mutation_dict(step_index, task, mutation):
    return {
        "step": step_index,
        "task": [list(x) for x in task],
        "route": mutation.route,
        "basis_before": list(mutation.basis_before),
        "basis_after": list(mutation.basis_after),
        "generators_before": [list(x) for x in mutation.generators_before],
        "generators_after": [list(x) for x in mutation.generators_after],
        "selected_operator":
            list(mutation.selected_operator)
            if mutation.selected_operator is not None else None,
        "selected_continuation": mutation.selected_continuation,
        "monoid_before": len(generated_monoid(mutation.generators_before)),
        "monoid_after": len(generated_monoid(mutation.generators_after)),
        "old_exact_lawful_candidates": mutation.old_exact_lawful_candidates,
        "new_exact_lawful_candidates": mutation.new_exact_lawful_candidates,
    }


def run_stream(table, table_index, initial_continuation, seal):
    task_stream = frozen_task_stream(seal, table_index, initial_continuation)
    stream_hash = canonical_hash(task_stream)
    basis = (initial_continuation,)
    generators = ()
    history = []
    acquired = []
    verifier_failures = 0
    restart_mismatches = 0
    ablation_checks = 0
    ablation_failures = 0
    dependent_reuse = []
    interface_dependent_reuse = []

    for step_index, task in enumerate(task_stream):
        # Each encounter begins from persisted state.
        payload = serialize_state(basis, generators)
        rb, rg = deserialize_state(payload)
        if rb != basis or rg != generators:
            restart_mismatches += 1
        basis, generators = rb, rg

        mutation = develop_one(table, basis, generators, task)
        if not verify_mutation(table, task, mutation):
            verifier_failures += 1

        if mutation.route in {"EXPAND_OPERATOR", "EXPAND_INTERFACE_OPERATOR"}:
            ablation_checks += 1
            if task_solved(mutation.generators_before, task):
                ablation_failures += 1
            if not task_solved(mutation.generators_after, task):
                ablation_failures += 1
            acquired.append(
                {
                    "step": step_index,
                    "route": mutation.route,
                    "operator": mutation.selected_operator,
                    "basis_before": mutation.basis_before,
                    "basis_after": mutation.basis_after,
                }
            )

        elif mutation.route == "REUSE" and acquired:
            full = generated_monoid(generators)
            if not any(task_satisfied(f, task) for f in full):
                verifier_failures += 1
            for idx, ancestor in enumerate(acquired):
                reduced_generators = tuple(
                    a["operator"] for j, a in enumerate(acquired) if j != idx
                )
                reduced = generated_monoid(reduced_generators)
                if not any(task_satisfied(f, task) for f in reduced):
                    witness = {
                        "future_step": step_index,
                        "future_task": [list(x) for x in task],
                        "ancestor_step": ancestor["step"],
                        "ancestor_route": ancestor["route"],
                        "ancestor_operator": list(ancestor["operator"]),
                    }
                    dependent_reuse.append(witness)
                    if ancestor["route"] == "EXPAND_INTERFACE_OPERATOR":
                        if quotient_congruent(
                            table, ancestor["basis_before"], ancestor["operator"]
                        ):
                            ablation_failures += 1
                        interface_dependent_reuse.append(witness)
                    break

        history.append(mutation_dict(step_index, task, mutation))
        basis, generators = mutation.basis_after, mutation.generators_after

        # Persist immediately; no future task receives live-only state.
        payload = serialize_state(basis, generators)
        rb, rg = deserialize_state(payload)
        if rb != basis or rg != generators:
            restart_mismatches += 1
        basis, generators = rb, rg

    routes = Counter(row["route"] for row in history)
    route_neutrality_mismatch = int(
        stream_hash != canonical_hash(
            frozen_task_stream(seal, table_index, initial_continuation)
        )
    )

    qualifying = bool(
        routes["EXPAND_OPERATOR"] >= 1
        and routes["EXPAND_INTERFACE_OPERATOR"] >= 1
        and routes["REUSE"] >= 1
        and routes["UNKNOWN"] == 0
        and routes["EXPAND_OPERATOR"] + routes["EXPAND_INTERFACE_OPERATOR"] >= 2
        and dependent_reuse
        and interface_dependent_reuse
        and verifier_failures == 0
        and restart_mismatches == 0
        and ablation_failures == 0
        and route_neutrality_mismatch == 0
    )

    return {
        "table_index": table_index,
        "initial_continuation": initial_continuation,
        "table": [list(row) for row in table],
        "task_stream_hash": stream_hash,
        "route_counts": dict(routes),
        "final_basis": list(basis),
        "final_generators": [list(x) for x in generators],
        "final_monoid_size": len(generated_monoid(generators)),
        "verifier_failures": verifier_failures,
        "restart_mismatches": restart_mismatches,
        "ablation_checks": ablation_checks,
        "ablation_failures": ablation_failures,
        "route_neutrality_mismatch": route_neutrality_mismatch,
        "dependent_reuse_count": len(dependent_reuse),
        "interface_dependent_reuse_count": len(interface_dependent_reuse),
        "dependent_reuse_witnesses": dependent_reuse[:10],
        "interface_dependent_reuse_witnesses":
            interface_dependent_reuse[:10],
        "qualifying": qualifying,
        "history": history if qualifying else None,
    }


def main():
    seal = (
        os.environ.get("VDN_V54_SEAL")
        or os.environ.get("GITHUB_SHA")
        or "LOCAL_UNSEALED"
    )

    total_streams = 0
    total_encounters = 0
    routes = Counter()
    verifier_failures = 0
    restart_mismatches = 0
    route_neutrality_mismatches = 0
    ablation_checks = 0
    ablation_failures = 0
    multi = 0
    direct = 0
    interface = 0
    dependent = 0
    interface_dependent = 0
    all_solved = 0
    qualifying = 0
    first_witness = None
    stream_rows = []

    tables = list(all_tables())
    for table_index, table in enumerate(tables):
        for c0 in C:
            result = run_stream(table, table_index, c0, seal)
            total_streams += 1
            total_encounters += len(TASK_UNIVERSE)
            rc = Counter(result["route_counts"])
            routes.update(rc)
            verifier_failures += result["verifier_failures"]
            restart_mismatches += result["restart_mismatches"]
            route_neutrality_mismatches += result["route_neutrality_mismatch"]
            ablation_checks += result["ablation_checks"]
            ablation_failures += result["ablation_failures"]

            acquisitions = rc["EXPAND_OPERATOR"] + rc["EXPAND_INTERFACE_OPERATOR"]
            multi += int(acquisitions >= 2)
            direct += int(rc["EXPAND_OPERATOR"] > 0)
            interface += int(rc["EXPAND_INTERFACE_OPERATOR"] > 0)
            dependent += int(result["dependent_reuse_count"] > 0)
            interface_dependent += int(
                result["interface_dependent_reuse_count"] > 0
            )
            all_solved += int(rc["UNKNOWN"] == 0)
            if result["qualifying"]:
                qualifying += 1
                if first_witness is None:
                    first_witness = result

            stream_rows.append(
                {
                    "table_index": table_index,
                    "initial_continuation": c0,
                    "task_stream_hash": result["task_stream_hash"],
                    "route_counts": result["route_counts"],
                    "final_monoid_size": result["final_monoid_size"],
                    "final_basis_size": len(result["final_basis"]),
                    "dependent_reuse_count": result["dependent_reuse_count"],
                    "interface_dependent_reuse_count":
                        result["interface_dependent_reuse_count"],
                    "qualifying": result["qualifying"],
                }
            )

    expected_streams = 2 ** (len(X) * len(C)) * len(C)
    expected_encounters = expected_streams * len(TASK_UNIVERSE)
    gates = {
        "declared_universe_exhausted":
            total_streams == expected_streams
            and total_encounters == expected_encounters,
        "zero_verifier_mismatches": verifier_failures == 0,
        "zero_restart_mismatches": restart_mismatches == 0,
        "route_neutral_task_streams": route_neutrality_mismatches == 0,
        "repeated_capability_acquisition_exists": multi > 0,
        "direct_operator_genesis_exists": direct > 0,
        "interface_forced_operator_genesis_exists": interface > 0,
        "future_reuse_depends_on_acquired_ancestor": dependent > 0,
        "future_reuse_depends_on_interface_acquired_ancestor":
            interface_dependent > 0,
        "exact_ancestor_ablations_clean":
            ablation_checks > 0 and ablation_failures == 0,
        "fully_continuous_qualifying_stream_exists": qualifying > 0,
    }

    summary = {
        "schema":
            "verified-developmental-navigation."
            "commit-sealed-continuous-genesis.v54",
        "classification":
            "FINITE_EXHAUSTIVE_COMMIT_SEALED_CAUSAL_CALIBRATION",
        "seal": seal,
        "parent_calibration": "V53 finite developmental ratchet",
        "declared_world": {
            "states": len(X),
            "continuations": len(C),
            "binary_tables": len(tables),
            "initial_contexts_per_table": len(C),
            "streams": total_streams,
            "task_universe_size": len(TASK_UNIVERSE),
            "encounters": total_encounters,
            "candidate_operator_universe": len(ALL_FUNCTIONS),
            "task_universe_hash": canonical_hash(TASK_UNIVERSE),
        },
        "route_counts": dict(routes),
        "streams_with_multi_acquisition": multi,
        "streams_with_direct_operator_genesis": direct,
        "streams_with_interface_genesis": interface,
        "streams_with_dependent_reuse": dependent,
        "streams_with_interface_dependent_reuse": interface_dependent,
        "all_tasks_solved_streams": all_solved,
        "qualifying_streams": qualifying,
        "verifier_failures": verifier_failures,
        "restart_mismatches": restart_mismatches,
        "route_neutrality_mismatches": route_neutrality_mismatches,
        "ancestor_ablation_checks": ablation_checks,
        "ancestor_ablation_failures": ablation_failures,
        "gates": gates,
        "all_gates_pass": all(gates.values()),
        "verdict":
            "PASS_COMMIT_SEALED_CONTINUOUS_CAPABILITY_GENESIS_V54"
            if all(gates.values())
            else "NO_COMMIT_SEALED_CONTINUOUS_CAPABILITY_GENESIS_V54",
        "claim_boundary": (
            "A PASS shows, exhaustively in the declared 3-state/"
            "3-continuation finite universe, that one restartable route-neutral "
            "developer can repeatedly acquire verified capability, including "
            "a capability unavailable under the ancestor quotient, retain it, "
            "and later reuse it on future commit-sealed tasks; exact ancestor "
            "ablation destroys at least one such later reuse. This is a bounded "
            "causal calibration, not unrestricted grammar invention, "
            "natural-domain transfer, or open-ended autonomous development."
        ),
        "first_witness": first_witness,
        "stream_summaries": stream_rows,
    }

    out_dir = Path(
        "verified-developmental-navigation/case_studies/finite_inevitability/"
        "results_v54_commit_sealed_continuous_genesis"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "result.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )

    print(json.dumps(
        {k: v for k, v in summary.items()
         if k not in {"first_witness", "stream_summaries"}},
        indent=2,
        sort_keys=True,
    ))
    if first_witness is not None:
        print("FIRST_WITNESS=" + json.dumps({
            "table_index": first_witness["table_index"],
            "initial_continuation": first_witness["initial_continuation"],
            "route_counts": first_witness["route_counts"],
            "final_monoid_size": first_witness["final_monoid_size"],
            "dependent_reuse_count":
                first_witness["dependent_reuse_count"],
            "interface_dependent_reuse_count":
                first_witness["interface_dependent_reuse_count"],
        }, sort_keys=True))

    if not summary["all_gates_pass"]:
        raise SystemExit("V54 frozen scientific verdict failed")


if __name__ == "__main__":
    main()
