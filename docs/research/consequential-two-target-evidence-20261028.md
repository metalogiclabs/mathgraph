# Two-target protected-frame / Metatron lineage transfer — evidence checkpoint

Date: 2026-10-28 (Pacific/Auckland)

**Disposition:** `WARRANTED_BOUNDED_LOCAL_REPLAY` for the listed historical
source-pinned, synthetic-authority scenarios. The reusable *decision kernel*
predates this experiment (`0aab2b4d`); the increment here is a byte-pinned
source adapter, independently derived named observations on two targets, and
causal withdrawal in the actual pinned Metatron Nucleus. CI status is recorded
only after the remote workflow completes. **No real owner policy or merge,
publication, release or deployment authorization was granted.**

## Objective and durable precedence

Goal: test whether the already existing MathGraph protected obligation
mechanism transfers to a different historical native source while its
source/observation provenance remains explicit, and whether Metatron retains
the dependency graph needed for selective source revocation after cold restart.

Original source for this branch: MathGraph `2c9428785b902465bb5bd2524807e1fa4a336b81`
had two packet-relative GOETH V19 false-admission controls. Subsequently
qualified protected-frame research `8faaf2fa3dca1ed2656859e11b1322ee3f4cba18`
and native-mapping research `0aab2b4d65a2e4fb29744f7dd32c65ad681e3a9e`
**already repaired the synthetic GOETH protected-frame decision**, with
independent CI recorded in the canonical Research OS. This V2 experiment is
rebased on `0aab2b4d`, and must not be represented as the first repair.

## Exact evidence authority

| Component | Pinned evidence | Boundary |
| --- | --- | --- |
| MathGraph decision source | `metalogiclabs/mathgraph` protected-frame research at `0aab2b4d65a2e4fb29744f7dd32c65ad681e3a9e` | Existing `assessWarrant(snapshot, contract, asOf, protectedFrame)` remains unmodified; old negative controls retained |
| Metatron memory source | `metalogiclabs/metatron@b9d1b5cc10477188be6e55617699be60e70f6dad`; `runtime/metatron/nucleus.py` SHA-256 `13f840fa61ef28803a17a7a7266f80e19fdcbdde90703969dbd83f232f44300d` | Actual pinned Nucleus is byte-hashed before import; no changes to kernel |
| GOETH | `metalogiclabs/go-ethereum#19@a04aa77aaebd81d11274560e8d24d90c6f417589`; historical [run 38202260024](https://github.com/metalogiclabs/go-ethereum/actions/runs/38202260024), artifact `11725753900`, GitHub ZIP digest `2f141757925ec5d12932d7d60c8d1105be3dbcd932963470b64d9ff262fca943` | Historical fork predicate/Engine tests only; `remote_conflicting_fcu` and `concurrent_fcu` still untested |
| goccy/go-yaml | [PR #958](https://github.com/goccy/go-yaml/pull/958) at `a34b94ecb553bb5a693296c30232a89026db79ca`; report Git blob `1aa1a916df72fbcf6a62abea5c4160c257e205f3`; carrier manifest Git blob `78d8374b3882fa29e84bfacc41e464caf2d444b1` | 69 repairs, zero introduced regressions in declared 130-case matrix, 20 inherited issue #872 residuals. Human-orchestrated original Go work; native tests **not rerun here** |
| goccy native metadata | Historical [run 38559572638](https://github.com/heathsanchez/test/actions/runs/38559572638) artifact `11891727361` ZIP digest `f36a2f6fb0027ead5885354f18cdf019c7bd9bf590ac4e26ce3d810e6dcbc35a`; [run 38560167831](https://github.com/heathsanchez/test/actions/runs/38560167831) artifact `11891373353` ZIP digest `bc150693a314107764c59d7f395deb2c2ce4d4107f83324fdfe425d58b353d04`; [run 38560825707](https://github.com/heathsanchez/test/actions/runs/38560825707) | Live GitHub job/artifact metadata readbacks were SUCCESS / present at the respective pins. They are metadata readbacks, **not** a fresh ZIP rehash or Go execution in this experiment |

Canonical no-final-newline UTF-8 JSON source frames:

| Frame | SHA-256 |
| --- | --- |
| `fixtures/consequential-goeth-v19.v1.json` | `b6ee6aee99405607e924b8eba6a6b668522b0c40fdace4c7f0d9ecb3bf2e50cd` |
| `fixtures/consequential-goccy-pr958.v1.json` | `0f36816614d9b7464a437f60680b663e25783161f9831c2bff6067f912c1736c` |

The frame hashes are independently listed in the tests, replay pins and
Metatron bridge. A normal source-case replay rejects recalculated digests for
modified frames. Tests of *hypothetical* amended frames are labelled synthetic
and do not promote source authority.

## Observations and comparison

| Target / condition | Packet-relative baseline | Protected-frame V0 through byte-pinned adapter | Meaning |
| --- | --- | --- | --- |
| GOETH: valid synthetic signature falsely claims all required FCU tests true | `ADMIT` | `ABSTAIN` | Native predicate observation is qualified; two FCU tests remain `INSUFFICIENT` |
| GOETH: signed packet omits required FCU obligations | Packet-only can `ADMIT` (retained original negative lineage) | `ABSTAIN` | Frozen required universe cannot be shortened by a signer |
| goccy: synthetic `publish_report` grant, exact archived matrix report and matching native receipt | `ADMIT` | `ADMIT` | **Research-only bounded report**; no normative permission to publish/merge in a real environment |
| goccy: archive/source receipt changed or withdrawn | `ADMIT` from unchanged signed packet | `ABSTAIN` | Historical report support is now absent |
| goccy: separately *synthetic* requirement that the inherited 20 issue-872 cases were fixed by PR #958 | Packet assertion could claim true | `REFUSE` under declared negative observation | Do not confuse inherited failures with PR-introduced regressions |
| GOETH or goccy: cross-target native subject, altered source head or forged observation source | N/A | `ABSTAIN` | A qualified envelope is not permission to relabel its subject or observation |
| Frozen frame expects true but independently named native observation says false | Signed assertion of true | `ABSTAIN` with `CONFLICTING` observation | Neither an unsupported positive nor an invented definitive negative may be issued |

The independently coded conventional fixed-frame evaluator, given the **same
complete frame, native observations and synthetic grant**, ties on the tested
GOETH/goccy/withdrawal cases. The packet-only comparator is a retained
counterexample to an incomplete model, *not* a serious frontier baseline.
There is **no demonstrated decision-quality or cost superiority** over an
equally informed conventional controller.

## Actual Metatron lineage test

The bridge verifies exact Git commit **and** source-file SHA-256 before
importing the unmodified Metatron `nucleus.py`, then logs for each target:
`source -> historical receipt -> derived research assessment`. It retains
six live labelled records initially. Revoking the GOETH **source** cuts all
three GOETH descendants while retaining three unrelated goccy records.
Revoking only the goccy **receipt** then cuts that receipt and its decision,
leaving the goccy source. JSONL `dumps/loads` and a second independent Python
process reconstruct the same live state from eight append-only events.
An additional integration test passes the **actual computed decisions** from
the original GOETH/goccy native-adapter test harness into the pinned Python
Nucleus bridge, rather than only logging predeclared decision fixtures.

This tests causal *memory*, not the truth of the incoming two decisions. It
does not connect the native receipt to any external grant, protected effect
API or production service. The bridge rejects invented `UNIVERSAL_PROOF` and
production-decision labels before logging.

## Reproduction and local verification (28 Oct 2026)

`METATRON_SOURCE_CHECKOUT` must point to a separate checkout at the commit
and source digest listed above. For CI, `METATRON_REQUIRED=1` makes a missing
checkout a **test failure** rather than a skipped optional replay.

```sh
# From pinned Metatron checkout
python3 -m unittest discover -s tests -p test_nucleus_exhaustive.py -v

# From MathGraph v2 research checkout
node --test integrations/mathgraph-check-github/consequential-frame.test.mjs integrations/mathgraph-check-github/consequential-two-target.test.mjs integrations/mathgraph-check-github/consequential-metatron-replay.test.mjs
node --test integrations/mathgraph-check-github/*.test.mjs integrations/mathgraph-check-github/cloudflare/*.test.mjs
```

- Metatron original exhaustive test: **1/1 PASS**, 28 October.
- New research controls, including actual pinned Nucleus cold replay:
  **24/24 PASS**.
- Complete MathGraph Check regression on protected-frame base plus this
  adapter: **116/116 PASS** under permitted native test subprocess and
  loopback operations; no failures or skips in the final local run.
- `git diff --check`: **PASS**. No changes to `warrant.mjs`, production
  Worker, original GOETH source adapters, signed contract verifier, native
  goccy adapter or trusted Metatron kernel.
- Dedicated read-only CI workflow:
  `.github/workflows/mathgraph-consequential-two-target-v2.yml` checks out
  both repositories at explicit refs, runs native Metatron exhaustive controls,
  and forces cold-replay tests to fail if that checkout is absent.

### Negative lineage retained and repaired in this increment

The previous research branch's two misleading signed packets remain explicit
negative controls. Independent review of the first iteration also caught
two *harness* weaknesses: (a) it had constructed a native subject from the
frame under test, and (b) normal replay had accepted freshly recalculated
frame hashes. Both were corrected with separately pinned native source
constants and immutable case digests. A new TDD regression first failed when
an intact native receipt envelope with **no named observation** still
appeared to qualify the predicate. That red case now passes because the
adapter requires an actual source-labelled observation before constructing
the existing protected frame. The frozen research frame remains a reviewed
assumption, not an authenticated production policy registry.

## Epistemic state and next decisive residual

- **REUSABLE / already warranted in its own boundary:** the existing V0
  protected-frame obligation reconciliation, not invented by this change.
- **WARRANTED_BOUNDED_LOCAL_REPLAY:** the exact finite two-source synthetic
  results, source/observation mismatch rejection and cold Metatron lineage
  replay under the listed pins and test harness.
- **CANDIDATE:** operational cross-target provenance adapter and causal
  research memory, pending separate policy, source-monitor and blind tests.
- **UNKNOWN:** real owner requirement registry, frame-producer credentials,
  production effect mediation, current FCU race outcomes, a fresh blind third
  domain, L7 autonomous norm invention, and superiority/effort economics.
- **REJECTED:** that a valid signed packet alone establishes protected
  obligation completeness or native observation truth.

**Cheapest decisive next experiment:** obtain an independently authenticated
real owner requirement/policy source **read-only**; separately source new native
observations for GOETH's two FCU residuals; pre-register an unfamiliar third
source/owner decision with an external oracle and strong equally informed
conventional baseline. Run positive, omission, conflicting, withdrawn and
expired cases, score false admission, false refusal, valid permits, time to
separating observation and all-in cost. Until then, the outer permission
ceiling stays `NO_EXTERNAL_ACTION_AUTHORITY`.
