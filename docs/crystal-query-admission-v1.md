# Crystal query admission V1

Goal: an exact query moves UNKNOWN -> external candidate -> independently checked
answer -> persisted Crystal -> identical query, without another external search.

This extension reuses the existing TPTP/Vampire route and protected-continuation
objects. `scripts/learn_crystal.py` is the bounded local front door.

## Qualified grammar and verifier boundary

Only ground unary atoms `p(a)` and axioms `! [X] : (p(X) => q(X))` are
admissible. Names are arbitrary; formulas are fully parsed, not substring
matched. Other connectives, equality, functions, arithmetic and existential
axioms return UNKNOWN. Limits: 128 axioms, 4096 characters per axiom, 4096 ground
predicate/constant pairs. This is not a general TPTP frontend.

Vampire is discovery only. The admission checker independently reconstructs a
proof from the exact axioms or produces a complete finite interpretation that
satisfies every axiom and falsifies the conjecture. Lean 4.24.0 checks the
resulting source and must report no axiom dependencies. There is no `sorry`,
`native_decide`, or user-supplied Lean in this path. This is an independent
reproof/model-check boundary, not proof-trace reconstruction from Vampire.

Query identity binds the entire residual (axioms, conjecture, boundary, source
references). Both positive and negative answers require live checker support.
Revocation returns UNKNOWN. The gateway was corrected to apply support liveness
to EXCLUDED answers as well as WARRANTED answers.

Input and output bytes, candidate result, Lean source, checker output, receipt,
and machine snapshots are retained as evidence. Hashes identify bytes; they do
not themselves establish truth. Premises are conditional mathematical hypotheses,
not assertions that the world satisfies those premises.

## Usage

Install the package and make pinned Vampire 5.1.0 and Lean 4.24.0 available:

```sh
python -m pip install -e '.[dev]'
python scripts/learn_crystal.py \
  --residual examples/crystal_brain_demo_residual.json \
  --store /tmp/crystal-socrates/machine.json \
  --evidence-dir /tmp/crystal-socrates/evidence \
  --vampire /path/to/vampire --lean /path/to/lean
```

Repeat that command with `--vampire /missing --lean /missing`: the persisted exact
answer must still be returned, with `external_calls: 0`. `--no-discovery` always
queries only the local store. The original demo's natural-language label is not
a semantic binding; this command derives the question from the formal residual.

## Limits

This is a trusted-local-runner prototype, not an authenticated public service.
The operator controls the checker executable, live-support policy and store.
Arbitrary edited machine JSON must not be accepted from an untrusted client.
No transactional multi-writer merge or cross-foundation equivalence is claimed.
One store is currently one exact residual. Output latency measures distinguish
cold external work from in-process query time; neither is a global scaling law.

Target gate: inherited 25 tests + new admission regressions + real Vampire/Lean
proof, countermodel and renamed-chain cases + reload/no-tools replay + revocation.
A separate repository-wide diagnostic is recorded; its failures are not silently
reclassified as admission correctness results.
