# MathGraph modular contracts — local release-candidate evidence

Observed 11 October 2026 in the isolated worktree on
`codex/mathgraph-contracts-and-modules-v1`. This is a local qualification record,
not a production-release or remote-CI receipt. P0 Resolve publication remains
complete at `11944c2b44ac890ecc03c7f183ae74ea4640246c`.

## Source identity and release status

The qualified executable source is
`fbd3994642735f7599ec66bc89c2b9394a7b6b53`, Git tree
`5eb51b98b76a75e2395dfce319799f54d4781d67`. It includes the Task 7 projection,
the two empty package markers required for combined pytest collection, and the
three independently reviewed release fixes described below. This report and the
audit update are subsequent evidence-only changes; their commit is recorded by
Git history and does not modify the qualified executable artifacts.

| Component | Implementation commit(s) |
| --- | --- |
| Resolve contracts | `a642325dafc3222256bfeea14c2f28749f17e945`, fix `f1746ec8cdd6b7fdc7a9f00808dad2c20d9a3646` |
| Independent package/ranking | `d86488e75b133afd4a2ad238e98cdd6f2c24e078` |
| Advisory Discover | `eabba18a566a341ccf41f2a51aa3aab511536c6d`, fix `561775559d54c9cf9c4a579d1447c1ffe2399424` |
| Capability contracts | `ecdb6f1fdd1b801d3c5e778c879be56a047c3f92`, fix `898f26a87af6ffa0ec00ea4f34acf336f3548785` |
| Independent finite qualification | `6c7c443ddf9cc64665d3fbfd731e034736fb89c3` |
| Unsigned in-toto binding | `02a817e8de64c65e4d88d43a6279ee9f16d4364d` |
| Astro projection | `b7bbdc8a3e0d30fb752882f0ed83048c2543bec1` |
| Combined-test collection fix | `0037dbe515c43481ba02426e56bc7eaefc296285` |
| Structured parser-limit rejection | `d335223d368b146ac220e60198eaa0ae6d88e7cf` |
| Complete modular CI coverage | `ae65f940486a372489aa097aa76d2a5cd056fd1c` |
| Resolve schema discovery | `fbd3994642735f7599ec66bc89c2b9394a7b6b53` |

No branch push, PR, remote preview, production promotion, alias, DNS change, or
hosted deployment was performed. Task-scoped review, whole-branch review, and
scoped re-review of all findings completed. Linux Docker
isolation and candidate-specific remote website CI are **PENDING**. Historical
P0 CI links in the audit are not evidence that this candidate passed remote CI.

## Fresh commands and results

Commands run from the repository root unless marked otherwise. Python was
**3.11.14**, Homebrew runtime **3.11.14_3**. All successful results below were
observed during Task 8 or rerun on the final reviewed executable head; they are
not inferred from earlier implementation reports.

```sh
python -m pytest conformance/protocol_v1 conformance/resolve_v1 conformance/discover_v1 conformance/capability_v1 conformance/interoperability_v1 tests/test_mathgraph_protocol_import.py tests/test_discovery_scheduler.py tests/test_discovery_candidate_sources.py -q
python -m pytest tests/test_mathgraph_resolve_publication_v1.py tests/test_mathgraph_protocol_import.py -q
python -m pytest tests/test_discovery_scheduler.py tests/test_discovery_candidate_sources.py -q
python -m pytest conformance/resolve_v1 -q
python -m pytest conformance/capability_v1 -q
```

| Gate, in command order | Observed final result |
| --- | --- |
| Expanded final-head conformance and compatibility | Exit 0; **311 passed, 72 subtests passed** |
| Historical publication and package import | Exit 0; **24 passed** |
| Existing discovery scheduler/source compatibility | Exit 0; **14 passed** |
| Standalone Resolve after package-marker fix | Exit 0; **15 passed, 52 subtests passed** |
| Standalone capability after package-marker fix | Exit 0; **147 passed** |

The initial combined command exited 2 during collection: both Resolve and
capability supplied an unqualified top-level `test_consumer` module. Empty
`conformance/resolve_v1/__init__.py` and
`conformance/capability_v1/__init__.py` give them distinct package names. The
exact combined command, both standalone suites, and historical/import tests
passed afterward. No tests, consumers, or fixtures were rewritten to obtain this
result. The full unrelated monorepo suite was not run; its pre-existing external
fixture/SorryDB residual remains in the audit's Section 2.4.

A final repeat inside the outer execution sandbox reached **280 passed and 60
subtests**, but one enforced-isolation test failed with
`sandbox-exec: sandbox_apply: Operation not permitted`. The complete combined
command and historical/import gate were then rerun with host permission to
create the narrower sandbox; the final successful counts above apply to that
run. This environment prerequisite is not skipped or converted into a passing
test, and does not require weakening network denial.

### Independent offline and original finite replays

```sh
python conformance/resolve_v1/run_isolated.py --backend macos --policy-sha256 09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a
python conformance/capability_v1/run_isolated.py --backend macos --policy-sha256 7069c764579d933679f6bfd9b922a724ad9bcb250e4060c660cb4fd099c60e89
python experiments/developmental_capability_growth_v1/run_all.py
```

Both isolation commands exited 0 using host permission to create their narrower
macOS sandboxes. Each denied IPv4 and IPv6 access (`errno [1,1]`), denied
repository access, audited only standard-library imports, and compared two
identical replay outputs. Resolve's readable application inputs were only its
consumer, bundle, and policy; capability's were only its consumer, finite vectors,
contract, and policy. System/runtime libraries were separately permitted.
The successful macOS run does **not** qualify the Linux Docker backend.

Resolve replay SHA-256:
`8c7b30e1eb2a24d2960e170d36652ca95aa71b41075f673abe394e154ae66668`.
The seven results remain three documentary supports `STALE`, three mathematical
propositions `UNKNOWN`, and the exact 48-case JPL observation
`WARRANTED_BOUNDED`. The original JPL Lean proof was not rerun.

Finite replay SHA-256:
`5d85d7117532fd777d7b2948ab1138bec47db81176327fdb9591e0be7fe2a006`.
It recomputed old masks `[0,105,150,255]`, four obstruction pairs, unique
named-family repair `bit0`, refined closure size 16, discovery mask 144, reuse
mask 246, sham failure, ablation, complete old-policy retention, 256 Boolean
refinements, 32 successes, 224 failures, eight successful partition classes, and
four three-cell / 28 four-cell successes. All nine receipt checks were true.

The original read-only `run_all.py` invoked `run.py` and
`audit_all_boolean_refinements.py`. Both full outputs were read. It exited 0 with
`PASS_BOUNDED_DEVELOPMENTAL_EVENT` (eight gates true) and
`PASS_GLOBAL_REFINEMENT_CLASS_AUDIT` (four gates true), with matching finite
counts. Original source bytes stayed unchanged. These original verdicts are a
separate observation; they are not inputs to the independent consumer's admission.

### Complete website qualification

The specified Node/npm versions were already cached, so no acquisition was
needed. This is the executed equivalent of the plan's `npx node@24.15.0` command:

```sh
cd website
PATH=/Users/heath/.npm/_npx/fb837012b869f4d0/node_modules/node/bin:$PATH \
  /Users/heath/.npm/_npx/fb837012b869f4d0/node_modules/node/bin/node \
  /Users/heath/.npm/_npx/fb837012b869f4d0/node_modules/npm/bin/npm-cli.js run qualify
```

Verified versions: Node **24.15.0**, npm **12.2.0**. The first outer-sandbox run
passed through HTML validation but stopped at linkinator's local server with
`listen EPERM: operation not permitted 127.0.0.1`. The entire command was rerun
with loopback-server permission and exited **0**:

- Social-card identity: 51,254 bytes, SHA-256
  `7269e84d1a81dbe671867bfc3f6effdde233c5ddffabfad35e665d1a9508844c`.
- Astro: 49 files, **0 errors, 0 warnings, 0 hints**.
- Data **68/68**, contract **16/16**, rendering **37/37**: **121 checks**.
- Build: **16 Astro pages**; built integrity: **17 HTML pages**, **32,206 client
  bytes**, catalogue V2, two records, 1200×630 social card.
- Resolver documentation contract and HTML validation passed; **58 links** passed.
- Independent static consumer passed, including eight negative `UNKNOWN` cases.
  Independent Resolve HTTP consumer passed all seven claims with external pins,
  recomputed closure, and current applicability `UNKNOWN`.

The link checker intentionally skips GitHub and production-origin URLs, as
declared in `website/linkinator.config.json`. These 58 checks are not external
link availability evidence. Source links target committed module revision
`02a817e8…`; their public availability requires the later branch push.

## Immutable identities and byte parity

`shasum -a 256` was run over the exact files below. Replay output identities came
from the successful isolation harnesses. Each immutable Resolve value matches
the published audit baseline.

| Object | SHA-256 |
| --- | --- |
| Resolve bundle | `957080db79555f982fd3a314c263cf5177ef506969229e856897f0b19ccc1d62` |
| Resolve policy | `09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a` |
| Resolve Python consumer | `27a9be606040cc94a47c9b903dfc1cb24a86cbbc4e05ce71040c6c3d6e8d527b` |
| Record 002 transport/source and website data | `0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87` |
| Record 002 payload self-hash, checked by publication tests | `b95297a081d513fb0ec145a776cc997eaed18109d6b2af39fa8e61f6d637af41` |
| Resolve scenarios | `ed458ccbee85e3aa3f49d9d38e7ad5380515d00d707bac09c584cc4955b88181` |
| Resolve TypeScript consumer | `e7360df24b2fd0900c8ea88ccb1689163cec73a6c2e2347e4ab2b23b4d01bc2e` |
| Finite independent consumer | `d70a1a13d15ca6d7331c84e49d81c3f96e484f919f351b88dc66d7c9fc26870f` |
| Finite trust policy | `7069c764579d933679f6bfd9b922a724ad9bcb250e4060c660cb4fd099c60e89` |
| Finite capability contract | `24e639b9181af313100504e0aa525536197d868810e6ffdb5093fd13501577a8` |
| Finite vectors | `62d74bd64163edd83c82414b344c7fd3c16e4983bbf480c165cf9e8218a86c60` |
| Finite receipt | `2f07b700dfd2b75236ee399f77f4f288953b045af0eae55f4099a558278cb009` |
| Finite evaluation | `c1cf195917694f4402e6b3e41a174985d52fb57c5f0de99bd96a28ebf91d4312` |
| Registry and public registry mirror | `7ae45ef09ce492856234872c12adc6999667b14899a008baddc19687934b1358` |
| Discover request | `23d6d59eef4fd6ba7bdddd673d01b8f2e61e71412b1d7bc66d3fce68b728c25a` |
| Discover result | `6d9a24c7ffebe2288561e976a774f9d184f47b21e40572046e003b917cc939a5` |
| Unsigned in-toto statement | `01cf99a1a37a370e453c5978914625c63602938420591c1dd2cfeef1ad86b5e6` |
| Discovery V3 manifest | `3bde9969e635a39153f58b7f237979b954302c48878c2266dffe2ab9afd16540` |
| Original finite `run.py` | `4a76cae749b75e1461948854bf91fbcff5c5385591ec1f21967d44ba9738d588` |
| Original all-refinement audit | `e4354d8c5ad2c07c5494907f0909f522f33a9c861f8f79586da395bc7535a0f3` |

All eight normative schema/public pairs passed `cmp`:

```sh
for schema_file in protocol/schemas/*.json; do
  cmp "$schema_file" "website/public/schemas/${schema_file##*/}" || exit 1
done
cmp protocol/registries/capabilities-v1.json website/public/capabilities/index-v1.json
```

| Schema under `protocol/schemas/` | SHA-256 |
| --- | --- |
| `resolve-bundle-v1.schema.json` | `cec1df4fbb5d1a093abc575211f4ec2804b7f55f50aad1b44f710e21b75ae679` |
| `resolve-trust-policy-v1.schema.json` | `998110b89771d068b1352cb53ecc22478321698fcb5f5b8b715550efc03b8986` |
| `discover-request-v1.schema.json` | `a6acebf28c22900f7d0037f3ed0f5edabc27b792ed2d1dde470cae76212b0dfb` |
| `discover-result-v1.schema.json` | `9939a86c551df816a258f7a542a87ee18bdfbbf907208d6f21613713a4cc00a2` |
| `capability-contract-v1.schema.json` | `647dc9c12a100fbec335cf55de9e2353e9878e5e1fb770d0f4551e63f2b71fbb` |
| `capability-evaluation-v1.schema.json` | `df3db4e8ba7d1d34d45594e72fdeb1e525982e3a2b792043faf2bdf12038d779` |
| `capability-registry-v1.schema.json` | `bbc463159f6e3f50da01f3ef03ba7a305026634fe9f785e5b2d0bb3f3809be30` |
| `external-binding-v1.schema.json` | `4d56677ff14162aaf11f7394bd8552ada9dbde70d75c68a2e910414596f8404a` |

Each of the ten paths in `website/src/lib/modules.ts::moduleArtifactPaths`
passed `cmp "$artifact_file" "website/dist/artifacts/$artifact_file"`: the
Discover request/result, finite contract/vectors/profile schema/evaluation/
receipt/policy/consumer, and unsigned in-toto statement. Resolve consumer,
bundle, policy, record, and scenarios also passed canonical/public `cmp`.

These exact read-only Git checks exited 0:

```sh
git diff --exit-code 11944c2b44ac890ecc03c7f183ae74ea4640246c -- evidence website/public/evidence website/src/data website/public/examples website/public/schemas/discovery-v1.schema.json website/public/schemas/discovery-v2.schema.json experiments/developmental_capability_growth_v1 vercel.json website/vercel.json website/astro.config.mjs website/package-lock.json
git diff --exit-code 11944c2b44ac890ecc03c7f183ae74ea4640246c -- conformance/resolve_v1 ':!conformance/resolve_v1/__init__.py'
git diff --check
```

Thus existing tracked record 001/002 evidence, data, independent clients, original
finite experiment sources, lockfile, and those deployment/configuration paths
have no diff. The only change under historical Resolve conformance is the empty
test package marker. Hashes establish identity; they do not authenticate a
publisher or create mathematical qualification.

## Routes and visual evidence

New static routes: `/discover/`, `/develop/`, `/capabilities/`. Updated entry
points: `/`, `/protocol/`, `/developers/`, `/agents/`, `/llms.txt`,
`/.well-known/mathgraph.json`, and `/sitemap.xml`. The eight new stable schema
downloads are under `/schemas/`; registry is `/capabilities/index-v1.json`;
ten exact build-time downloads are under `/artifacts/`. There is no runtime
execution form, arbitrary fetch endpoint, hosted Discover/Develop service, or
mandatory orchestration loop.

A fresh headless Chrome **155.0.8059.39** profile inspected the completed static
build at `http://127.0.0.1:4324` using the package's
`npm run preview -- --host 127.0.0.1 --port 4324`. The browser checker is
`/private/tmp/mathgraph-task8-browser.ooQo9Y/inspect.mjs`; its full 21-case report
and additional evidence-section images are in that temporary directory. It was
run with the cached Node executable and a separate Chrome profile/debug port
9335. Temporary browser data is not release evidence in Git.

Seven routes (the three new pages, home, protocol, developers, agents) passed at
**1440×1000, 768×1000, and 390×1000**: **21 combinations**, zero document
overflow even with disclosures expanded, one main/h1 each, named controls, no
positive tabindex, visible first-tab skip-link focus, keyboard-operated Discover
disclosure, and no browser warning/error/exception events. These checks do not
claim exhaustive accessibility or cross-browser certification. The existing
mobile header uses intentional horizontal navigation scrolling.

All nine top-of-page images below and all nine corresponding evidence-section
images were visually inspected. Typography, buttons, status labels, finite
limitations, advisory boundaries, and wrapped identifiers remained readable.
Nine representative images, about **824 KiB** on disk, are retained under the
existing small QA screenshot convention:

| Route | Desktop | Tablet | Mobile |
| --- | --- | --- | --- |
| Discover | [1440](../website/qa/screenshots/discover-desktop-1440.png) | [768](../website/qa/screenshots/discover-tablet-768.png) | [390](../website/qa/screenshots/discover-mobile-390.png) |
| Develop | [1440](../website/qa/screenshots/develop-desktop-1440.png) | [768](../website/qa/screenshots/develop-tablet-768.png) | [390](../website/qa/screenshots/develop-mobile-390.png) |
| Capabilities | [1440](../website/qa/screenshots/capabilities-desktop-1440.png) | [768](../website/qa/screenshots/capabilities-tablet-768.png) | [390](../website/qa/screenshots/capabilities-mobile-390.png) |

## Implemented boundary and unresolved obligations

| Surface | Observed supported result | Still experimental, unknown, or absent |
| --- | --- | --- |
| Resolve | Explicit v1 transport/policy, independent structural validation, preserved historical replay | Present applicability `UNKNOWN`; freshness/revocation `NOT_CHECKED`; no original Lean rerun |
| Discover | Pure local advisory ranking; strict malformed-input controls; nine present source artifacts checked; deterministic committed result | `PARTIAL`, `NOT_CHECKED`, no accepted terminal claim; missing candidate-score CSV/full-replay SQLite ledger; no historical experiment authentication or rerun |
| Capability description | Portable exact descriptor, separate evaluation axes, critical-extension fail-closed behavior | A descriptor alone remains `UNKNOWN`; no self-qualification |
| Finite Develop | One exact `QUALIFIED_BOUNDED` registry entry after independent finite replay | Same-owner implementation independence only; two distinct target functions within one owned source, not independent organizations; no universal invention/autonomous improvement claim |
| VDN / compiler | Separate experimental VDN candidate | No pinned native Lean admission; Capability Family Compiler `NOT_IMPLEMENTED` |
| Interoperability | Unsigned in-toto subject/schema/scope/evidence correspondence | No authentication, signing, transparency, Sigstore/SCITT/RATS implementation, freshness, or authority |
| Website | Qualified local static projection and schema/artifact parity | No remote preview or production promotion; source-link availability awaits publication; V3 adoption is explicit for consumers pinned to V2 |

All capability temporal axes stay separate: current applicability `UNKNOWN`,
freshness/revocation/supersession `NOT_CHECKED`, action authorization `NONE`.
The three mathematical terminal forms remain unchanged. No outside-organization
adoption is claimed.

## Plan acceptance and next release action

The implementation plan was read line by line. The following maps its final
requirements to observed evidence; historic RED runs and earlier task reviews
remain in the controller's task reports and were not recreated here.

| Plan requirement | Task 8 disposition |
| --- | --- |
| Task 1: preserve bytes, strict schemas, independent structural consumer and historical gates | Combined/standalone/publication tests and immutable/parity checks passed |
| Task 2: dependency-free package and shared ranking parity | Import tests plus 14 legacy scheduler/source tests passed |
| Task 3: strict advisory/source contract, deterministic offline example | Discover conformance passed, including isolated dependency/audit-hook checks; exact request/result download parity passed |
| Task 4: descriptor/evaluation separation and registry contract | Capability conformance passed; general descriptor cannot self-admit; empty registry remains a supported shape |
| Task 5: independent finite replay before bounded admission | Fresh four-input macOS isolation passed, matched exact receipt counts; registry has one bounded entry; Linux backend pending |
| Task 6: unsigned external mapping and negative controls | Interoperability conformance passed; no authentication/admission implied |
| Task 7: routes, machine parity, desktop/tablet/mobile behavior | Full qualify and 21 browser combinations passed; nine retained images visually verified |
| Task 8 Step 1: all specified isolated gates, original scripts, immutable hashes | Completed; collection issue corrected and exact command rerun; full outputs inspected |
| Task 8 files: observed audit update and release report, permitted screenshot artifacts | Audit baseline retained with explicit addendum; this report and nine small QA images added |
| Task 8 Step 2: independent release review | Task review approved; whole-branch review found three interface gaps; all three fixes passed scoped re-review with no remaining finding |
| Task 8 Step 3: push/draft PR/CI/preview | Push and draft PR remain pending; no production or remote action occurred during local qualification |
| No P0 regeneration or production/config mutation | Immutable Git comparisons and exact pins passed; no deployment action taken |

The smallest next action is to publish this branch and open the requested draft
PR, collect fresh Linux Docker and website CI results, inspect an automatically
created preview if available, and attach the exact final commit and evidence links.
Production promotion remains a separate action. No release should cite this
document as evidence that those pending gates have already passed.
