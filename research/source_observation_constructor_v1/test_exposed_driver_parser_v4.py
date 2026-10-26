#!/usr/bin/env python3
"""Source-free exact test-ID parser controls, including adversarial interruptions."""
import importlib.util
import json
from pathlib import Path
import sys

spec=importlib.util.spec_from_file_location(
    "md2_parser_v4", Path(__file__).with_name("exposed_driver_replay_v4.py"))
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


def check(log, expected, count=None):
    got=mod.extract_native_ids(log)
    assert got["status"]==expected,(got,expected)
    if count is not None:
        assert got.get("count")==count,(got,count)
    return got


def main():
    exact="cli/filevars/a ... ok\nmarkdown2/tm/b [tags] ... ok\n\nRan 2 tests in 0.01s\n\nOK\n"
    good="markdown2/tm/b ... WARNING:test:skipping pygments tests ('pygments' module not found)\nWARNING:test:skipping emoji tests ('emoji' module not found)\nok\ncli/filevars/a ... ok\n\nRan 2 tests in 0.01s\n\nOK\n"
    good_ref=check(good,"WARRANTED_BOUNDED_EXECUTED_NATIVE_IDS",2)
    assert good_ref["recognized_optional_dependency_warnings"]==2
    assert good_ref["case_ids"]==["cli/filevars/a","markdown2/tm/b"]
    check(exact,"WARRANTED_BOUNDED_EXECUTED_NATIVE_IDS",2)
    check(good.replace("Ran 2 tests","Ran 3 tests"),"UNKNOWN_AUTHOR_NATIVE_TEST_IDENTITIES")
    check(good.replace("WARNING:test:skipping emoji", "WARNING:test:skipping dangerous"),
          "UNKNOWN_AUTHOR_NATIVE_TEST_IDENTITIES")
    check(good.replace("\nok\n", "\nUNKNOWN\n"),
          "UNKNOWN_AUTHOR_NATIVE_TEST_IDENTITIES")
    check(good.replace("cli/filevars/a", "markdown2/tm/b"),"UNKNOWN_AUTHOR_NATIVE_TEST_IDENTITIES")
    check(good.replace("cli/filevars/a ... ok\n",""),
          "UNKNOWN_AUTHOR_NATIVE_TEST_IDENTITIES")
    check(good.replace("cli/filevars/a ... ok", "cli/filevars/a ... FAIL"),
          "UNKNOWN_NATIVE_FAILURE")
    check(good.replace("Ran 2 tests in 0.01s", "summary missing"),
          "UNKNOWN_AUTHOR_NATIVE_CASE_SUMMARY")
    check(good.replace("Ran 2 tests in 0.01s", "Ran 2 tests in 0.01s\nRan 2 tests in 0.01s"),
          "UNKNOWN_AUTHOR_NATIVE_CASE_SUMMARY")
    cases=10
    print(json.dumps({"status":"PASS_F1_V4B_SOURCE_FREE_PARSER",
                      "targeted_cases":cases,"protected_source_access":"NONE",
                      "not_proved":"real author intent or native runner unforgeability"},sort_keys=True))


if __name__=="__main__":
    main()
