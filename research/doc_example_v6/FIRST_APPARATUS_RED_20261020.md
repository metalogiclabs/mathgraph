# V6 first prospect apparatus RED — pristine source and presealed UNKNOWN retained

Status: **UNKNOWN_NATIVE_APPARATUS** on original first run, **UNKNOWN_NO_SAFE_LITERAL_SOURCE_EXAMPLE** at the independent pre-native proposal stage. This run is NOT native scientific GREEN despite the GitHub workflow's overall success (the intended fail-closed wrapper retained the native failure and did not promote anything).

Exact selected source `lepture/mistune@d449488ce6baf5bcc386186cc01c40bf2afdc82c` was locked before inspection at [491dafa](https://github.com/metalogiclabs/mathgraph/commit/491dafaacdc52efe609026eaa8d1e6612da94d4b). Scientific method/protocol at [dfcc088](https://github.com/metalogiclabs/mathgraph/commit/dfcc088ca6f4a280272c361e043dd0f49afa1b5b), resolver `7f38aa70`; their exact SHA-256 receipts passed in the original job.

**[GitHub Actions #39346764486](https://github.com/metalogiclabs/mathgraph/actions/runs/39346764486)** at `b8a0ed012995bb657dcbca626d5c308259ef60cd`: archived artifact #12231252251, independent archive SHA-256 `c9e1893accf55e46c35c555132aa72f4db6be2b63acc482b9e877932cf370da8`.

**Before source import/native tests:** exact source-bound scanner returned `UNKNOWN_NO_SAFE_LITERAL_SOURCE_EXAMPLE`; `obligations=[]`. Proposal JSON SHA-256 `91f39a06ceed5bc4f74e7a8d396915b1becef490a013c9dcd8df772695890691`. There is no obligation for the stdlib doctest reference to test, irrespective of later native fixture success.

**Native command first attempt:** `python -m pytest -q external-native --junitxml=verified/native-junit.xml` executed from the **MathGraph workspace root**, not the selected repository root. Exactly **1182 PASS / 1 FAIL**; the single failure is `TestMiscCases.test_project_script_entrypoint`, which reads relative `Path('pyproject.toml')` and received the unrelated MathGraph root metadata rather than Mistune's own. This is a **runner working-directory defect**, not demonstrated Mistune behavior error.

**Permitted apparatus recovery:** change ONLY original native pytest subprocess current working directory to the selected `external-native` checkout, preserve exact original package revision and test folder, native author tests, V6 frozen method, source selection, proposed JSON, evaluator and sources. Do not add/remove native tests or edit scientist parameters, fixture cases, comparer, or selected source. Reexecute same source with this cwd correction; report any remaining native or observer UNKNOWN independently. No outcome-based source substitution.

**All post-exposure classification:** selected Mistune is EXPOSED TRAINING now. V6 first prospective acquisition of source-doctest relation is already negative (0 admitted proposals). A later runner recovery does not change that prospective result.
