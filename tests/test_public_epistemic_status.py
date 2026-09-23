import json
import subprocess
import sys
from pathlib import Path

from mathgraph.epistemic_status import (
    audit_epistemic_status_view,
    build_epistemic_status_view,
    epistemic_status_to_markdown,
)
from mathgraph.lawbook import lawbook_entry_from_certificate_like
from mathgraph.certificates import TerminalForm
from mathgraph.proof_digestion import DigestionStatus, ProofDigestionTrace, ReusableSchemaCandidate
from mathgraph.api_service import artifact_to_api_dict
from mathgraph.demo_release import public_demo_report_to_markdown, run_public_demo


ROOT = Path(__file__).resolve().parents[1]


def test_verified_claim_surfaces_four_independent_axes():
    claim = lawbook_entry_from_certificate_like(
        claim_id="claim-1",
        terminal_form=TerminalForm.VERIFIED_PROOF,
        certificate_id="cert-1",
        verifier_boundary_crossed=True,
        provenance={"verifier": "lean"},
    )

    view = build_epistemic_status_view(claim)

    assert view["verification"]["status"] == "VERIFIED_PROOF"
    assert view["verification"]["truth_promoting"] is True
    assert view["human_digest"]["status"] == "UNKNOWN"
    assert view["human_digest"]["truth_promoting"] is False
    assert view["statement_fidelity"]["status"] == "UNKNOWN"
    assert view["statement_fidelity"]["truth_promoting"] is False
    assert view["generalization"]["status"] == "UNKNOWN"
    assert view["generalization"]["truth_promoting"] is False
    assert not [x for x in audit_epistemic_status_view(view) if x["severity"] == "CRITICAL"]


def test_exposition_and_generalization_never_promote_truth():
    digest = ProofDigestionTrace(
        trace_id="digest-1",
        status=DigestionStatus.EXPOSITION_READY,
    )
    schema = ReusableSchemaCandidate(
        schema_id="schema-1",
        name="candidate pattern",
        pattern="possible reusable structure",
    )

    digest_view = build_epistemic_status_view(digest)
    schema_view = build_epistemic_status_view(schema)

    assert digest_view["verification"]["truth_promoting"] is False
    assert digest_view["human_digest"]["status"] == "EXPOSITION_READY"
    assert digest_view["human_digest"]["truth_promoting"] is False
    assert schema_view["generalization"]["status"] == "ADVISORY_CANDIDATE"
    assert schema_view["generalization"]["truth_promoting"] is False


def test_real_public_lean_artifact_renders_inherited_warrant_without_axis_leak():
    artifact = json.loads(
        (ROOT / "artifacts/lawbook/finite_htilt_survivor_law_v1.json").read_text(encoding="utf-8")
    )
    sidecar = json.loads(
        (
            ROOT
            / "experiments/epistemic_orthogonality_v0/finite_htilt_survivor_state.json"
        ).read_text(encoding="utf-8")
    )

    view = build_epistemic_status_view(artifact, sidecar=sidecar)

    assert view["verification"]["status"] == "VERIFIED_PROOF"
    assert view["verification"]["authority"] == "INHERITED_VERIFIER_BOUND"
    assert view["verification"]["truth_promoting"] is True
    assert view["human_digest"]["status"] == "UNDIGESTED"
    assert view["statement_fidelity"]["status"] == "UNKNOWN"
    assert view["generalization"]["status"] == "UNKNOWN"
    assert all(
        view[axis]["truth_promoting"] is False
        for axis in ("human_digest", "statement_fidelity", "generalization")
    )
    assert not [x for x in audit_epistemic_status_view(view) if x["severity"] == "CRITICAL"]

    markdown = epistemic_status_to_markdown(view)
    assert "Epistemic Status" in markdown
    assert "VERIFIED_PROOF" in markdown
    assert "UNDIGESTED" in markdown
    assert "Statement fidelity" in markdown
    assert "Generalization" in markdown


def test_api_artifacts_include_epistemic_status_without_changing_truth_boundary():
    claim = lawbook_entry_from_certificate_like(
        claim_id="claim-api",
        terminal_form=TerminalForm.VERIFIED_PROOF,
        certificate_id="cert-api",
        verifier_boundary_crossed=True,
        provenance={"verifier": "lean"},
    )

    wrapped = artifact_to_api_dict(claim)

    assert wrapped["truth_boundary"]["verifier_boundary_crossed"] is True
    assert wrapped["epistemic_status"]["verification"]["status"] == "VERIFIED_PROOF"
    assert wrapped["epistemic_status"]["human_digest"]["status"] == "UNKNOWN"


def test_public_demo_explains_epistemic_axes_even_when_no_claim_is_verified():
    report = run_public_demo()
    markdown = public_demo_report_to_markdown(report)

    assert "Epistemic Status" in markdown
    assert "Verification" in markdown
    assert "Human digest" in markdown
    assert "Statement fidelity" in markdown
    assert "Generalization" in markdown
    assert "do not promote truth" in markdown


def test_status_renderer_cli_emits_real_artifact_card(tmp_path):
    out = tmp_path / "status.md"
    subprocess.run(
        [
            sys.executable,
            "scripts/render_epistemic_status.py",
            "--artifact",
            "artifacts/lawbook/finite_htilt_survivor_law_v1.json",
            "--sidecar",
            "experiments/epistemic_orthogonality_v0/finite_htilt_survivor_state.json",
            "--format",
            "markdown",
            "--out",
            str(out),
            "--fail-on-critical",
        ],
        cwd=ROOT,
        check=True,
    )
    text = out.read_text(encoding="utf-8")
    assert "VERIFIED_PROOF" in text
    assert "UNDIGESTED" in text
