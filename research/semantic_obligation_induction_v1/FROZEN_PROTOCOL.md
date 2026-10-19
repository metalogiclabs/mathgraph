# Prospective API-to-semantic-correspondence obligation induction V1 — frozen before source exposure

Status: CANDIDATE, source-unopened at protocol freeze. Date: 2026-10-19 NZ.
This is a **new, isolated scientific lane**. Preserve prior PKC V7, L4YAML, and MarkupSafe evidence and leave the MathGraph V1 correspondence core at `9c8b427c679398fd80ea56d9a91a1627b2e96b6d` untouched.

## Scientific claim tested
Can a fixed, source-independent, finite public-API grammar propose independently checkable **semantic correspondence obligations** on a new repository, from only public API exports and GitHub repository metadata, before observing its implementation, return values, native tests or correspondence outcomes?

This is **not** autonomous invention of a new grammar or arbitrary human intent. A fully informed expert-authored name/format-rule cookbook acts as the comparator, not a recruited independent expert.

## Hard pre-exposure freeze and source selection
1. Freeze `propose.py`, `evaluate.py`, `preflight.py`, this protocol and source-independent fixtures at one exact Git commit. Synthetic preflight only is permitted before freeze. A CI checkout of that exact SHA must execute the candidate *and* comparator.
2. **Ordered pool, fixed now without reading source, tests or source outcomes:** `uiri/toml`, `hukkin/tomli-w`, `python-poetry/tomlkit`, `simplejson/simplejson`.
3. Using **repository metadata ONLY**, select the first candidate that is public, not archived, has `language = Python` and has a nonempty default branch. Check public GitHub HEAD commit SHA and pin it. Do not inspect candidate source before the freeze. Once selected, no skipping for failed tests, difficult syntax, unsupported API, or an unfavorable comparison. Stop at one selected source.
4. Prevent retrospective leakage: PKC, L4YAML and MarkupSafe are the earlier disclosed sources; none is eligible. Prior appearances elsewhere in ROS, if discovered, must be disclosed (not silently rebranded unseen).
5. No third-party writes, no patches to the held-out implementation, no internet-dependent oracle at execution, no secret or private account data.

## Identical information and execution budget
At **proposal** time, both arms receive (A) the exact public `PACKAGE/__init__.py` UTF-8 text including AST-import symbols and `__all__`, and (B) the same `repository`, public `description`, pinned `source_sha`. Neither may read test files, native outputs, implementation body of imported functions, or source outcomes. Both produce immutable `candidate.json` / `expert.json` **before** importing or running source.
- **Candidate:** `propose.py --arm candidate` finite two-stage rule: classify TOML/JSON from metadata; find exported writer among `dumps,serialize,encode`; generate external `independent_parse(writer(mapping))=mapping` obligation and optional `reader(writer(mapping))=mapping` if a matching public reader exists. Otherwise UNKNOWN.
- **Matched expert-rule cookbook:** same code `propose.py --arm expert` but independently preregistered conventional pair priority `dumps,encode,serialize` / `loads,decode,parse` and same independent oracle. It has all metadata, source API, declared examples and verifier access that the candidate receives. Neither arm gets hidden hindsight or source-specific hints. **This is NOT measured human expert performance**, and ties are credible evidence rather than defeats.
- **Evidence:** original author native test suite `pytest` on pinned source; standard Python 3.12 `tomllib.loads` (TOML) or `json.loads` (JSON), independent of held-out serializer; three fixed semantic-mapping fixtures in `evaluate.py` and deliberate wrong-expected-value negative control. No trial-specific input edits.
- **Independent verifier:** `evaluate.py` only evaluates the already written proposals and official native JUnit; preserves case observations and errors, SHA256 of both proposal files and native test results. External oracle success is **WARRANTED_BOUNDED_INDEPENDENT** only for exactly the three specified values and the pinned environment. Native roundtrip success has its separate weaker `WARRANTED_BOUNDED_NATIVE_CONSISTENCY` boundary.

## Decision and comparison
- Unsupported format, unrecognized exports, missing relation or missing native authority: UNKNOWN, not a loss swept aside.
- Native suite must execute at least one non-skipped original test without failures/errors to admit source-native claims.
- External parse equals the exact original typed mapping for all three fixtures AND wrong-expected-value controls reject: bounded positive witness. A reproduced unequal result is a bounded negative witness. Exceptions/unsupported seeds: UNKNOWN.
- Compare independent positive obligations, false promotions, native failures, semantic mismatches and abstentions **on the exact same source and inputs**. Report WIN, TIE, LOSS or INCONCLUSIVE; numerical score difference alone cannot show a human-expert advantage.
- A GREEN workflow is not by itself a claimed new semantic law. Archive native JUnit, candidate/expert proposals *produced before execution*, independent oracle observations, source SHA and run digest.
- A method change *after reading selected source* forfeits first prospective status. Preserve a RED/UNKNOWN as a legitimate negative result; a repair may launch only as separately re-frozen V2 on a different untouched future.

## Relationship to Research OS
ROS records a stronger independently native PKC V7 type-mutation result at [CI 39208993375](https://github.com/metalogiclabs/mathgraph/actions/runs/39208993375), so there is no warrant in rebuilding that result. The outstanding frontier remains **proposing a previously unsupplied semantic observation or operation type** and eventually transferring it twice with native verification and a true competent expert/agent baseline. This V1 tests a narrower but decisive first gate: pre-exposure *finite-grammar* obligation proposal vs equally informed conventional expert-authored rules.
