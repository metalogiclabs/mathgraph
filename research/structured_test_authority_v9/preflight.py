#!/usr/bin/env python3
"""Pre-exposure synthetic structured source-author pytest scope tests and exposed Bottle calibration."""
import argparse,importlib.util,json,pathlib,tempfile


def load(name,path):
    spec=importlib.util.spec_from_file_location("structured_v9_"+name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--exposed",type=pathlib.Path,required=True)
    a=parser.parse_args()
    here=pathlib.Path(__file__).parent
    scan=load("scan",here/"scan.py")
    evalmod=load("evaluate",here/"evaluate.py")
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td);(root/"tests").mkdir()
        (root/"tests"/"test_scope.py").write_text("def test_one(): assert 2 + 2 == 4\ndef test_two(): assert 3 * 3 == 9\n")
        pyproject=root/"pyproject.toml"
        original='[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
        pyproject.write_text(original)
        (root/"Makefile").write_text(".PHONY: test\ntest:\n\t$(VENV)/bin/pytest\n")
        before=scan.scan(root)
        expert=scan.cookbook(root)
        assert before["status"]=="CANDIDATE_SOURCE_CONFIGURED_PYTEST_ROOTS",before
        assert before["make_signal"]["signal"]=="MAKEFILE_TEST_TARGET_POINTS_TO_PYTEST"
        assert before["selected"]["testpaths"]==expert["selected"]["testpaths"]==["tests"]
        meta={"repository":"synthetic/test-fixture","source_sha":"f"*40}
        selection={"selected":meta}
        proposal={"source":meta,"candidate":before,"expert_rule":expert}
        selectionfile=root/"lock.json";selectionfile.write_text(json.dumps(selection))
        proposalfile=root/"proposal.json";proposalfile.write_text(json.dumps(proposal))
        resultfile=root/"results"/"receipt.json"
        # Strict original native pytest and both equal-informed arms.
        import sys
        old=sys.argv
        sys.argv=["evaluate.py","--source",str(root),"--selection",str(selectionfile),
                  "--proposal",str(proposalfile),"--out",str(resultfile)]
        try:evalmod.main()
        finally:sys.argv=old
        result=json.loads(resultfile.read_text())
        assert all(v.startswith("WARRANTED") for v in result["status"].values()),result
        assert result["comparison"]["default_testcases"]==2
        assert result["comparison"]["candidate_equals_default"] is True
        assert result["comparison"]["candidate_equals_expert"] is True
        old_sha=before["evidence_files"]["pyproject.toml"]
        # Physically withdraw ONLY source configuration authority, not native tests.
        pyproject.write_text("[tool.pytest.ini_options]\n")
        withdrawn=scan.scan(root)
        assert withdrawn["status"]=="CANDIDATE_AUTHOR_MAKE_PYTEST_NO_ROOT_AUTHORITY",withdrawn
        assert withdrawn["selected"] is None
        assert scan.cookbook(root)["selected"] is None
        assert withdrawn["make_signal"]==before["make_signal"]
        pyproject.write_text(original)
        restored=scan.scan(root)
        assert restored["selected"]==before["selected"]
        assert restored["evidence_files"]["pyproject.toml"]==old_sha
        # Separate alternate explicit config conflicts with root config -> fail closed.
        (root/"pytest.ini").write_text("[pytest]\ntestpaths = other\n")
        (root/"other").mkdir()
        assert scan.scan(root)["status"]=="UNKNOWN_CONFLICTING_PYTEST_ROOTS"
        (root/"pytest.ini").unlink()
        # Invalid path traversal is not an excuse to run arbitrary targets.
        pyproject.write_text('[tool.pytest.ini_options]\ntestpaths = ["../other"]\n')
        assert scan.scan(root)["selected"] is None
        assert any("invalid_testpaths" in x for x in scan.scan(root)["unknowns"])
    # EXPOSED Bottle V8 training only. It is not new source science.
    bottle=scan.scan(a.exposed)
    assert "pyproject.toml" in bottle["evidence_files"],bottle
    assert bottle["selected"] and bottle["selected"]["testpaths"]==["test"],bottle
    assert bottle["make_signal"] is not None,bottle
    print("V9_SYNTHETIC_PYTEST_CASE_ID_AND_SOURCE_WITHDRAWAL_GREEN; EXPOSED_BOTTLE_STRUCTURED_AUTHORITY",bottle["status"])


if __name__=="__main__":
    main()
