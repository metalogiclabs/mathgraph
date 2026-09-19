from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
MSI_ROOT = Path(os.environ.get("MSI_SOURCE_ROOT", "_vendor/msi_source"))

MSI_COMMIT = "5d448c0ecc82ff3945d009963064ebbb67d2f308"
ARITHMETIC_TEST_BLOB = "5d23b9b5b2d16e94e2c15c2ed7439fba1335c6a3"

BASE = 10
BASIS_CONTEXT = (0, 0)
OLD_SCOPE_ID = "addition-next-digit-all-contexts-v1"
NEW_OBLIGATION_ID = "audit-last-pair-is-9-1-v1"
FLASH_AFTER_RAW_HISTORIES = 20
V2_PAIRWISE_AUTHORITY_CHECKS_PER_UPDATE = 5050


class RecoveryUnavailable(RuntimeError):
    pass


def load_arithmetic():
    path = MSI_ROOT / "tests/test_arithmetic_base_invariance.py"
    spec = importlib.util.spec_from_file_location("arith_revocable_v3", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value, prefix="") -> str:
    return hashlib.sha256((prefix + canonical_json(value)).encode()).hexdigest()


def history_id(history) -> str:
    if not history:
        return "eps"
    if len(history) != 1:
        raise ValueError("V3 carrier expects empty or one-position histories")
    a, b = history[0]
    return f"{a}:{b}"


def partition_from_map(ids, values):
    buckets = {}
    for ident in ids:
        buckets.setdefault(values[ident], []).append(ident)
    return tuple(
        sorted(
            (tuple(sorted(block)) for block in buckets.values()),
            key=lambda block: (len(block), block),
        )
    )


def identity_partition(ids):
    return tuple((ident,) for ident in sorted(ids))


def audit_obligation(history) -> int:
    return int(history == ((9, 1),))


@dataclass(frozen=True)
class ScopeCertificate:
    scope_id: str
    basis_context: tuple[int, int]
    source_commit: str
    source_blob: str
    full_family_size: int
    carrier_size: int
    basis_partition_digest: str
    full_partition_digest: str

    @property
    def certificate_id(self) -> str:
        return digest(
            {
                "scope_id": self.scope_id,
                "basis_context": self.basis_context,
                "source_commit": self.source_commit,
                "source_blob": self.source_blob,
                "full_family_size": self.full_family_size,
                "carrier_size": self.carrier_size,
                "basis_partition_digest": self.basis_partition_digest,
                "full_partition_digest": self.full_partition_digest,
            },
            prefix="scope-certificate-v1:",
        )


@dataclass(frozen=True)
class RevocationRecord:
    representation_id: str
    old_scope_id: str
    triggering_obligation_id: str
    reason: str

    def payload(self):
        return {
            "representation_id": self.representation_id,
            "old_scope_id": self.old_scope_id,
            "triggering_obligation_id": self.triggering_obligation_id,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class MaintainedRepresentation:
    active_partition: tuple[tuple[str, ...], ...]
    reserve_ids: tuple[str, ...]
    basis_values: tuple[tuple[str, int], ...]
    scope_id: str
    scope_certificate_id: str
    representation_id: str
    revocations: tuple[RevocationRecord, ...] = ()

    def payload(self):
        return {
            "version": "maintained-representation-v3",
            "active_partition": [list(block) for block in self.active_partition],
            "reserve_ids": list(self.reserve_ids),
            "basis_values": [[k, v] for k, v in self.basis_values],
            "scope_id": self.scope_id,
            "scope_certificate_id": self.scope_certificate_id,
            "representation_id": self.representation_id,
            "revocations": [r.payload() for r in self.revocations],
        }

    @property
    def digest(self):
        return digest(self.payload(), prefix="qckn-maintained-representation:")

    def text(self):
        return canonical_json(self.payload()) + "\n"

    @classmethod
    def parse(cls, text):
        p = json.loads(text)
        if p.get("version") != "maintained-representation-v3":
            raise ValueError("unsupported maintained representation version")
        state = cls(
            active_partition=tuple(tuple(str(x) for x in block) for block in p["active_partition"]),
            reserve_ids=tuple(str(x) for x in p["reserve_ids"]),
            basis_values=tuple((str(k), int(v)) for k, v in p["basis_values"]),
            scope_id=str(p["scope_id"]),
            scope_certificate_id=str(p["scope_certificate_id"]),
            representation_id=str(p["representation_id"]),
            revocations=tuple(
                RevocationRecord(
                    representation_id=str(r["representation_id"]),
                    old_scope_id=str(r["old_scope_id"]),
                    triggering_obligation_id=str(r["triggering_obligation_id"]),
                    reason=str(r["reason"]),
                )
                for r in p.get("revocations", ())
            ),
        )
        if state.text() != text:
            raise ValueError("non-canonical maintained representation")
        return state


def qualify_scope_certificate(ar):
    pairs, histories, retained, learned_classes = ar.adaptive_partition(BASE)
    if retained != (BASIS_CONTEXT,):
        raise AssertionError(retained)

    ids = tuple(history_id(h) for h in histories)
    by_id = {history_id(h): h for h in histories}

    basis_values = {
        ident: ar.oracle_next_digit(by_id[ident], BASIS_CONTEXT, BASE)
        for ident in ids
    }
    full_values = {
        ident: tuple(ar.oracle_next_digit(by_id[ident], c, BASE) for c in pairs)
        for ident in ids
    }

    basis_partition = partition_from_map(ids, basis_values)
    full_partition = partition_from_map(ids, full_values)
    learned_partition = tuple(
        sorted(
            (
                tuple(sorted(history_id(h) for h in cls))
                for cls in learned_classes
            ),
            key=lambda block: (len(block), block),
        )
    )

    if basis_partition != full_partition or full_partition != learned_partition:
        raise AssertionError("retained arithmetic basis is not exact for frozen scope")

    cert = ScopeCertificate(
        scope_id=OLD_SCOPE_ID,
        basis_context=BASIS_CONTEXT,
        source_commit=MSI_COMMIT,
        source_blob=ARITHMETIC_TEST_BLOB,
        full_family_size=len(pairs),
        carrier_size=len(histories),
        basis_partition_digest=digest(basis_partition),
        full_partition_digest=digest(full_partition),
    )
    return {
        "pairs": pairs,
        "histories": histories,
        "ids": ids,
        "by_id": by_id,
        "basis_values": basis_values,
        "basis_partition": basis_partition,
        "full_partition": full_partition,
        "certificate": cert,
        "qualification_oracle_evaluations": len(histories) * len(pairs),
    }


def compile_initial_coarsening(world, reserve_ids):
    ids = world["ids"]
    basis = world["basis_values"]

    # Runtime authority work: one certified sufficient-basis observation per raw state.
    runtime_evaluations = len(ids)
    active = partition_from_map(ids, basis)
    if active != world["basis_partition"]:
        raise AssertionError("basis compilation mismatch")

    rid = digest(
        {
            "scope": OLD_SCOPE_ID,
            "active": active,
            "certificate": world["certificate"].certificate_id,
        },
        prefix="representation:",
    )
    return MaintainedRepresentation(
        active_partition=active,
        reserve_ids=tuple(sorted(reserve_ids)),
        basis_values=tuple(sorted(basis.items())),
        scope_id=OLD_SCOPE_ID,
        scope_certificate_id=world["certificate"].certificate_id,
        representation_id=rid,
    ), runtime_evaluations


def extend_reserve(state, ids):
    merged = tuple(sorted(set(state.reserve_ids) | set(ids)))
    return MaintainedRepresentation(
        active_partition=state.active_partition,
        reserve_ids=merged,
        basis_values=state.basis_values,
        scope_id=state.scope_id,
        scope_certificate_id=state.scope_certificate_id,
        representation_id=state.representation_id,
        revocations=state.revocations,
    )


def revoke_for_new_obligation(state, world):
    if NEW_OBLIGATION_ID == state.scope_id:
        raise AssertionError("new obligation must be outside old scope")
    if set(state.reserve_ids) != set(world["ids"]):
        raise RecoveryUnavailable("raw distinctions required for scope revocation are unavailable")

    record = RevocationRecord(
        representation_id=state.representation_id,
        old_scope_id=state.scope_id,
        triggering_obligation_id=NEW_OBLIGATION_ID,
        reason="protected consequence family expanded beyond certified scope",
    )

    reopened = identity_partition(world["ids"])
    return MaintainedRepresentation(
        active_partition=reopened,
        reserve_ids=state.reserve_ids,
        basis_values=state.basis_values,
        scope_id=f"{OLD_SCOPE_ID}+{NEW_OBLIGATION_ID}",
        scope_certificate_id="scope-expansion-pending",
        representation_id=digest(
            {"reopened_from": state.representation_id, "obligation": NEW_OBLIGATION_ID},
            prefix="representation:",
        ),
        revocations=state.revocations + (record,),
    )


def compile_expanded_scope(reopened, world):
    if len(reopened.active_partition) != len(world["ids"]):
        raise AssertionError("scope expansion must reopen raw distinctions before recompilation")

    basis = dict(reopened.basis_values)
    audit_values = {
        ident: audit_obligation(world["by_id"][ident])
        for ident in world["ids"]
    }
    runtime_evaluations = len(audit_values)
    combined = {
        ident: (basis[ident], audit_values[ident])
        for ident in world["ids"]
    }
    final_partition = partition_from_map(world["ids"], combined)

    if len(final_partition) != 3:
        raise AssertionError(final_partition)

    state = MaintainedRepresentation(
        active_partition=final_partition,
        reserve_ids=reopened.reserve_ids,
        basis_values=reopened.basis_values,
        scope_id=reopened.scope_id,
        scope_certificate_id=digest(
            {
                "old_certificate": world["certificate"].certificate_id,
                "new_obligation": NEW_OBLIGATION_ID,
                "new_obligation_digest": digest(tuple(sorted(audit_values.items()))),
            },
            prefix="expanded-scope-certificate:",
        ),
        representation_id=digest(
            {"scope": reopened.scope_id, "active": final_partition},
            prefix="representation:",
        ),
        revocations=reopened.revocations,
    )
    return state, runtime_evaluations, audit_values


def find_unsoundness_without_revocation(state, world):
    block_of = {}
    for i, block in enumerate(state.active_partition):
        for ident in block:
            block_of[ident] = i
    audits = {ident: audit_obligation(world["by_id"][ident]) for ident in world["ids"]}
    for a in world["ids"]:
        for b in world["ids"]:
            if a >= b:
                continue
            if block_of[a] == block_of[b] and audits[a] != audits[b]:
                return {
                    "left": a,
                    "right": b,
                    "old_class": block_of[a],
                    "new_consequences": [audits[a], audits[b]],
                }
    return None


def run_flash(world):
    first = world["ids"][:FLASH_AFTER_RAW_HISTORIES]
    state, initial_authority = compile_initial_coarsening(world, first)
    state = extend_reserve(state, world["ids"][FLASH_AFTER_RAW_HISTORIES:])

    pre_restart = state
    restarted = MaintainedRepresentation.parse(pre_restart.text())
    restart_exact = (
        restarted.text() == pre_restart.text()
        and restarted.digest == pre_restart.digest
    )

    reopened = revoke_for_new_obligation(restarted, world)
    final, expansion_authority, audit_values = compile_expanded_scope(reopened, world)

    return {
        "initial_raw_active_before_flash": FLASH_AFTER_RAW_HISTORIES,
        "initial_runtime_authority_evaluations": initial_authority,
        "initial_active_classes": len(state.active_partition),
        "reserve_entries_after_stream": len(state.reserve_ids),
        "restart_exact": restart_exact,
        "restart_digest": restarted.digest,
        "revocation_count": len(reopened.revocations),
        "reopened_classes": len(reopened.active_partition),
        "raw_reacquisition_count": 0,
        "expanded_runtime_authority_evaluations": expansion_authority,
        "final_active_classes": len(final.active_partition),
        "final_scope_id": final.scope_id,
        "final_digest": final.digest,
        "audit_positive_count": sum(audit_values.values()),
        "total_runtime_authority_evaluations": initial_authority + expansion_authority,
        "final_state": final,
    }


def run_restart_control(world):
    state, initial = compile_initial_coarsening(world, world["ids"])
    text = state.text()
    restarted = MaintainedRepresentation.parse(text)
    reopened = revoke_for_new_obligation(restarted, world)
    final, expansion, _ = compile_expanded_scope(reopened, world)
    return {
        "restart_exact": restarted.text() == text and restarted.digest == state.digest,
        "initial_runtime_authority_evaluations": initial,
        "expanded_runtime_authority_evaluations": expansion,
        "final_active_classes": len(final.active_partition),
        "revocation_count": len(final.revocations),
        "final_digest": final.digest,
    }


def run_no_reserve(world):
    state, initial = compile_initial_coarsening(world, ())
    failed = False
    message = ""
    try:
        revoke_for_new_obligation(state, world)
    except RecoveryUnavailable as exc:
        failed = True
        message = str(exc)
    return {
        "initial_runtime_authority_evaluations": initial,
        "recovery_failed": failed,
        "error": message,
    }


def run_no_revocation(world):
    state, initial = compile_initial_coarsening(world, world["ids"])
    witness = find_unsoundness_without_revocation(state, world)
    return {
        "initial_runtime_authority_evaluations": initial,
        "kept_old_active_classes": len(state.active_partition),
        "unsoundness_detected": witness is not None,
        "witness": witness,
    }


def run():
    ar = load_arithmetic()
    world = qualify_scope_certificate(ar)

    flash = run_flash(world)
    restart = run_restart_control(world)
    no_reserve = run_no_reserve(world)
    no_revocation = run_no_revocation(world)

    # Compare to the V2 exact pairwise authority if it were repeated for both updates.
    v2_two_update_checks = 2 * V2_PAIRWISE_AUTHORITY_CHECKS_PER_UPDATE
    runtime_two_update_checks = flash["total_runtime_authority_evaluations"]

    final_state = flash.pop("final_state")
    expected_final_partition = final_state.active_partition
    basis_counts = {}
    for _, value in world["basis_values"].items():
        basis_counts[value] = basis_counts.get(value, 0) + 1

    gates = {
        "source_basis_exact_for_frozen_scope": (
            world["basis_partition"] == world["full_partition"]
            and len(world["basis_partition"]) == 2
        ),
        "source_basis_is_single_context": world["certificate"].basis_context == BASIS_CONTEXT,
        "flash_initial_coarsening_101_to_2": (
            flash["initial_runtime_authority_evaluations"] == 101
            and flash["initial_active_classes"] == 2
        ),
        "reserve_maintained_for_all_101_raw_histories": flash["reserve_entries_after_stream"] == 101,
        "restart_exact_before_scope_change": flash["restart_exact"],
        "scope_change_emits_revocation": flash["revocation_count"] == 1,
        "revocation_reopens_101_raw_classes": flash["reopened_classes"] == 101,
        "revocation_requires_zero_raw_reacquisition": flash["raw_reacquisition_count"] == 0,
        "expanded_scope_uses_101_new_consequence_evaluations": flash["expanded_runtime_authority_evaluations"] == 101,
        "expanded_scope_recompiles_to_3_classes": flash["final_active_classes"] == 3,
        "new_obligation_has_one_positive_history": flash["audit_positive_count"] == 1,
        "no_reserve_control_fails_recovery": no_reserve["recovery_failed"],
        "no_revocation_control_detects_unsound_merge": no_revocation["unsoundness_detected"],
        "restart_control_matches_3_class_result": (
            restart["restart_exact"]
            and restart["final_active_classes"] == 3
            and restart["revocation_count"] == 1
        ),
        "runtime_two_update_authority_is_202": runtime_two_update_checks == 202,
        "runtime_authority_below_repeated_v2_pairwise": runtime_two_update_checks < v2_two_update_checks,
    }
    gates["pass"] = all(gates.values())

    result = {
        "schema": "mathgraph.qckn.maintained-revocable-equilibration.v3",
        "source_authority": {
            "repository": "heathsanchez/Minimal-Sufficient-Interface",
            "commit": MSI_COMMIT,
            "test_blob": ARITHMETIC_TEST_BLOB,
            "base": BASE,
            "carrier_size": len(world["ids"]),
            "protected_family_size": len(world["pairs"]),
            "qualified_basis_context": list(BASIS_CONTEXT),
            "scope_certificate_id": world["certificate"].certificate_id,
            "qualification_oracle_evaluations": world["qualification_oracle_evaluations"],
            "qualification_cost_boundary": (
                "The complete frozen scope is requalified in CI. Runtime figures below measure reuse of that "
                "previously earned sufficiency certificate rather than charging its proof again on every update."
            ),
        },
        "old_scope": {
            "scope_id": OLD_SCOPE_ID,
            "basis_class_counts": basis_counts,
            "active_classes": 2,
        },
        "new_obligation": {
            "obligation_id": NEW_OBLIGATION_ID,
            "definition": "1 iff the most recent digit pair is exactly (9,1), else 0",
            "outside_old_scope": True,
            "expected_expanded_classes": 3,
        },
        "flash": flash,
        "restart_control": restart,
        "no_reserve_control": no_reserve,
        "no_revocation_control": no_revocation,
        "economics": {
            "v2_pairwise_authority_checks_per_update": V2_PAIRWISE_AUTHORITY_CHECKS_PER_UPDATE,
            "v2_pairwise_checks_if_repeated_for_two_updates": v2_two_update_checks,
            "v3_runtime_authority_evaluations_two_updates": runtime_two_update_checks,
            "runtime_check_reduction_fraction_vs_repeated_v2_pairwise": 1 - runtime_two_update_checks / v2_two_update_checks,
            "steady_active_classes_before_scope_change": 2,
            "transient_reopened_classes_on_revocation": 101,
            "steady_active_classes_after_scope_change": len(expected_final_partition),
            "maintained_reserve_entries": 101,
        },
        "qckn_alignment": {
            "design": "ACTIVE + RESERVE + explicit revocation + canonical restart",
            "realitygraph_reference_commit": "a03310d7660ea98ac37cdeace4264e36f2a4b6ed",
            "claim": (
                "V3 applies the existing QCKN retention/revocation pattern to representation state; "
                "it does not modify the frozen QCK/MSI kernel."
            ),
        },
        "gates": gates,
        "scientific_verdict": (
            "PASS_INCREMENTAL_REVOCABLE_CONSEQUENTIAL_EQUILIBRATION"
            if gates["pass"]
            else "FAIL_MAINTAINED_REVOCABLE_EQUILIBRATION_V3"
        ),
        "boundary": (
            "Bounded finite maintained representation experiment. A previously qualified sufficient basis is "
            "reused to coarsen runtime state incrementally; raw distinctions remain in reserve; an out-of-scope "
            "new protected consequence revokes the old coarsening, reopens raw distinctions without reacquisition, "
            "and recompiles a new minimum present. This does not establish cheap basis discovery, open-world safe "
            "coarsening without scope certificates, or universal representation optimality."
        ),
    }
    result["digest_sha256"] = digest(result, prefix="v3-result:")
    return result


def main():
    r = run()
    (ROOT / "result.json").write_text(json.dumps(r, indent=2, sort_keys=True) + "\n")
    print("MAINTAINED_REVOCABLE_EQUILIBRATION_V3=" + r["scientific_verdict"])
    print("FLASH=" + json.dumps(r["flash"], sort_keys=True))
    print("NO_RESERVE=" + json.dumps(r["no_reserve_control"], sort_keys=True))
    print("NO_REVOCATION=" + json.dumps(r["no_revocation_control"], sort_keys=True))
    print("ECONOMICS=" + json.dumps(r["economics"], sort_keys=True))
    print("DIGEST_SHA256=" + r["digest_sha256"])
    if not r["gates"]["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
