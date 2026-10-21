# V4 closed-boundary real-test skip — preregistered before code change

Research only. Existing main source conformance/resolve_v1/consumer.py; change only sha(raw) from hashlib.sha256(raw).hexdigest() to hashlib.sha256(raw).digest().hex(), identical for all hashlib-accepted bytes-like inputs. Keep all original conformance tests unchanged.
Frozen protected two-suite universe:
A conformance/resolve_v1/test_consumer.py (source-owning consumer tests): MUST KEEP.
B tests/test_mathgraph_warrant_resolution_core.py (different isolated warrant resolver module): CANDIDATE SKIP only if independently certified disjoint.
The change is a real library source edit, not a fabricated test and not merged.

Certification gate B:
- Exact pinned unchanged B test file and its dependency mathgraph_check/warrant_resolution.py, plus imports restricted to pytest, dataclasses and that unchanged production module. No test-level runtime importlib/subprocess/eval/exec/open/filesystem, no opaque helper imports; any changed B source, opaque dynamic import or changed module dependency => KEEP. No claim of general Python source-independence outside frozen two-suite universe and pinned pytest runner/CI.
- A must contain existing direct dynamic load of the local conformance/resolve_v1/consumer.py; no authoritatively justified removal.
- Inject a synthetic dynamic import of changed consumer into B test source (in memory, never modify actual tests); gate must REVOKE SKIP.
- Alter fake source-diff beyond exact approved sha() rewrite; gate must REVOKE SKIP.
- Independent native qualification: run BOTH suites once on actual changed source (audit), compare source-prescribed SHA-256 digest on several bytes cases with old version and native hashlib. Run altered digest negative control and ensure deviation detected.

Fair baseline:
- Fully informed conventional module-level test selector using the same frozen source-to-suite map and known B non-dependence, not a naive strawman. Expected TIE on selected suite; independently execute 5 full-vs-selective pairs alternated on same runner. All check/setup and selector costs recorded. A measured speedup is only for this two-suite profile; NOT entire repo CI, not release cost.
- Protected decision is scoped TWO-SUITE_REVIEW: can omit B only while exact hashes, closed import authority and native negative controls remain qualified. Source, boundary, or mutation-control withdrawal removes permission.
- The broader five-suite evidence and full application release must remain UNKNOWN and cannot be silently replaced.
- R7.2, CLC and existing MathGraph warrant tracking unchanged.
Failure to achieve eligible authentic B skip is an accepted negative; do not tune profiles after outcome.
