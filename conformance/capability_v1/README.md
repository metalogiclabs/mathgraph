# Independent finite capability qualification v1

The admitted result is `QUALIFIED_BOUNDED` for one exact contract and finite
profile. This is **same-owner implementation-independent qualification**, not
external adoption or independent organizational trust. It establishes no
universal invention theorem, autonomous improvement, open-ended generalization,
present applicability, freshness, revocation status, or authorization. It does
not add a mathematical terminal form.

`consumer.py` uses only Python's standard library. It never imports the original
experiment, `mathgraph_protocol`, the website, or producer verdict tables. Its
inputs are the finite vectors/boundary, exact portable descriptor, and separately
pinned trust policy. Source references are provenance; their programs are not
executed or mounted during qualification. The correspondence test checks their
original byte hashes outside isolation.

Typed inputs and outputs describe the portable replay boundary and its
evaluation. The original implementation pin identifies candidate provenance;
this admission does not certify that original program's CLI or runtime behavior.

## Replay and scope

The carrier is the ordered eight-state Boolean cube. A vector is encoded as an
integer mask with state index 0 in the least significant bit. The consumer
enumerates all 256 Boolean functions of the carrier, retaining exactly the masks
that respect every pair of observationally indistinguishable states. This is a
different implementation from the producer's enumeration of output assignments
to representation cells. Closure cardinality is cross-checked against `2^cells`.

The old parity closure is `[0, 105, 150, 255]`; discovery mask 144 is excluded.
The obstruction consists of state-index pairs `(1,4), (1,7), (2,4), (2,7)`.
Only `bit0` repairs discovery within the fixed named family (`bit0`, `bit1`,
`bit2`, `weight`, `constant_zero`). The chosen feature equals neither target.
The refined closure has 16 policies; independently replayed lookup witnesses
construct discovery and reuse mask 246. The same-shape `bit1` sham fails both.
Removing `bit0` restores the old partition and obstruction; all four old policies
remain available after refinement. Reuse means two distinct target functions in
the same owned source, not two external sources or consumers.

All 256 Boolean one-bit features are examined. For each, literal closure
membership, cell consistency, and separation of every certified conflict must
agree. Exactly 32 succeed, inducing eight partition classes: four successful
features have three cells and 28 have four cells. The receipt includes every
successful mask and partition signature. Cost/minimality here is one appended
observable and finite policy/cell counts within the named family, not wall-clock
efficiency or globally minimal invention. The original protocol was not
historically preregistered.

## Pins and admission

The policy pin is supplied independently of the input documents:

```text
7069c764579d933679f6bfd9b922a724ad9bcb250e4060c660cb4fd099c60e89
```

The policy pins exact fixture, descriptor, and verifier bytes. The verifier
checks its own bytes against that policy, validates the supported profile, then
recomputes every gate. An evaluation or receipt is never an input to replay.
No producer-supplied `PASS`, gate table, qualification, or circular receipt can
qualify the descriptor. Trusting a different policy is an explicit consumer
decision; deriving a policy hash from untrusted supplied bytes grants no trust.
Hashes establish byte correspondence, not independent publisher authenticity.

Only after replay succeeded were `evaluation.json` and `receipt.json` saved and
one entry admitted to `protocol/registries/capabilities-v1.json`. The registry
schema puts status and scope in pinned artifacts: `evaluation.json` says
`QUALIFIED_BOUNDED`; the contract and receipt give the scope and limitations.
The public `website/public/capabilities/index-v1.json` is byte-identical. The VDN
Lean candidate remains `EXPERIMENTAL`. The general descriptor evaluator still
returns `UNKNOWN`; it does not infer qualification merely by reading a registry.

The policy binds the verifier but not its own receipt. The receipt binds the
policy and all inputs; the evaluation binds the receipt. The registry pins each
artifact. This dependency chain has no receipt-to-input qualification cycle.

## Offline operation

```bash
python -I -S conformance/capability_v1/consumer.py \
  --fixture conformance/capability_v1/fixtures/finite-representation-refinement-v1.json \
  --contract conformance/capability_v1/fixtures/capability-contract.json \
  --policy conformance/capability_v1/trust-policy.json \
  --policy-sha256 7069c764579d933679f6bfd9b922a724ad9bcb250e4060c660cb4fd099c60e89 \
  --audit-imports

python conformance/capability_v1/run_isolated.py --backend macos \
  --policy-sha256 7069c764579d933679f6bfd9b922a724ad9bcb250e4060c660cb4fd099c60e89

python -m pytest conformance/capability_v1 -q
```

CLI exit 0 means exact bounded replay succeeded; all nonqualification outcomes
exit nonzero with `UNKNOWN` and no receipt. It never fetches artifact locators,
executes a constructor, deploys anything, or mutates a record.

The host isolation harness copies exactly `consumer.py`, `finite.json`,
`capability-contract.json`, and `trust-policy.json` to a read-only input
directory. On macOS it uses `sandbox-exec` with default deny, network deny, and
read access only to system/runtime files and the four inputs. The sandbox must
run from a host able to create it; nested restricted sandboxes can reject
`sandbox_apply`. The test fails in that environment rather than skipping denial
checks. On Linux the new workflow uses a previously acquired immutable Docker
image, `--network none`, a read-only filesystem, dropped capabilities, an
unprivileged user, and only that directory mounted. Runtime libraries are the
only non-input reads allowed. Credentials, producer sources, repository, and
Docker socket are not mounted or passed through.

The harness probes both IP families for network denial and verifies the
repository is unreadable, audits standard-library-only imports, and compares
two complete replay outputs byte-for-byte. Its metadata goes to stderr. The
Linux backend is exercised by CI; the local admission used the macOS backend.
The workflow saves logs in temporary artifact storage, not the repository.

Mutation controls cover missing/duplicate states, altered targets/refinements,
incomplete policy/refinement coverage, sham substitution, retention loss,
ablation, identical reuse source/target, changed scope/source/verifier/assumptions,
unsupported profiles/transports/extensions, duplicate JSON keys, nonfinite
numbers, Boolean-as-integer values, and self/circular qualification. Rebound
policy tests also check that changing pins cannot expand the implemented profile.
