# MathGraph Source-Bound Specification Assurance — TLA+ V1

**Status:** Bounded research experiment on an unmodified external source pin.

## Motivation

This experiment tests one sharply limited claim-fidelity implication:
**a green model checker cannot authorize an independently identified property
that the checked configuration did not include**.

The public example is Stephan Merz's `tlaplus/Examples` Lamport distributed
mutual-exclusion TLA+ model, including its published README and `Mutex` safety
property. It is not a Microsoft code-migration artifact.

## Exact sources

- Source: `tlaplus/Examples@53955cf52c9cbe417b2bde68ab72edf2b9096cfc`
  under `specifications/lamport_mutex`.
- Publisher configuration: `MCLamportMutex.cfg` (`N=3`, `MaxNat=7`,
  `maxClock=6`, `INVARIANTS TypeOK BoundedNetwork Mutex`, finite clock constraint).
- TLC executable: public `tlaplus/tlaplus` v1.8.0 release JAR, fixed SHA256
  `78f7e2c6bf9a8b65eda665a23e94431255587e0b43a834a4e2af1723562d9b4a`.
  The prerelease tag may move; any changed downloaded bytes must fail closed.
- Original source README/model/wrapper/config/manifest exact byte hashes are
  hardcoded and checked by the independent adjudicator.
- MathGraph source: `research/microsoft_spec_assurance_tla_v1` only, no edits
  in the upstream checkout.

## Native controls

| Lane | Precisely frozen difference | TLC expectation | Claim decision |
|---|---|---|---|
| `author` | Original author code and original model configuration, byte-for-byte | exhaustive finite model completes | `WARRANTED_BOUNDED_AUTHOR_MODEL` |
| `mutant_checked` | Local-only deletion of `beats(p,q)` priority guard inside `Enter(p)`; acknowledgement guard retained; `N=2`, `MaxNat=4`, `maxClock=3`; `Mutex` still selected | real finite `Mutex` violation, with `crit={1,2}` | `FINITE_COUNTERMODEL` for altered model |
| `mutant_weakened` | Exact same mutated model and finite bounds but `Mutex` omitted from `INVARIANTS`, `TypeOK` and `BoundedNetwork` still selected | model checker completes | `REJECTED_MISSING_MUTEX_GATE` for a mutual-exclusion claim |

The deliberately changed algorithm is not a discovered upstream defect. The
positive author lane does not establish unbounded mutual exclusion, actual
application behavior, any C/C++ to Rust correspondence, or AI-inferred intent.

### Seven source-linked acceptance and rejection cases

The `challenge_native.py` script runs against **copies of completed native
TLC logs**: original result, stale source revision, wrong tool binary digest,
missing original log, deleted author invariant check, forged successful
mutant result, and replaced mutated source. The last six must respectively
WITHDRAW, REJECT, WITHDRAW, REJECT, REJECT, REJECT; no silent promotion.
Unit tests use clearly labeled synthetic logs and do not substitute for these
actual native executions.

## Conventional comparator

`conventional_baseline.py` independently uses the original author's `Mutex`
definition/README, exact case config and actual TLC status; it does not import
MathGraph's checker. The predeclared result is expected `BASELINE_TIE`: the
source-aware comparator also refuses green-but-unchecked safety. A claimed
MathGraph accuracy, labor, cost or novelty advantage is **REJECTED/UNKNOWN**
unless a stronger prospective comparison genuinely demonstrates one.

## Exact-head acceptance

GitHub Actions `.github/workflows/mathgraph-microsoft-spec-assurance-tla.yml`
must, in the same job, fetch exact source revision, hash native TLC executable,
run original and two separate native variants, check independent claim
adjudication, execute a strong conventional comparator, run all unit and actual
receipt-tamper tests, check upstream checkout cleanliness and upload all logs,
mutant text, configs, machine-readable reports and code hashes. Only a green
exact-head run plus inspectable artifact merits `WARRANTED_BOUNDED` for this
experiment. A failing/missing artifact means no CI-qualified promotion.

This is a controlled configuration-selection experiment. It does not establish
automatic natural-language intent understanding or a comparative advantage
over a competent source-aware checker.
