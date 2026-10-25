# V4 prospective first attempt: apparatus RED, not scientific source failure

Source and method already sealed:
- frozen static export method commit `7f38aa7029c8d89006db956941767033b09717ca`;
- original frozen V3 proposer/comparator/evaluator `b13f64c3caa2210f8c9aa17423d210063683a119`;
- first metadata-eligible, ROS-unexposed future `mozillazg/python-pinyin@85bf408b3b326676e4e1ffa727f8063774f709f6`, selection commit `d148301914ab1f88fe70d396205a6246c24c720b`.

**CI attempt #39222569377** failed on missing native test-runner plugin (`pytest.ini` explicitly requires `--cov-report term-missing`; original pinned `requirements_dev.txt` and `pyproject.toml [dependency-groups].dev` declare `pytest-cov`). Zero real original pytest test results; do not count the CI failure as a scientific negative.

**Pre-native protocol integrity independently completed:** SHA-pinned V4/V3 method/selection checks, exact upstream checkout, static export closure and candidate/comparator proposal sealing. The previously missing public API symbol was recovered: `pypinyin.slug`. Both frozen relation proposers emitted the *same* two obligations (idempotence and independent percent encoding). Neither proposal was allowed to see native outcomes before sealing.

**Recovery boundary:** edit ONLY GitHub Actions test environment to install source-declared `pytest-cov`, correct the shell's explicit `set +e` on native-test execution so actual failures are archived, and retain the exact same first eligible source SHA and all static/proposer/evaluator source SHA pins, fixtures and declared success criteria. No new test inputs or semantics after exposure. The first apparatus RED must remain in lineage. Future semantic verdict requires a completed pinned original test suite and unchanged independent evaluator.
