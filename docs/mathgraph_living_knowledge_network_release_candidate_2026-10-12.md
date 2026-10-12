# MathGraph living knowledge network — release-candidate checkpoint

Status: **UNRELEASED_CANDIDATE**. Observed 12 October 2026 UTC / 13 October
2026 NZDT on branch `codex/living-knowledge-network`. This file travels with
the release-gate commit; its exact Git identity is recorded by Git and the
corresponding CI run rather than embedded recursively in its own bytes. A final
GitHub CI run, draft pull request and protected Vercel preview are **PENDING**.
Production has not been changed by this work and remained associated with
`main` commit `50b74559551d4935d7b5237ff5e98438f09d5d26` at the observed release
boundary.

## What this increment makes real

The existing Astro product now exposes a deterministic, source-pinned
mathematical catalogue alongside the already published Check, Resolve,
Discover and Develop contracts:

- `/explore/` searches real source occurrences, existing evidence objects and
  qualified capabilities without combining their authority.
- `/objects/{id}/` provides permanent declaration-occurrence pages with exact
  source range, statement digest, status axes, typed structural relationships,
  bounded neighbourhood and offline validation instructions.
- The homepage retains **“Knowledge you can verify. Capabilities you can build
  on.”**, derives five separate network measurements from committed data and
  points to real Explore, Verify and Build journeys.
- Resolve keeps record 002's published-after state, modeled-before comparison
  and explicit counterfactual withdrawal separate from immutable evidence.
- `/agents/`, `/developers/`, `/.well-known/mathgraph.json` and `/llms.txt`
  expose the versioned, read-only, fail-closed catalogue contract. Action
  authorization remains `NONE`.

No source-indexed declaration enters the MathGraph accepted-claim kernel. An
accepted mathematical claim still requires exactly one of `VERIFIED_PROOF`,
`FINITE_COUNTERMODEL` or `NAMED_OBSTRUCTION`.

## Exact source catalogue

| Field | Pinned value |
| --- | --- |
| Source | `leanprover-community/mathlib4` tag `v4.34.1` |
| Commit | `d13f23b723b8a846827a245b89c10fc7d3f11612` |
| Git tree | `efa132418a56d0e38c56cc412a06df22178dac5c` |
| Lean toolchain | `leanprover/lean4:v4.34.1` |
| Catalogue | `mathlib-v4.34.1-foundations-v1` |
| Manifest SHA-256 | `5974ac4d68b1e090d511964cd61237565b80d39b5e47e9966171d4d8bcd2fe68` |
| Coverage | 13 selected modules; 2,345 declaration occurrences; 3,571 structural relations |
| Named omissions | 1,201 declarations; 93 imports; 19,141 type references |

The deterministic catalogue relation breakdown is 2,345 `DECLARES`, 1,224
`TYPE_REFERENCES` and 2 `IMPORTS_MODULE`. These relations describe containment,
direct expression constants and direct module imports. They are not logical
implication, semantic equivalence, proof dependency or evidence.

Every catalogue object and relation carries the same non-escalating boundary:

| Axis | Result |
| --- | --- |
| Source status | `SOURCE_INDEXED` |
| Independent verification | `NOT_CHECKED` |
| Current applicability | `NOT_CHECKED` |
| Freshness | `PINNED_HISTORICAL_SOURCE` |
| Authority | `NONE` |
| Action authorization | `NONE` |

The implementation-independent standard-library consumer validates canonical
bytes, exact pins, identities, closed relation endpoints, relation meanings,
counts, omissions and budgets without importing the producer or calling
MathGraph.org. It does not fetch Mathlib, rerun Lean, establish current GitHub
state, prove catalogue declarations or authorize action:

```sh
python3 -I -S -B conformance/source_catalogue_v1/consumer.py \
  --catalogue-root website/public/catalogues/mathlib/v4.34.1 \
  --policy conformance/source_catalogue_v1/trust-policy.json \
  --policy-sha256 c3cdec2b2c784728621bb8c25a055a1e73d67d3c1c922b7ab62b09003399e1c9 \
  --audit-imports
```

A digest retrieved from the same origin detects corruption, not a compromised
origin. The consumer must receive its trust-policy and manifest pins through an
independently chosen channel. Repository authentication under such a policy is
still not mathematical truth.

## Source-derived network measurements

The website derives, validates and displays these categories separately:

| Category | Count | Meaning |
| --- | ---: | --- |
| Indexed mathematical objects | 2,345 | Mathlib declaration occurrences only; `SOURCE_INDEXED`, not verified claims |
| Independently qualified results | 1 | Unique qualified Check result; Resolve reuse does not double-count it |
| Typed relations | 3,578 | 3,571 source-catalogue relations plus 7 qualified-evidence relations |
| External source projects | 4 | Mathlib, L4YAML, OpenAI mathematics and YAML test-suite identities |
| Qualified reusable capabilities | 1 | Exact finite registry entry only |

There is deliberately no combined “knowledge”, adoption or verification total.
Source declarations, Resolve states, advisory candidates and capabilities do
not inflate the qualified-result count.

## Preserved authority and history

Records 001 and 002, their immutable JSON, schemas, receipt identities, trust
policies and historical URLs are reused without reinterpretation. The living
network adds bounded presentation and source projections; it does not rewrite
historical evidence. Record 001 remains the exact 48-case JPL/YAML observation
with its declared UNKNOWNs. Record 002 continues to distinguish stale
documentary support from theorem refutation and leaves the three propositions
`UNKNOWN`; the unrelated JPL observation remains `WARRANTED_BOUNDED` at its
exact scope.

The qualified finite capability remains one exact eight-state profile. The
Capability Family Compiler, broad Lean qualification, hosted resolver, MCP,
arbitrary URL ingestion, natural-language verification, continuous
requalification and action execution remain unavailable or unimplemented.

## Local qualification observed

Against one rebuilt local static artifact from the current source, the branch
recorded:

- 107 data tests, 21 contract tests and 68 rendering tests passing;
- a clean Astro build producing 2,394 pages and 2,395 HTML files;
- successful static-artifact, independent catalogue-consumer, Source Check and
  Resolve HTTP-consumer checks;
- the complete browser suite passing across desktop, tablet, mobile, JavaScript
  and no-JavaScript paths, including import, navigation, catalogue, source
  objects, evidence map, Resolve and accessibility;
- 48/48 accessibility route/viewport scans with zero axe violations and zero
  incomplete results after decorative text/gradients were removed, mobile
  Resolve content reflowed, and keyboard-scrollable code blocks received
  `tabindex="0"`; the generated `aria-hidden` SVG diagrams are excluded from
  Axe because their exact content is independently tested in adjacent semantic
  HTML lists;
- a deterministic 50-result JavaScript window over all 2,372 searchable
  semantic entries, with all 2,372 still present in the static/no-JavaScript
  publication and keyboard “Show more” expansion;
- settled search p95 of 30.8 ms normally and 29.1 ms under 4× CPU slowdown;
  4× navigation-to-ready 1,285.0 ms, first use 26.9 ms and clear/reset 22.8
  ms; and
- the largest exercised bounded graph route becoming interactive in 277.6 ms
  under 4× CPU slowdown, with 7.2 ms selection and 0.8 ms traversal p95.

The exact release-focused Python qualification recorded **654 passed tests and
72 passed subtests**. A broader repository diagnostic recorded **2,187 passed,
1 skipped, 13 failed and 19 setup errors**. Those 32 residuals are not website
regressions: 19 require the externally acquired exact OpenAI/V1/V2 evidence
fixtures, while 13 require inherited SorryDB summaries/source cache, sufficient
disk for one planner path, or the breakthrough-demo dependency. The dedicated
CI evidence-integrity job acquires the exact archives before running its
bounded tests. The failing broad diagnostic is retained as a limitation and is
not represented as a green whole-repository gate.

The focused result was produced with the exact Lean 4.34.1 executable supplied
through `MATHGRAPH_CATALOGUE_LEAN` and this test selection:

```sh
MATHGRAPH_CATALOGUE_LEAN=/absolute/path/to/lean-4.34.1/bin/lean \
python3.11 -m pytest \
  conformance/source_catalogue_v1 \
  conformance/import_v1 \
  conformance/protocol_v1 \
  conformance/resolve_v1 \
  conformance/discover_v1 \
  conformance/capability_v1 \
  conformance/interoperability_v1 \
  tests/test_source_catalogue_contract_v1.py \
  tests/test_mathlib_source_catalogue_publisher_v1.py \
  tests/test_mathlib_source_catalogue_extractor_v1.py \
  tests/test_mathgraph_protocol_import.py \
  tests/test_discovery_scheduler.py \
  tests/test_discovery_candidate_sources.py \
  tests/test_core_invariants.py \
  tests/test_finite_failure_not_true.py \
  tests/test_no_advisory_truth_promotion.py -q
```

The full browser and static measurements are recorded in
[the browser qualification checkpoint](mathgraph_living_knowledge_network_browser_qualification_2026-10-12.md).
These are local Chrome 155.0.8059.39 observations, not yet exact-final-commit
GitHub CI or protected-preview evidence.

## Release boundary and next action

| Item | State |
| --- | --- |
| Implementation | Present on the isolated branch |
| Pinned source catalogue and offline consumer | Implemented; previously qualified and replayable |
| Current-worktree local regression and independent review | Passed within the boundaries above; final committed-head replay pending |
| GitHub exact-head CI | `PENDING` |
| Draft pull request | `PENDING` |
| Protected preview and preview browser review | `PENDING` |
| Production merge/promotion | `NOT_PERFORMED` |
| DNS, registrar, mail and trust-policy changes | `NOT_PERFORMED` |

The smallest qualifying next action is to run every deterministic, browser,
performance, immutable-evidence and independent-consumer gate on one clean final
commit, obtain fresh review, then publish that exact commit as a draft pull
request and protected review-only preview. Production promotion remains a
separate human-authorized action.
