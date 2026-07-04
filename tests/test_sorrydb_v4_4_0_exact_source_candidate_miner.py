import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/sorrydb/sorrydb_v4_4_0_exact_source_candidate_miner.py"
OUTPUT = ROOT / "artifacts/sorrydb/mined_queues/sorrydb_v4_4_0_exact_source_candidates.json"
QUEUE_RUNNER = ROOT / "experiments/sorrydb/sorrydb_v4_3_5_json_patch_queue_runner.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_evidence(root: Path, *, patch_snippet: str = "  exact True.intro"):
    manifests = root / "manifests"
    certificates = root / "certificates"
    source = root / "repo" / "Example.lean"
    manifests.mkdir(parents=True)
    certificates.mkdir(parents=True)
    source.parent.mkdir(parents=True)
    source_snippet = "example : True := by\n  sorry"
    source.write_text(f"namespace Fixture\n{source_snippet}\nend Fixture\n", encoding="utf-8")

    certificate = {
        "certificate_id": "accepted-example",
        "certificate_version": "v4.test",
        "status": "PATCH_ACCEPTED",
        "final_verdict": "PATCH_ACCEPTED",
        "lean_returncode": 0,
        "file_path": "Example.lean",
        "source_snippet": source_snippet,
        "patch_snippet": patch_snippet,
        "project": "fixture/project",
        "project_commit": "abc123",
        "restore_check": "source restored",
    }
    manifest = {
        "verdict": "PATCH_ACCEPTED",
        "patch_verdict": "PATCH_ACCEPTED",
        "patch_result": {"returncode": 0},
        "patch_certificate_id": "accepted-example",
        "repo_root": str(source.parent),
        "file_path": "Example.lean",
        "source": str(source),
        "source_snippet": source_snippet,
        "patch_snippet": patch_snippet,
        "timeout_seconds": 10,
        "required_gb": 1,
    }
    (certificates / "accepted-example.json").write_text(json.dumps(certificate), encoding="utf-8")
    (manifests / "accepted-example.manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifests, certificates, source


def test_parse_known_spans():
    miner = load_module(SCRIPT, "sorrydb_v440_spans")
    assert miner.parse_known_spans(["3", "7:9"]) == [
        {"start_line": 3, "end_line": 3},
        {"start_line": 7, "end_line": 9},
    ]


def test_mines_valid_queue_entry_from_exact_evidence(tmp_path):
    miner = load_module(SCRIPT, "sorrydb_v440_valid")
    queue_runner = load_module(QUEUE_RUNNER, "sorrydb_v435_for_v440")
    manifests, certificates, source = write_evidence(tmp_path)

    queue = miner.mine_queue(
        manifests,
        certificates,
        source,
        [{"start_line": 3, "end_line": 3}],
    )
    assert queue["candidate_count"] == 1
    assert queue["obstruction_count"] == 0
    candidate = queue["candidates"][0]
    assert candidate["source_span"] == {"start_line": 2, "end_line": 3}
    assert candidate["sorry_span"] == {"start_line": 3, "end_line": 3}
    assert candidate["certificate_id"] == "accepted-example"

    output = tmp_path / "queue.json"
    output.write_text(json.dumps(queue), encoding="utf-8")
    loaded, obstruction = queue_runner.load_queue(output)
    assert obstruction == ""
    assert loaded == queue["candidates"]


def test_mismatch_becomes_named_obstruction(tmp_path):
    miner = load_module(SCRIPT, "sorrydb_v440_mismatch")
    manifests, certificates, source = write_evidence(tmp_path)
    certificate_path = certificates / "accepted-example.json"
    certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
    certificate["patch_snippet"] = "  exact by trivial"
    certificate_path.write_text(json.dumps(certificate), encoding="utf-8")

    queue = miner.mine_queue(
        manifests,
        certificates,
        source,
        [{"start_line": 3, "end_line": 3}],
    )
    assert queue["candidate_count"] == 0
    assert queue["obstructions"][0]["terminal_form"] == "NAMED_OBSTRUCTION"
    assert queue["obstructions"][0]["reason"] == "EVIDENCE_FIELD_MISMATCH:patch_snippet"


def test_ambiguous_source_and_unknown_span_are_obstructions(tmp_path):
    miner = load_module(SCRIPT, "sorrydb_v440_source_boundaries")
    manifests, certificates, source = write_evidence(tmp_path)
    original = source.read_text(encoding="utf-8")
    source.write_text(original + original, encoding="utf-8")
    ambiguous = miner.mine_queue(
        manifests,
        certificates,
        source,
        [{"start_line": 3, "end_line": 3}],
    )
    assert ambiguous["obstructions"][0]["reason"] == "EXACT_SOURCE_SNIPPET_AMBIGUOUS"

    source.write_text(original, encoding="utf-8")
    outside = miner.mine_queue(
        manifests,
        certificates,
        source,
        [{"start_line": 99, "end_line": 99}],
    )
    assert outside["obstructions"][0]["reason"] == "SORRY_OUTSIDE_KNOWN_SPANS"


def test_committed_mined_queue_is_bounded_and_runner_valid():
    queue_runner = load_module(QUEUE_RUNNER, "sorrydb_v435_committed_v440")
    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert data["status"] == "MINED_CANDIDATE_QUEUE"
    assert data["candidate_count"] == 2
    assert data["obstruction_count"] == 0
    assert data["does_not_claim"] == [
        "new proof discovery",
        "general SorryDB mining",
        "upstream automation",
    ]
    candidates, obstruction = queue_runner.load_queue(OUTPUT)
    assert obstruction == ""
    assert len(candidates) == 2


def test_doc_records_exact_boundary():
    text = (ROOT / "docs/sorrydb_v4_4_0_exact_source_candidate_miner.md").read_text(encoding="utf-8")
    for phrase in (
        "exact source/patch/certificate rows",
        "new proof discovery",
        "general SorryDB mining",
        "upstream automation",
        "candidate",
    ):
        assert phrase in text
