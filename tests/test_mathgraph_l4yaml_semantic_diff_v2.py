"""Generative-but-frozen native differential contract; no claim of universal coverage."""

import json
from io import BytesIO
import zipfile

import pytest

from research.l4yaml_semantic_diff_v2.differential import (
    classify_native, generate_cases, reject_unreplayed_commit,
    check_installed_oracle_composer, check_installed_pyyaml_module,
    corroborate_ordinary_with_pyyaml,
)


def test_fixed_grammars_cover_180_alias_and_352_ordinary_unique_inputs():
    alias, ordinary = generate_cases()
    assert (len(alias), len(ordinary)) == (180, 352)
    assert len({r["input"] for r in alias + ordinary}) == 532
    assert len({r["family"] for r in alias}) == 12
    assert len([r for r in ordinary if r["family"] == "explicit_string"]) == 1
    assert '[&x [&x [&x 1]], *x]' in {r["input"] for r in alias}
    assert "k: !!str true\n" in {r["input"] for r in ordinary}


def fixture():
    oracle = [
        {"input": "[1]", "suite": "ordinary", "family": "simple", "expected": [1]},
        {"input": "[&x [&x 1], *x]", "suite": "anchor", "family": "nested", "value": "1", "expected": [[1], 1]},
    ]
    native = [
        {"input": "[1]", "legacy": {"status": "ok", "value": "[1]"},
         "indexed": {"status": "ok", "value": "[1]"}},
        {"input": "[&x [&x 1], *x]", "legacy": {"status": "ok", "value": "[[1],[1]]"},
         "indexed": {"status": "ok", "value": "[[1],[1]]"}},
    ]
    return oracle, [json.dumps(row) for row in native]


def test_independent_native_mismatch_is_preserved_but_controls_remain_warrantable():
    oracle, lines = fixture()
    report = classify_native(oracle, lines)
    assert report["cases"] == 2
    assert report["mismatched"] == 1
    assert report["matched"] == 1
    assert report["legacy_indexed_disagreement"] == 0
    assert report["by_suite"]["anchor"]["mismatched"] == 1
    assert report["by_suite"]["ordinary"]["matched"] == 1


def test_real_repair_must_be_recognized_as_bounded_match():
    oracle, lines = fixture()
    repaired = json.loads(lines[1])
    for mode in ("legacy", "indexed"):
        repaired[mode]["value"] = "[[1],1]"
    lines[1] = json.dumps(repaired)
    assert classify_native(oracle, lines)["mismatched"] == 0


def test_native_bool_cannot_masquerade_as_integer_under_python_equality():
    oracle, lines = fixture()
    oracle[0]["expected"] = [True]
    # The native value is still JSON integer 1, not Boolean true.
    result = classify_native(oracle, lines)
    assert result["matched"] == 0
    assert result["mismatched"] == 2


@pytest.mark.parametrize("tamper", [
    lambda lines: lines.pop(),
    lambda lines: lines.append(lines[0]),
    lambda lines: lines.__setitem__(1, lines[0]),
    lambda lines: lines.__setitem__(0, '{"input":"[1]","input":"[1]"}'),
    lambda lines: lines.__setitem__(0, '{"input":"[1]","legacy":{"status":"ok","value":"NaN"},"indexed":{"status":"ok","value":"[1]"}}'),
])
def test_incomplete_duplicate_or_untrusted_native_log_rejects(tamper):
    oracle, lines = fixture()
    tamper(lines)
    with pytest.raises(ValueError):
        classify_native(oracle, lines)


def test_disagreement_between_native_paths_is_not_suppressed():
    oracle, lines = fixture()
    changed = json.loads(lines[0]); changed["indexed"]["value"] = "[2]"
    lines[0] = json.dumps(changed)
    report = classify_native(oracle, lines)
    assert report["legacy_indexed_disagreement"] == 1
    assert report["mismatched"] == 2


def test_old_receipt_never_transports_to_a_new_commit_by_hash_label():
    old = "82cdb78e8909f25d9079d9bb05ed7c6f508ee95c"
    assert reject_unreplayed_commit(old, old) is False
    assert reject_unreplayed_commit(old, "f" * 40) is True
    with pytest.raises(ValueError):
        reject_unreplayed_commit(old, "not-a-commit")


def test_oracle_package_contents_must_match_wheel_not_only_version():
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("ruamel/yaml/composer.py", b"qualifier = 1")
    check_installed_oracle_composer(buffer.getvalue(), b"qualifier = 1")
    with pytest.raises(ValueError, match="ORACLE_COMPOSER_BYTES_CHANGED"):
        check_installed_oracle_composer(buffer.getvalue(), b"qualifier = 2")


def test_second_parser_corroborates_only_the_declared_ordinary_subset():
    qualified = [{"input": "[1]", "suite": "ordinary", "family": "simple", "expected": [1]}]
    assert corroborate_ordinary_with_pyyaml(qualified) == 1
    qualified[0]["expected"] = [2]
    with pytest.raises(ValueError, match="SECOND_PARSER_DISAGREES"):
        corroborate_ordinary_with_pyyaml(qualified)


def test_second_parser_bool_vs_integer_must_be_distinct():
    # YAML "true" is Boolean, whereas Python compares True == 1.
    qualified = [{"input": "true\n", "suite": "ordinary", "family": "bool", "expected": 1}]
    with pytest.raises(ValueError, match="SECOND_PARSER_DISAGREES"):
        corroborate_ordinary_with_pyyaml(qualified)


def test_second_parser_installed_bytes_are_bound_to_its_wheel():
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("yaml/constructor.py", b"constructor = 1")
        z.writestr("yaml/loader.py", b"loader = 1")
    check_installed_pyyaml_module(buffer.getvalue(), b"constructor = 1", b"loader = 1")
    with pytest.raises(ValueError, match="SECOND_PARSER_BYTES_CHANGED"):
        check_installed_pyyaml_module(buffer.getvalue(), b"constructor = 2", b"loader = 1")
