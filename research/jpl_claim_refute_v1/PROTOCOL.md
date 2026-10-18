# JPL L4YAML: refute-first, source-pinned claim-scope audit (V1)

**Independent experiment on existing public source; no JPL write or contact.**
This report is deliberately narrow and reproducible. The September MathGraph
[issue #134](https://github.com/metalogiclabs/mathgraph/issues/134) and
[issue #135](https://github.com/metalogiclabs/mathgraph/issues/135)
already refuted the earlier `parse_iff_grammar` theorem. Do **not**
credit this experiment with rediscovering those counterexamples.

## Precommitted source and advertised claim

- Repository: `nasa-jpl/L4YAML`
- Exact head: `bca37392fdcb80481342a186a37ab37a5ede6e46` (18 October 2026 UTC)
- [README at exact SHA](https://github.com/nasa-jpl/L4YAML/blob/bca37392fdcb80481342a186a37ab37a5ede6e46/README.md):
  opening paragraph says conformance to YAML 1.2.2 and the yaml-test-suite
  "is established by mathematical proof, not by testing alone".
- That same README later labels `parse_iff_grammar` "**NOT the target: this
  statement is false**" and states a converse remains open.
- [Serialization package README](https://github.com/nasa-jpl/L4YAML/blob/bca37392fdcb80481342a186a37ab37a5ede6e46/L4YAML/Proofs/Serialization/README.md)
  says independent whole-input input-to-event correspondence is **not proved**.
- [Narrower proved boundary](https://github.com/nasa-jpl/L4YAML/blob/bca37392fdcb80481342a186a37ab37a5ede6e46/L4YAML/Proofs/Serialization/ExecutableBoundary.lean):
  `parse_iff_executable_language` factors the real executable stages; it is
  not a non-circular proof of a normative YAML language correspondence.

## Predeclared verdict rule

A broad documentation claim asserting completed full conformance **together
with an explicit open required converse** is `NOT_ESTABLISHED_BY_DOCUMENTED_PROOF`.
This is a mismatch between the headline's warrant and the author's own later
scope statement. It does **not** refute an actual Lean theorem, establish a
new YAML counterexample or declare the library unsafe.

A missing residual must yield `UNKNOWN_REQUIRE_FURTHER_AUTHORITY`, not a
fabricated counterexample. The known, narrow factorization lemma remains
`BOUNDED_PROOF_NOT_REFUTED`.

## Independently executable controls

1. `claim_audit.py`: checks exact target Git commit, validates exact scoped
   author statements, SHA256-hashes evidence files, runs five positive and
   negative classification controls, and emits `jpl-claim-audit.json`.
2. `native_probe.lean`: invokes actual `L4YAML.TokenParser.parseYaml` at
   the same immutable revision, tests two accepted inputs and four historically
   documented rejected inputs. These tests are control replication, not an
   independently discovered new obstruction.
3. `.github/workflows/jpl-claim-refute-v1.yml`: runs the two lanes using
   GitHub's hosted CI. Failures due to network, dependency installs or
   build infrastructure are **APPARATUS UNKNOWN** until the logs support a
   more specific conclusion. No automated changes to JPL sources.

## Exact finding / invitation to a prospective test

`NOT_ESTABLISHED_BY_DOCUMENTED_PROOF` on the public README opening claim,
according to its own later caveat. The repair could be a scope-precise
headline, without changing or weakening any existing proof.

A genuine next scientific advance requires **a fresh, precisely stated
candidate claim, frozen before the adversarial search**, and a source-native
counterexample, non-counterexample or explicit UNKNOWN result. Prefer the next
corrected surface/executable correspondence theorem to replaying the old
`parse_iff_grammar` refutation. Compare against the maintainers' already
available test suite and verification scripts to establish incremental value.

## Scope of results

At file creation time, results are *pending CI*. Successful source-identity,
report controls and native probes must be read from actual GitHub Actions jobs
before elevating their status. No correctness certification or new theorem
falsification is being advertised.
