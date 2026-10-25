# API obligation V1 — source-blind prospective hpack result (19 October 2026)

**Scientific status:** `WARRANTED_BOUNDED_FINITE_OBLIGATION_INSTANTIATION` that an unchanged grammar automatically *proposed and refuted* an exact value/type identity candidate on a preselected source. Proposed universal identity: **REJECTED_BOUNDED**. Relative advantage over equally informed expert-authored comparator: **TIE**. Autonomous acquisition of new semantic relation/quotient: **UNKNOWN**. No upstream defect inferred.

## Immutable chronology and authentic sources

1. Precommitted method, 13 probes, source-order/eligibility rule, independently written expert-rule comparator and synthetic controls: [f0d4868d6dfe67781038772c46f80e4710d40084](https://github.com/metalogiclabs/mathgraph/commit/f0d4868d6dfe67781038772c46f80e4710d40084).
2. Original source-blind synthetic GREEN: [Actions #39216625119](https://github.com/metalogiclabs/mathgraph/actions/runs/39216625119); artifact #12170320355 SHA256 `f66f49eb0cfd4103818165cc30effa624b99d887a1f522a3b6b884804a58a355`.
3. After this freeze, metadata-only first eligible selection: `python-hyper/hpack`, Python, nonarchived, `master@c2edbee3b5508e0b1689877fe6f173eafb097aef`, frozen in [e234f42](https://github.com/metalogiclabs/mathgraph/commit/e234f42f1eb1dce50f6a9175559c5b76e8e4956e). No source/tree/tests opened before selection.
4. First [apparatus RED #39216900365](https://github.com/metalogiclabs/mathgraph/actions/runs/39216900365): full `pytest -q external-native` from parent directory collected bench tests requiring an uninstalled benchmark fixture and ran integrations without checkout-relative fixture paths: 88 PASS, 11 environment/collection ERROR. **Generator not executed; not a scientific failure or a separate trial.** Only workflow invocation changed to the publisher's declared source-root pytest context. No generator, comparator, source, corpus or selection changed.
5. First full prospective qualifying [Actions GREEN #39217080220](https://github.com/metalogiclabs/mathgraph/actions/runs/39217080220), workflow commit [21afef67](https://github.com/metalogiclabs/mathgraph/commit/21afef6732523f725d1153a4666aa9a182725cf2), artifact #12169972409. Actual ZIP SHA256 `95e202a1a5ceed18246a114766969afbd250e949b8e1f7d3addc77e96d44068b`, independently recomputed locally from connector artifact bytes and matched GitHub's archive digest.

## Native evidence and proposed relation

The publisher's original source-native pytest suite: **502 PASSED, zero failed, zero skipped, seven warnings** under Python 3.12. Immutable source SHA checked; `hpack` imports resolved under the original editable source checkout.

The unchanged method selected **one** public signature/name-pair candidate:

`class:Encoder.encode -> Decoder.decode`

Predeclared candidate strict relation: `type(Decoder().decode(Encoder().encode(x))) is type(x)` AND `Decoder().decode(Encoder().encode(x)) == x` with fresh instances for each of all 13 predeclared seeds.

Exact verdict from machine evidence:
- **4 ineligible encoder inputs:** seed indices 0 (`str "hello"`), 1 (`bytes b"hello"`), 4 (`int 0`) and 5 (`int 1`). Exceptions were preserved, not counted as counterexamples.
- **9 accepted seeds:** 3 exact matches at indices 7, 9, 11 (all string-header tuple lists), **6 semantic/type counterexamples** at indices 2, 3, 6, 8, 10, 12.
- Concrete counterexample families: empty str/bytes inputs encode but decode to an empty header list; dict input normalizes to a list of header tuples; byte-string header-pair inputs decode as string pairs by default. These refute **strict type+value identity** but not the library's intended supported HPACK semantics. No repair attempted.

The independently implemented **expert-authored rule** received the same API, source and fixed seeds and independently emitted `REJECTED_BOUNDED`, 9 accepted, 6 counterexamples with exact per-seed agreement. Thus **TIE**, not superiority. It is a fair equal-input automatic conventional-rule comparator, **not** an independent human expert or competent coding-agent experiment.

## Warrant/promotion decision

- **WARRANTED_BOUNDED:** the frozen method instantiated a previously unexamined third-party public API relation candidate and its finite adjudication, including genuine falsifiers, without any per-target grammar patch. The source-native test suite is green.
- **REJECTED_BOUNDED:** claimed exact identity on the accepted 9-case finite corpus (six falsifiers).
- **UNKNOWN:** automatic inference of correct semantic quotient (byte/string normalization, mapping-vs-list canonicalization), externally authoritative intended API requirements, usefulness beyond familiar reversible-name grammars, economic improvement against competent humans/agents, G2/L7 autonomous constructor invention and source-distinct transfer.
- **SUPERSEDED/NOT CLAIMED:** a green CI run never turns the rejected identity into a valid law. A hindsight repair of V1 would invalidate the held-out test.

**Smallest next decisive experiment:** make this exposed hpack evidence TRAINING, derive a *source-neutral* output-canonicalization operation from its counterexamples, freeze the operation and candidate pool **before** opening a second unrelated repository, then test unchanged with independent native evidence against both a fully informed rule baseline and competent coding-agent baseline. If no stable quotient can be inferred, record UNKNOWN_NO_CANONICALIZATION instead of hand-coding a target schema.

This is new *obligation instantiation* inside a human-authored grammar, not universal autonomous semantic-language learning.
