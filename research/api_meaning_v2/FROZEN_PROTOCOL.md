# V2 — Prospective canonical-meaning obligation acquisition (frozen before held-out source)

**Scientific state: CANDIDATE until independent native/prospective verification.**

## Training and gap
Training source `python-hyper/hpack@c2edbee3b5508e0b1689877fe6f173eafb097aef` exposed in V1. Frozen V1 discovery [f0d4868d](https://github.com/metalogiclabs/mathgraph/commit/f0d4868d6dfe67781038772c46f80e4710d40084); [502/502 native GREEN #39217080220](https://github.com/metalogiclabs/mathgraph/actions/runs/39217080220), raw ZIP SHA256 `95e202a1a5ceed18246a114766969afbd250e949b8e1f7d3addc77e96d44068b`. 9 accepted, 6 strict identity counterexamples, equal-information rule comparator TIED. Many negatives are intended list/dict/byte-to-text normalization; V1 did not discover the correct quotient.

**Objective:** A human-authored but source-independent proposer should instantiate not just strict inverse identity but a *canonical-form stability obligation* and an independently interpreted *JSON correspondence obligation* when a standard-library JSON reader genuinely applies. This is a bounded, PREDECLARED interpretation family, not autonomous grammar invention or general JSON correctness.

## Selection sealed before code or source access
Deterministic ordered pool (metadata-only; no files, documentation, commit diff, API signatures, tests, issues or outcomes read before freeze):
1. `simplejson/simplejson`
2. `agronholm/cbor2`
3. `msgpack/msgpack-python`

After immutably committing protocol, proposer and comparator, execute synthetic source-blind controls in CI. Select **first** GitHub repository with `archived=false`, `disabled=false`, `language=Python`, and available default-branch full SHA. Record selection SHA and only then open native repository. No fallback after checking outcomes. Module = repository basename, except strip terminal `-python` (source-neutral fixed rule). Missing import or unsupported API -> UNKNOWN, not target-specific edits.

## Frozen API proposal grammar
Discover exported top-level named pairs with exactly one mandatory positional argument and optional extras:
`dumps/loads`, `encode/decode`, `packb/unpackb`, `safe_dump/safe_load`, `serialize/deserialize`. Discover public `*Encoder`/`*Decoder` class pairs, both no-required-arg constructors, with one-payload `encode/decode` methods. No per-target rules or fixture edits.

Frozen seeds (in this order): `'hello'`, `b'hello'`, `''`, `b''`, `0`, `1`, `True`, `None`, `{'x-mg':'v-mg'}`, `[('x-mg','v-mg')]`, `[(b'x-mg',b'v-mg')]`, `[(':method','GET')]`, `[(b':method',b'GET')]`, `[('x-mg','v-mg'),('x-other','2')]`, `[(b'x-mg',b'v-mg'),(b'x-other',b'2')]`, `{'x':[1,2],'z':True}`, `2.5`.

For every encoder-accepted seed, with fresh instances:
1. Strict original identity, `D(E(x)) == x` and same Python type. Counterexamples reject THIS overly strong candidate, never imply publisher defect.
2. Canonical normal form: with `N(x)=D(E(x))`, compare `N(N(x))` to `N(x)` with strict type/value equality; distinguish ineligible canonical inputs and true mismatch. Qualification requires >=3 supported canonical seeds, >=2 distinct canonical outputs, and all supported stable.
3. Independently interpreted reference: call independent **Python standard-library `json.loads`** on the emitted wire when accepted. Require exact type/value agreement `json.loads(E(x)) == D(E(x))`, >=3 usable seed cases incl >=1 dict/list and >=2 distinct reference outputs. Additionally append `!` to each JSON wire: require independent stdlib JSON reader REJECT the perturbed wire on >=2 examples. Any observed reference disagreement REJECTS; unparseable wires or missing independent interpreter are UNKNOWN, not semantic negatives. Scope is the finite JSON subset and stdlib oracle only; no other grammar or oracle may be learned after seeing source.
4. Missing or ambiguous independent relation always **UNKNOWN** for general semantic fidelity, regardless of canonical idempotence or native tests.
5. No status may be REUSABLE without source-distinct prospective transfer after freeze and comparator qualification.

## Strong equal-information baselines
- Author's **original native pytest suite** executed unchanged and archived; tests are authoritative for their own specified behaviors and may not be overridden by these proposed relations.
- A **separately authored, source-independent expert-rule comparator** receives identical pinned source/API surface, 17 seeds, stdlib JSON oracle and mutation checks, and independently enumerates the same public patterns. It must not import proposer or consume proposer outputs. Report exact candidate/seed-level differences; any disagreement returns UNKNOWN_COMPARATOR_CONFLICT.
- This is NOT an independent outside human expert or competent coding agent. We must NOT assert economic, recall, precision or superior utility if it ties.

## Admission, controls and stopping
Self-tests must cover supported JSON, constant-output decoder (nontriviality guard), disagreement with standard-library reference, unsupported/no-pair and benign encoder refusals, before source opening. Freeze exact SHA for protocol + two executables + seeds + comparator + test. Workflow invokes this SHA, not working-branch versions.
Native runner checks original Git SHA, no source writes, author test JUnit with failures/skips, exact input/output hashes and independent reference results. Archive raw data. Errors and UNKNOWNs are genuine outcomes; apparatus corrections only with their own red history and never change frozen code or seeds.

**No prospective reroll, no manual target adapter and no retcon of hpack V1.** A successful V2 licenses only finite reference-linked semantic correspondence in the JSON standard subset under the pinned source and reference interpreter.
