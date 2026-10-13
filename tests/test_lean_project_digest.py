import csv
import json

from mathgraph.lean_project_digest import digest_lean_files, run_lean_project_digest
from scripts.run_repo_architecture_audit import ROOT, run_audit


def test_fallback_demo_emits_expected_files_and_trust_audit(tmp_path) -> None:
    report = run_lean_project_digest(tmp_path / "digest", fallback_demo=True)
    assert report.mode == "fallback-demo"
    assert report.declaration_count >= 5
    assert report.incomplete_proof_count == 1
    assert report.axiom_count == 1
    assert report.unsafe_count == 1
    assert report.can_promote_truth_count == 0
    assert report.advisory_boundary_ok is True

    out = tmp_path / "digest"
    for name in (
        "project_manifest.json",
        "declaration_inventory.csv",
        "import_graph.csv",
        "trust_boundary_audit.json",
        "lawbook_entries.jsonl",
        "reason_atlas_routes.csv",
        "lean_project_digest_report.md",
    ):
        assert (out / name).exists()

    manifest = json.loads((out / "project_manifest.json").read_text(encoding="utf-8"))
    assert manifest["boundary_type"] == "textual_digest"
    assert manifest["can_promote_truth"] is False
    audit = json.loads((out / "trust_boundary_audit.json").read_text(encoding="utf-8"))
    assert audit["textual_parsing_is_advisory"] is True
    assert audit["lean_execution_confirmed"] is False
    assert audit["can_promote_truth_count"] == 0

    inventory = list(csv.DictReader((out / "declaration_inventory.csv").open(encoding="utf-8")))
    by_name = {row["name"]: row for row in inventory}
    assert by_name["unfinished_demo"]["trust_status"] == "incomplete_proof"
    assert by_name["external_axiom_demo"]["trust_status"] == "trusted_assumption_or_external_axiom"
    assert by_name["risky_demo"]["trust_status"] == "unsafe_requires_warning"
    assert {row["can_promote_truth"] for row in inventory} == {"False"}


def test_parser_keeps_sorry_admit_axiom_and_unsafe_out_of_verified_status() -> None:
    records, imports = digest_lean_files(
        [
            {
                "file": "Mini.lean",
                "text": "\n".join(
                    [
                        "import Mathlib.Init",
                        "theorem complete_demo : True := by trivial",
                        "lemma sorry_demo : True := by sorry",
                        "theorem admit_demo : True := by admit",
                        "axiom axiom_demo : False",
                        "unsafe def unsafe_demo : Nat := 0",
                    ]
                ),
            }
        ]
    )
    assert imports == [{"file": "Mini.lean", "import": "Mathlib.Init", "advisory_only": True, "can_promote_truth": False}]
    by_name = {row.name: row for row in records}
    assert by_name["complete_demo"].trust_status == "imported_verified_candidate"
    assert by_name["complete_demo"].can_promote_truth is False
    assert by_name["complete_demo"].advisory_only is True
    assert by_name["sorry_demo"].trust_status == "incomplete_proof"
    assert by_name["admit_demo"].trust_status == "incomplete_proof"
    assert by_name["axiom_demo"].trust_status == "trusted_assumption_or_external_axiom"
    assert by_name["unsafe_demo"].trust_status == "unsafe_requires_warning"


def test_project_root_mode_scans_lean_files_without_requiring_lean(tmp_path) -> None:
    project = tmp_path / "lean_project"
    (project / "MathGraphDemo").mkdir(parents=True)
    (project / "MathGraphDemo" / "Basic.lean").write_text(
        "\n".join(
            [
                "import Mathlib.Data.Nat.Basic",
                "def localValue : Nat := 1",
                "lemma localLemma : True := by trivial",
            ]
        ),
        encoding="utf-8",
    )
    report = run_lean_project_digest(tmp_path / "out", project_root=project)
    assert report.mode == "project-root"
    assert report.declaration_count == 2
    assert report.can_promote_truth_count == 0
    assert report.advisory_boundary_ok is True
    routes = list(csv.DictReader((tmp_path / "out" / "reason_atlas_routes.csv").open(encoding="utf-8")))
    assert routes
    assert {row["advisory_only"] for row in routes} == {"True"}
    assert {row["can_promote_truth"] for row in routes} == {"False"}


def test_committed_lean_digest_demo_preserves_public_boundary() -> None:
    demo = ROOT / "examples" / "lean_project_digest_demo"
    expected = {
        "README.md",
        "project_manifest.json",
        "declaration_inventory.csv",
        "import_graph.csv",
        "trust_boundary_audit.json",
        "lawbook_entries.jsonl",
        "reason_atlas_routes.csv",
        "lean_project_digest_report.md",
    }
    assert expected <= {path.name for path in demo.iterdir()}

    audit = json.loads((demo / "trust_boundary_audit.json").read_text(encoding="utf-8"))
    assert audit["advisory_boundary_ok"] is True
    assert audit["can_promote_truth_count"] == 0
    assert audit["textual_parsing_is_advisory"] is True
    assert audit["lean_execution_confirmed"] is False

    inventory = list(csv.DictReader((demo / "declaration_inventory.csv").open(encoding="utf-8")))
    statuses = {row["trust_status"] for row in inventory}
    assert "imported_verified_candidate" in statuses
    assert "incomplete_proof" in statuses
    assert "trusted_assumption_or_external_axiom" in statuses
    assert "unsafe_requires_warning" in statuses
    assert {row["can_promote_truth"] for row in inventory} == {"False"}

    lawbook_entries = [json.loads(line) for line in (demo / "lawbook_entries.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lawbook_entries
    assert {entry["can_promote_truth"] for entry in lawbook_entries} == {False}
    assert {entry["advisory_only"] for entry in lawbook_entries} == {True}


def test_lean_digest_documentation_and_readme_links_are_public_ready() -> None:
    guide = (ROOT / "docs" / "lean_project_digest.md").read_text(encoding="utf-8")
    lower = guide.lower()
    assert "textual parsing is advisory" in lower
    assert "verified_proof" in lower
    assert "can_promote_truth=false" in lower
    assert "sorry" in lower and "axiom" in lower and "unsafe" in lower

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/lean_project_digest.md" in readme
    assert "examples/lean_project_digest_demo/" in readme
    assert "docs/public/lean_project_digest_announcement.md" not in readme


def test_architecture_audit_recognizes_lean_digest_public_demo() -> None:
    report = run_audit(ROOT)
    assert report["canonical_doc_presence"]["examples/lean_project_digest_demo/README.md"] is True
    assert report["canonical_doc_presence"]["examples/lean_project_digest_demo/trust_boundary_audit.json"] is True
    assert report["lean_digest_demo_audit"]["all_present"] is True
    assert report["status"] == "PASS"
