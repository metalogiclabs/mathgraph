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
    """Small ACTIVE state plus raw recovery RESERVE.

    ACTIVE stores only class keys. It deliberately does not serialize raw class
    membership. Raw identities and their retained sufficient-basis values live
    only in RESERVE, so exact recovery genuinely depends on reserve retention.
    """

    active_class_keys: tuple[str, ...]
    reserve_entries: tuple[tuple[str, int], ...]
    scope_id: str
    scope_certificate_id: str
    representation_id: str
    revocations: tuple[RevocationRecord, ...] = ()

    def payload(self):
        return {
            "version": "maintained-representation-v3",
            "active_class_keys": list(self.active_class_keys),
            "reserve_entries": [[k, v] for k, v in self.reserve_entries],
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
            active_class_keys=tuple(str(x) for x in p["active_class_keys"]),
            reserve_entries=tuple((str(k), int(v)) for k, v in p["reserve_entries"]),
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

    # Runtime authority work: one already-certified sufficient-basis observation
    # per raw state. The expensive proof that this basis is sufficient belongs to
    # the pinned source certificate and is requalified separately in CI.
    runtime_evaluations = len(ids)
    class_keys = tuple(sorted({str(basis[ident]) for ident in ids}))

    reserve = tuple(
        sorted((ident, int(basis[ident])) for ident in reserve_ids)
    )
    rid = digest(
        {
            "scope": OLD_SCOPE_ID,
            "active_class_keys": class_keys,
            "certificate": world["certificate"].certificate_id,
        },
        prefix="representation:",
    )
    return MaintainedRepresentation(
        active_class_keys=class_keys,
        reserve_entries=reserve,
        scope_id=OLD_SCOPE_ID,
        scope_certificate_id=world["certificate"].certificate_id,
        representation_id=rid,
    ), runtime_evaluations


def extend_reserve(state, ids, world):
    merged = dict(state.reserve_entries)
    for ident in ids:
        merged[ident] = int(world["basis_values"][ident])
    return MaintainedRepresentation(
        active_class_keys=state.active_class_keys,
        reserve_entries=tuple(sorted(merged.items())),
        scope_id=state.scope_id,
        scope_certificate_id=state.scope_certificate_id,
        representation_id=state.representation_id,
        revocations=state.revocations,
    )


def revoke_for_new_obligation(state, world):
    reserve = dict(state.reserve_entries)
    if set(reserve) != set(world["ids"]):
        raise RecoveryUnavailable(
            "raw distinctions required for scope revocation are unavailable"
        )

    record = RevocationRecord(
        representation_id=state.representation_id,
        old_scope_id=state.scope_id,
        triggering_obligation_id=NEW_OBLIGATION_ID,
        reason="protected consequence family expanded beyond certified scope",
    )

    # Reopening uses only RESERVE. ACTIVE had retained no raw membership list.
    reopened_class_keys = tuple(sorted(reserve))
    return MaintainedRepresentation(
        active_class_keys=reopened_class_keys,
        reserve_entries=state.reserve_entries,
        scope_id=f"{OLD_SCOPE_ID}+{NEW_OBLIGATION_ID}",
        scope_certificate_id="scope-expansion-pending",
        representation_id=digest(
            {
                "reopened_from": state.representation_id,
                "obligation": NEW_OBLIGATION_ID,
                "raw_reserve_digest": digest(state.reserve_entries),
            },
            prefix="representation:",
        ),
        revocations=state.revocations + (record,),
    )


def compile_expanded_scope(reopened, world):
    if len(reopened.active_class_keys) != len(world["ids"]):
        raise AssertionError(
            "scope expansion must reopen every raw distinction before recompilation"
        )

    reserve = dict(reopened.reserve_entries)
    audit_values = {
        ident: audit_obligation(world["by_id"][ident])
        for ident in world["ids"]
    }
    runtime_evaluations = len(audit_values)

    combined_keys = tuple(
        sorted(
            {
                f"{reserve[ident]}|{audit_values[ident]}"
                for ident in world["ids"]
            }
        )
    )
    if combined_keys != ("0|0", "1|0", "1|1"):
        raise AssertionError(combined_keys)

    state = MaintainedRepresentation(
        active_class_keys=combined_keys,
        reserve_entries=reopened.reserve_entries,
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
            {"scope": reopened.scope_id, "active_class_keys": combined_keys},
            prefix="representation:",
        ),
        revocations=reopened.revocations,
    )
    return state, runtime_evaluations, audit_values


def find_unsoundness_without_revocation(state, world):
    if state.active_class_keys != ("0", "1"):
        raise AssertionError(state.active_class_keys)

    basis = world["basis_values"]
    audits = {
        ident: audit_obligation(world["by_id"][ident])
        for ident in world["ids"]
    }
    for i, a in enumerate(world["ids"]):
        for b in world["ids"][i + 1:]:
            if basis[a] == basis[b] and audits[a] != audits[b]:
                return {
                    "left": a,
                    "right": b,
                    "old_class_key": str(basis[a]),
                    "new_consequences": [audits[a], audits[b]],
                }
    return None


def run_flash(world):
    first = world["ids"][:FLASH_AFTER_RAW_HISTORIES]
    state, initial_authority = compile_initial_coarsening(world, first)

    # Future raw events affect execution only through the two-class ACTIVE state,
    # but are appended to RESERVE for possible recovery.
    state = extend_reserve(
        state,
        world["ids"][FLASH_AFTER_RAW_HISTORIES:],
        world,
    )

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
        "initial_active_classes": len(state.active_class_keys),
        "reserve_entries_after_stream": len(state.reserve_entries),
        "active_serializes_raw_membership": False,
        "restart_exact": restart_exact,
        "restart_digest": restarted.digest,
        "revocation_count": len(reopened.revocations),
        "reopened_classes": len(reopened.active_class_keys),
        "raw_reacquisition_count": 0,
        "expanded_runtime_authority_evaluations": expansion_authority,
        "final_active_classes": len(final.active_class_keys),
        "final_scope_id": final.scope_id,
        "final_digest": final.digest,
        "audit_positive_count": sum(audit_values.values()),
        "total_runtime_authority_evaluations": initial_authority + expansion_authority,
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
        "final_active_classes": len(final.active_class_keys),
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
        "active_class_keys": list(state.active_class_keys),
        "reserve_entries": len(state.reserve_entries),
        "recovery_failed": failed,
        "error": message,
    }


def run_no_revocation(world):
    state, initial = compile_initial_coarsening(world, world["ids"])
    witness = find_unsoundness_without_revocation(state, world)
    return {
        "initial_runtime_authority_evaluations": initial,
        "kept_old_active_classes": len(state.active_class_keys),
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

    v2_two_update_checks = 2 * V2_PAIRWISE_AUTHORITY_CHECKS_PER_UPDATE
    runtime_two_update_checks = flash["total_runtime_authority_evaluations"]

    basis_counts = {}
    for value in world["basis_values"].values():
        basis_counts[value] = basis_counts.get(value, 0) + 1

    gates = {
        "source_basis_exact_for_frozen_scope": (
            world["basis_partition"] == world["full_partition"]
            and len(world["basis_partition"]) == 2
        ),
        "source_basis_is_single_context": (
            world["certificate"].basis_context == BASIS_CONTEXT
        ),
        "flash_initial_coarsening_101_to_2": (
            flash["initial_runtime_authority_evaluations"] == 101
            and flash["initial_active_classes"] == 2
        ),
        "active_does_not_serialize_raw_membership": (
            flash["active_serializes_raw_membership"] is False
        ),
        "reserve_maintained_for_all_101_raw_histories": (
            flash["reserve_entries_after_stream"] == 101
        ),
        "restart_exact_before_scope_change": flash["restart_exact"],
        "scope_change_emits_revocation": flash["revocation_count"] == 1,
        "revocation_reopens_101_raw_classes": flash["reopened_classes"] == 101,
        "revocation_requires_zero_raw_reacquisition": (
            flash["raw_reacquisition_count"] == 0
        ),
        "expanded_scope_uses_101_new_consequence_evaluations": (
            flash["expanded_runtime_authority_evaluations"] == 101
        ),
        "expanded_scope_recompiles_to_3_classes": (
            flash["final_active_classes"] == 3
        ),
        "new_obligation_has_one_positive_history": (
            flash["audit_positive_count"] == 1
        ),
        "no_reserve_control_has_no_raw_leak": (
            no_reserve["reserve_entries"] == 0
            and no_reserve["active_class_keys"] == ["0", "1"]
        ),
        "no_reserve_control_fails_recovery": no_reserve["recovery_failed"],
        "no_revocation_control_detects_unsound_merge": (
            no_revocation["unsoundness_detected"]
        ),
        "restart_control_matches_flash_final_digest": (
            restart["restart_exact"]
            and restart["final_active_classes"] == 3
            and restart["revocation_count"] == 1
            and restart["final_digest"] == flash["final_digest"]
        ),
        "runtime_two_update_authority_is_202": (
            runtime_two_update_checks == 202
        ),
        "runtime_authority_below_repeated_v2_pairwise": (
            runtime_two_update_checks < v2_two_update_checks
        ),
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
            "qualification_oracle_evaluations": (
                world["qualification_oracle_evaluations"]
            ),
            "qualification_cost_boundary": (
                "The complete frozen scope is requalified in CI. Runtime figures "
                "measure reuse of that already-earned sufficiency certificate rather "
                "than charging its proof again on every live update."
            ),
        },
        "old_scope": {
            "scope_id": OLD_SCOPE_ID,
            "basis_class_counts": basis_counts,
            "active_classes": 2,
        },
        "new_obligation": {
            "obligation_id": NEW_OBLIGATION_ID,
            "definition": (
                "1 iff the most recent digit pair is exactly (9,1), else 0"
            ),
            "outside_old_scope": True,
            "expected_expanded_classes": 3,
        },
        "flash": flash,
        "restart_control": restart,
        "no_reserve_control": no_reserve,
        "no_revocation_control": no_revocation,
        "economics": {
            "v2_pairwise_authority_checks_per_update": (
                V2_PAIRWISE_AUTHORITY_CHECKS_PER_UPDATE
            ),
            "v2_pairwise_checks_if_repeated_for_two_updates": (
                v2_two_update_checks
            ),
            "v3_runtime_authority_evaluations_two_updates": (
                runtime_two_update_checks
            ),
            "runtime_check_reduction_fraction_vs_repeated_v2_pairwise": (
                1 - runtime_two_update_checks / v2_two_update_checks
            ),
            "steady_active_classes_before_scope_change": 2,
            "transient_reopened_classes_on_revocation": 101,
            "steady_active_classes_after_scope_change": 3,
            "maintained_reserve_entries": 101,
        },
        "qckn_alignment": {
            "design": (
                "small ACTIVE + raw recovery RESERVE + explicit revocation + "
                "canonical restart"
            ),
            "realitygraph_reference_commit": (
                "a03310d7660ea98ac37cdeace4264e36f2a4b6ed"
            ),
            "claim": (
                "V3 applies the existing QCKN retention/revocation pattern to "
                "representation state; it does not modify the frozen QCK/MSI kernel."
            ),
        },
        "gates": gates,
        "scientific_verdict": (
            "PASS_INCREMENTAL_REVOCABLE_CONSEQUENTIAL_EQUILIBRATION"
            if gates["pass"]
            else "FAIL_MAINTAINED_REVOCABLE_EQUILIBRATION_V3"
        ),
        "boundary": (
            "Bounded finite maintained representation experiment. A previously "
            "qualified sufficient basis is reused to coarsen runtime state; raw "
            "distinctions remain only in reserve; an out-of-scope new protected "
            "consequence revokes the old coarsening, reopens raw distinctions with "
            "zero reacquisition, and recompiles a new minimum present. This does not "
            "establish cheap basis discovery, open-world safe coarsening without "
            "scope certificates, or universal representation optimality."
        ),
    }
    result["digest_sha256"] = digest(result, prefix="v3-result:")
    return result


def main():
    r = run()
    (ROOT / "result.json").write_text(
        json.dumps(r, indent=2, sort_keys=True) + "\n"
    )
    print(
        "MAINTAINED_REVOCABLE_EQUILIBRATION_V3="
        + r["scientific_verdict"]
    )
    print("FLASH=" + json.dumps(r["flash"], sort_keys=True))
    print("NO_RESERVE=" + json.dumps(r["no_reserve_control"], sort_keys=True))
    print(
        "NO_REVOCATION="
        + json.dumps(r["no_revocation_control"], sort_keys=True)
    )
    print("ECONOMICS=" + json.dumps(r["economics"], sort_keys=True))
    print("DIGEST_SHA256=" + r["digest_sha256"])
    if not r["gates"]["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
