import json
from pathlib import Path

from mathgraph.certificates import TerminalForm
from mathgraph.faithfulness import (
    FaithfulnessAssessment,
    FaithfulnessStatus,
    SoundnessStatus,
)
from mathgraph.lawbook import (
    LawbookReviewDecision,
    lawbook_entry_from_certificate_like,
    lawbook_entry_from_proof_digestion,
    review_lawbook_candidate,
)
from mathgraph.proof_digestion import (
    DigestionStatus,
    ExpositionNote,
    ProofDigestionTrace,
    ReusableSchemaCandidate,
)


ROOT = Path(__file__).resolve().parents[1]


def _verified_claim_entry():
    return lawbook_entry_from_certificate_like(
        claim_id="open-conjecture",
        terminal_form=TerminalForm.VERIFIED_PROOF,
        certificate_id="lean-cert-001",
        verifier_boundary_crossed=True,
        provenance={"verifier": "lean"},
    )


def test_verified_claim_can_remain_human_undigested():
    """Truth authority and human understanding are independent axes."""
    claim = _verified_claim_entry()
    digest = ProofDigestionTrace(
        trace_id="digest-001",
        certificate_ids=("lean-cert-001",),
        status=DigestionStatus.UNDIGESTED,
        terminal_form=TerminalForm.VERIFIED_PROOF,
        certificate_id="lean-cert-001",
        verifier_boundary_crossed=True,
    )

    assert review_lawbook_candidate(claim).decision == LawbookReviewDecision.ACCEPT
    assert digest.is_truth_terminal()
    assert not digest.is_digested()


def test_human_exposition_does_not_create_or_increase_truth_authority():
    """A digest may become exposition-ready while remaining non-verifying."""
    digest = ProofDigestionTrace(
        trace_id="digest-002",
        status=DigestionStatus.EXPOSITION_READY,
        exposition_notes=[
            ExpositionNote(
                note_id="note-001",
                title="Human explanation",
                summary="A readable explanation of the machine-checked argument.",
            )
        ],
        verifier_boundary_crossed=False,
    )

    entry = lawbook_entry_from_proof_digestion(digest)

    assert digest.is_digested()
    assert not digest.is_truth_terminal()
    assert not entry.is_truth_entry()
    assert review_lawbook_candidate(entry).decision == LawbookReviewDecision.NEEDS_VERIFIER


def test_statement_fidelity_and_generalization_remain_separate_from_truth():
    """Formalization fidelity and proposed reuse are independently qualified."""
    claim = _verified_claim_entry()
    fidelity = FaithfulnessAssessment(
        assessment_id="faithfulness-001",
        domain_kernel_id="informal-conjecture",
        formal_world_id="lean-world",
        embedding_id="statement-translation",
        object_logic="informal mathematics",
        host_logic="Lean",
        status=FaithfulnessStatus.MECHANIZED,
        soundness_status=SoundnessStatus.SOUND,
        proof_artifact_id="statement-check-001",
    )
    generalization = ReusableSchemaCandidate(
        schema_id="schema-001",
        certificate_id="lean-cert-001",
        name="possible-generalization",
        pattern="candidate reusable proof pattern",
    )

    assert review_lawbook_candidate(claim).decision == LawbookReviewDecision.ACCEPT
    assert fidelity.is_promotion_supporting()
    assert generalization.advisory is True


def test_real_verified_lean_artifact_supports_independent_unknown_axes():
    """Replay the decomposition on an existing public MathGraph VERIFIED_PROOF artifact."""
    artifact = json.loads(
        (ROOT / "artifacts/lawbook/finite_htilt_survivor_law_v1.json").read_text(encoding="utf-8")
    )
    state = json.loads(
        (
            ROOT
            / "experiments/epistemic_orthogonality_v0/finite_htilt_survivor_state.json"
        ).read_text(encoding="utf-8")
    )

    assert artifact["record_type"] == "LAWBOOK_ENTRY"
    assert artifact["status"] == "VERIFIED_PROOF"
    assert artifact["boundary"]["type"] == "Lean"
    assert artifact["boundary"]["lean_status"] == "compiled"
    assert artifact["boundary"]["no_sorry"] is True
    assert artifact["boundary"]["no_admit"] is True
    assert artifact["boundary"]["no_axiom"] is True

    digest = ProofDigestionTrace(
        trace_id="finite-htilt-survivor-digest-state",
        proof_artifact_ids=(artifact["artifact_id"],),
        status=DigestionStatus.UNDIGESTED,
    )
    fidelity = FaithfulnessAssessment(
        assessment_id="finite-htilt-survivor-fidelity-state",
        domain_kernel_id=artifact["domain"],
        formal_world_id="lean",
        embedding_id="informal-to-formal-core",
        object_logic="informal mathematics",
        host_logic="Lean",
        status=FaithfulnessStatus.UNKNOWN,
        soundness_status=SoundnessStatus.UNKNOWN,
        proof_artifact_id=artifact["artifact_id"],
    )
    generalization = ReusableSchemaCandidate(
        schema_id="finite-htilt-survivor-generalization-state",
        proof_artifact_id=artifact["artifact_id"],
        name="unqualified-generalization",
        pattern="not yet independently qualified",
    )

    assert state["source_artifact_git_blob"] == "5fb0374a44ce699f23287c2c045a6927b781c2a3"
    assert state["formal_verification"]["status"] == artifact["status"]
    assert state["human_digest"]["status"] == digest.status.value == "UNDIGESTED"
    assert state["statement_fidelity"]["status"] == fidelity.status.value == "UNKNOWN"
    assert state["reusable_generalization"]["status"] == "UNKNOWN"
    assert not digest.is_digested()
    assert not fidelity.is_promotion_supporting()
    assert generalization.advisory is True
