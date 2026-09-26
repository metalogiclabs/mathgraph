import json
import os
from pathlib import Path
import stat
import subprocess
import sys

from mathgraph.atp_tptp import (
    FirstOrderResidual,
    classify_szs,
    parse_szs_output_blocks,
    parse_szs_status,
    run_vampire,
)
from mathgraph.protected_future import (
    ContinuationStatus,
    ProtectedContinuation,
    ProtectedContinuationMachine,
)
from mathgraph.query_gateway import (
    CrystalQuestion,
    machine_from_dict,
    machine_to_dict,
    query_crystal,
)


ROOT = Path(__file__).resolve().parents[1]


def _machine():
    return ProtectedContinuationMachine(
        "brain-demo",
        ("q",),
        (
            ProtectedContinuation(
                "q", "claim:P", ("holds",), ContinuationStatus.WARRANTED,
                evidence_refs=("lean:proof:P",),
            ),
            ProtectedContinuation(
                "q", "claim:R", ("holds",), ContinuationStatus.EXCLUDED,
                evidence_refs=("finite-countermodel:R",),
            ),
            ProtectedContinuation(
                "q", "claim:U", ("holds",), ContinuationStatus.UNKNOWN,
            ),
            ProtectedContinuation(
                "q", "claim:supported", ("holds",), ContinuationStatus.WARRANTED,
                support_refs=("warrant:1",), evidence_refs=("proof:supported",),
            ),
            ProtectedContinuation(
                "q", "claim:conflict", ("holds",), ContinuationStatus.WARRANTED,
                evidence_refs=("proof:conflict",),
            ),
            ProtectedContinuation(
                "q", "claim:conflict", ("holds",), ContinuationStatus.EXCLUDED,
                evidence_refs=("countermodel:conflict",),
            ),
        ),
    )


def test_query_gateway_returns_warranted_with_provenance():
    answer = query_crystal(_machine(), CrystalQuestion("q", "claim:P", ("holds",)))
    assert answer.status is ContinuationStatus.WARRANTED
    assert answer.outcomes == (("holds",),)
    assert answer.provenance == ("lean:proof:P",)
    assert answer.residual is None


def test_query_gateway_returns_excluded_with_counterexample_provenance():
    answer = query_crystal(_machine(), CrystalQuestion("q", "claim:R", ("holds",)))
    assert answer.status is ContinuationStatus.EXCLUDED
    assert answer.provenance == ("finite-countermodel:R",)
    assert answer.residual is None


def test_query_gateway_explicit_unknown_emits_small_residual_and_atp_route():
    answer = query_crystal(
        _machine(),
        CrystalQuestion(
            "q", "claim:U", ("holds",),
            interface_id="logic.first-order.entailment@1",
        ),
    )
    assert answer.status is ContinuationStatus.UNKNOWN
    assert answer.residual is not None
    assert answer.residual.reason == "unresolved_continuation"
    assert answer.residual.route_hint == "atp:tptp"
    payload = answer.residual.to_dict()
    assert set(payload) == {
        "residual_id", "boundary_ref", "source", "continuation",
        "requested_outcome", "interface_id", "reason", "missing_supports",
        "evidence_refs", "route_hint",
    }


def test_query_gateway_missing_fact_stays_unknown_not_false():
    answer = query_crystal(_machine(), CrystalQuestion("q", "claim:missing", ("holds",)))
    assert answer.status is ContinuationStatus.UNKNOWN
    assert answer.residual.reason == "missing_continuation"


def test_query_gateway_revoked_support_becomes_unknown_then_live_when_restored():
    blocked = query_crystal(_machine(), CrystalQuestion("q", "claim:supported", ("holds",)))
    assert blocked.status is ContinuationStatus.UNKNOWN
    assert blocked.residual.reason == "missing_live_support"
    assert blocked.residual.missing_supports == ("warrant:1",)

    live = query_crystal(
        _machine(),
        CrystalQuestion("q", "claim:supported", ("holds",), live_supports=("warrant:1",)),
    )
    assert live.status is ContinuationStatus.WARRANTED
    assert live.provenance == ("proof:supported",)


def test_query_gateway_conflicting_authority_is_residual_not_precedence():
    answer = query_crystal(_machine(), CrystalQuestion("q", "claim:conflict", ("holds",)))
    assert answer.status is ContinuationStatus.UNKNOWN
    assert answer.residual.reason == "conflicting_authority"
    assert set(answer.provenance) == {"proof:conflict", "countermodel:conflict"}


def test_machine_json_roundtrip_preserves_query_answers():
    before = _machine()
    after = machine_from_dict(machine_to_dict(before))
    assert after == before
    q = CrystalQuestion("q", "claim:P", ("holds",))
    assert query_crystal(before, q).to_dict() == query_crystal(after, q).to_dict()


def test_tptp_fof_export_is_content_addressed_and_inspectable():
    residual = FirstOrderResidual(
        "modus-ponens",
        (("a1", "p(a)"), ("a2", "p(a) => q(a)")),
        "q(a)",
        source_refs=("source:test",),
    )
    text = residual.to_tptp()
    assert "fof(a1, axiom, (p(a)))." in text
    assert "fof(a2, axiom, (p(a) => q(a)))." in text
    assert "fof(conjecture, conjecture, (q(a)))." in text
    assert residual.tptp_sha256 in residual.to_dict()["tptp_sha256"]


def test_szs_status_and_output_blocks_map_conservatively():
    theorem = """% SZS status Theorem for demo
% SZS output start CNFRefutation for demo
fof(x,plain,$false).
% SZS output end CNFRefutation for demo
"""
    counter = "% SZS status CounterSatisfiable for demo\n"
    bad = "% SZS status ContradictoryAxioms for demo\n"
    assert parse_szs_status(theorem) == "Theorem"
    assert classify_szs("Theorem") == "CANDIDATE_WARRANTED"
    assert classify_szs(parse_szs_status(counter)) == "CANDIDATE_EXCLUDED"
    assert classify_szs(parse_szs_status(bad)) == "INVALID_PREMISE_SET"
    blocks = parse_szs_output_blocks(theorem)
    assert len(blocks) == 1
    assert blocks[0].kind == "CNFRefutation"
    assert "$false" in blocks[0].content


def _fake_vampire(path: Path, status: str = "Theorem") -> Path:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "print('% SZS status " + status + " for fake')\n"
        "print('% SZS output start CNFRefutation for fake')\n"
        "print('fof(step,plain,$false).')\n"
        "print('% SZS output end CNFRefutation for fake')\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_vampire_runner_returns_candidate_evidence_not_authority(tmp_path):
    residual = FirstOrderResidual("demo", (("a1", "p(a)"),), "p(a)")
    fake = _fake_vampire(tmp_path / "vampire")
    evidence = run_vampire(residual, executable=str(fake), time_limit_seconds=2)
    assert evidence.szs_status == "Theorem"
    assert evidence.candidate_status == "CANDIDATE_WARRANTED"
    assert evidence.requires_independent_check
    proposal = evidence.as_unadmitted_continuation("q")
    assert proposal.status is ContinuationStatus.UNKNOWN
    assert evidence.id in proposal.evidence_refs


def test_query_cli_taps_crystal_first_then_routes_unknown_to_atp(tmp_path):
    machine_path = tmp_path / "machine.json"
    machine_path.write_text(json.dumps(machine_to_dict(_machine())), encoding="utf-8")
    residual_path = tmp_path / "residual.json"
    residual_path.write_text(json.dumps({
        "problem_id": "demo",
        "axioms": [{"name": "a1", "formula": "p(a)"}],
        "conjecture": "p(a)",
        "boundary_ref": "logic:first-order",
    }), encoding="utf-8")
    fake = _fake_vampire(tmp_path / "vampire")

    proc = subprocess.run(
        [
            sys.executable, str(ROOT / "scripts" / "query_crystal.py"),
            "--machine", str(machine_path),
            "--source", "q",
            "--continuation", "claim:U",
            "--outcome", "holds",
            "--interface-id", "logic.first-order.entailment@1",
            "--atp-residual", str(residual_path),
            "--vampire", str(fake),
            "--atp-time-limit", "2",
        ],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["crystal"]["status"] == "UNKNOWN"
    assert payload["crystal"]["residual"]["route_hint"] == "atp:tptp"
    assert payload["atp_candidate"]["candidate_status"] == "CANDIDATE_WARRANTED"
    assert "candidate evidence only" in payload["authority_note"]
