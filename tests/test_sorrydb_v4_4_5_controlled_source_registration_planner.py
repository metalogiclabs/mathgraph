import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/sorrydb/sorrydb_v4_4_5_controlled_source_registration_planner.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sorrydb_v445_registration", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_fixture(
    root: Path,
    *,
    repo_root: str = "/tmp/unstable-checkout",
    project: str = "fixture/project",
    commit: str = "abc123",
    file_path: str = "Example.lean",
    source_hash: str | None = None,
) -> tuple[Path, Path, Path, str, str]:
    source_snippet = "example : True := by\n  sorry"
    patch_snippet = "example : True := by\n  trivial"
    source_hash = digest(source_snippet) if source_hash is None else source_hash
    patch_hash = digest(patch_snippet)

    snippets = root / "source_snippets"
    snippets.mkdir(parents=True, exist_ok=True)
    snippet_path = snippets / "source-input-case.json"
    snippet_path.write_text(
        json.dumps(
            {
                "row_id": "source-input-case",
                "certificate_id": "source-input-case",
                "file_path": file_path,
                "source_snippet": source_snippet,
                "source_snippet_sha256": digest(source_snippet),
                "patch_snippet": patch_snippet,
                "patch_snippet_sha256": patch_hash,
                "status": "SOURCE_CHECKOUT_PATH_UNSTABLE",
            }
        ),
        encoding="utf-8",
    )
    certificate = {
        "certificate_id": "source-input-case",
        "project": project,
        "project_commit": commit,
        "file_path": file_path,
    }
    cert_path = root / "certificates" / "source-input-case.json"
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    cert_path.write_text(json.dumps(certificate), encoding="utf-8")
    ledger = {
        "version": "v4.4.4",
        "rows": [
            {
                "row_id": "source-input-case",
                "source_input_status": "SOURCE_CHECKOUT_PATH_UNSTABLE",
                "certificate_id": "source-input-case",
                "file_path": file_path,
                "known_repo_root": repo_root,
                "known_repo_root_is_stable": False,
                "source_snippet_hash": source_hash,
                "patch_snippet_hash": patch_hash,
                "source_snippet_file": "source_snippets/source-input-case.json",
            }
        ],
    }
    ledger_path = root / "source_input_ledger.json"
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
    return ledger_path, snippets, cert_path, source_snippet, patch_snippet


def build_one(mod, root: Path, ledger_path: Path, snippets: Path, controlled: list[Path]):
    return mod.build_registration_plan(
        ledger_path,
        snippet_dir=snippets,
        reference_dirs=[root],
        controlled_source_dirs=controlled,
    )


def test_controlled_source_with_matching_snippet_is_ready(tmp_path):
    mod = load_module()
    controlled = tmp_path / "controlled"
    repo = controlled / "repo"
    repo.mkdir(parents=True)
    ledger_path, snippets, _, source_snippet, _ = write_fixture(
        tmp_path / "evidence",
        repo_root=str(repo),
    )
    (repo / "Example.lean").write_text(f"namespace T\n{source_snippet}\nend T\n", encoding="utf-8")
    summary, plan, _ = build_one(mod, tmp_path, ledger_path, snippets, [controlled])
    assert summary["registration_ready_count"] == 1
    assert plan["rows"][0]["registration_status"] == mod.REGISTRATION_READY_FROM_EXISTING_CHECKOUT


def test_url_and_commit_require_future_network_hydration(tmp_path):
    mod = load_module()
    ledger_path, snippets, _, _, _ = write_fixture(tmp_path)
    summary, plan, _ = build_one(mod, tmp_path, ledger_path, snippets, [tmp_path / "controlled"])
    assert summary["network_hydration_needed_count"] == 1
    row = plan["rows"][0]
    assert row["registration_status"] == mod.REGISTRATION_NEEDS_NETWORK_HYDRATION
    assert row["repo_url"] == "https://github.com/fixture/project"


def test_missing_repo_identity_is_blocked(tmp_path):
    mod = load_module()
    ledger_path, snippets, _, _, _ = write_fixture(tmp_path, project="", commit="")
    summary, _, _ = build_one(mod, tmp_path, ledger_path, snippets, [tmp_path / "controlled"])
    assert summary["category_counts"][mod.REGISTRATION_BLOCKED_INSUFFICIENT_REPO_IDENTITY] == 1


def test_missing_file_path_is_blocked(tmp_path):
    mod = load_module()
    ledger_path, snippets, _, _, _ = write_fixture(tmp_path, file_path="")
    summary, _, _ = build_one(mod, tmp_path, ledger_path, snippets, [tmp_path / "controlled"])
    assert summary["category_counts"][mod.REGISTRATION_BLOCKED_INSUFFICIENT_FILE_IDENTITY] == 1


def test_missing_snippet_hash_is_blocked(tmp_path):
    mod = load_module()
    ledger_path, snippets, _, _, _ = write_fixture(tmp_path, source_hash="")
    summary, _, _ = build_one(mod, tmp_path, ledger_path, snippets, [tmp_path / "controlled"])
    assert summary["category_counts"][mod.REGISTRATION_BLOCKED_MISSING_SNIPPET_HASH] == 1


def test_snippet_evidence_creates_non_replay_ready_fixture_plan(tmp_path):
    mod = load_module()
    ledger_path, snippets, _, _, _ = write_fixture(tmp_path)
    _, _, fixture_plan = build_one(mod, tmp_path, ledger_path, snippets, [tmp_path / "controlled"])
    assert len(fixture_plan["fixture_candidates"]) == 1
    assert fixture_plan["fixture_candidates"][0]["replay_ready"] is False
    assert fixture_plan["fixture_policy"]["actual_fixtures_created"] is False


def test_summary_category_counts_are_stable(tmp_path):
    mod = load_module()
    ledger_path, snippets, _, _, _ = write_fixture(tmp_path)
    summary, _, _ = build_one(mod, tmp_path, ledger_path, snippets, [tmp_path / "controlled"])
    assert list(summary["category_counts"]) == list(mod.CATEGORIES)
    assert sum(summary["category_counts"].values()) == 1
    assert summary["unstable_source_row_count"] == 1


def test_missing_source_ledger_records_note_without_crashing(tmp_path):
    mod = load_module()
    missing = tmp_path / "missing-ledger.json"
    summary, plan, fixture_plan = mod.build_registration_plan(
        missing,
        snippet_dir=tmp_path / "snippets",
        reference_dirs=[],
        controlled_source_dirs=[tmp_path / "controlled"],
    )
    assert summary["unstable_source_row_count"] == 0
    assert plan["rows"] == []
    assert fixture_plan["fixture_candidates"] == []
    assert any("missing source input ledger" in note for note in plan["notes"])
