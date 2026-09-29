from pathlib import Path

import pytest

from mathgraph.lean_import_slice import (
    materialize_slice,
    parse_imports,
    resolve_local_import_closure,
)


def test_parse_imports_supports_visibility_prefixes() -> None:
    assert parse_imports("""
import A.B
public import C.D
private import E.F
""") == ("A.B", "C.D", "E.F")


def test_exact_transitive_local_import_slice(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "A").mkdir(parents=True)
    (root / "B").mkdir(parents=True)
    (root / "A" / "Top.lean").write_text("import B.Middle\nimport Mathlib\n")
    (root / "B" / "Middle.lean").write_text("import B.Leaf\n")
    (root / "B" / "Leaf.lean").write_text("theorem leaf : True := by trivial\n")
    for name in ("lakefile.lean", "lake-manifest.json", "lean-toolchain"):
        (root / name).write_text(name)

    report = resolve_local_import_closure(root, ["A/Top.lean"])
    assert report["file_count"] == 3
    assert [x["path"] for x in report["files"]] == [
        "A/Top.lean", "B/Leaf.lean", "B/Middle.lean"
    ]
    assert not report["unresolved_local_candidates"]

    extra = tmp_path / "FinalCheck.lean"
    extra.write_text("import A.Top\n")
    out = tmp_path / "slice"
    result = materialize_slice(
        root, ["A/Top.lean"], out,
        extra_files=[(extra, "FinalCheck.lean")],
    )
    assert (out / "A/Top.lean").exists()
    assert (out / "B/Leaf.lean").exists()
    assert (out / "FinalCheck.lean").exists()
    assert result["status"] == "CANDIDATE_UNTIL_ISOLATED_BUILD"


def test_missing_project_local_import_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "Theorems").mkdir(parents=True)
    (root / "Theorems" / "Top.lean").write_text("import P2M.Missing\n")
    report = resolve_local_import_closure(root, ["Theorems/Top.lean"])
    assert report["unresolved_local_candidates"] == ["P2M.Missing"]
