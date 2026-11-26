# EIK: host sanitizers do not cover a distinct ARM C path

The numerical frontier work exposed a separate assurance obligation. The pinned
evaluator treats a sanitized x86 host check as evidence about target C behavior.
Identical preprocessing tokens do not establish that the host executes each
target's selected C path.

## Exact scope

Evaluator: `conjectures-io/exact-integer-kernels-miner` at
`5a32428ad4aa23bce737d50a738ace24ddeeed2e`. Fixture: publicly released former
champion #49, SHA-256
`8f8a23345b12abfe41040c6eca20ee06f4a4c50de69fbc6bdf8a9d758f129f37`,
recovered by read-only workflow
[45729980897](https://github.com/metalogiclabs/mathgraph/actions/runs/45729980897).
The fixture retains its original attribution and licensing. No defect is alleged
in that unmodified entry.

Its `RVB = (L'\0' - 1 < 0)` constant selects the RV implementation on the x86
host and RV32IM, and a separate implementation on Thumb. The experiment adds an
unused `uint32_t audit_shift = 1u << 32;` inside the Thumb tanh wrapper. The
repaired control changes the shift count to 31. Neither mutation is submitted to
the competition.

## Bounded evidence

| Check | Deliberately faulty control |
|---|---|
| Official source / preprocessing / object / stack gate | Accepted |
| Official host tanh check, chunk 1016:1017 | 1,048,576 inputs, zero mismatches, no sanitizer rejection |
| Direct visit to the Thumb wrapper under host sanitizers | UBSan rejects the shift by 32 |
| Unsanitized scoring guest allocated images, all three targets | Identical to the unmodified control |
| Target-specific UBSan trap build, tanh at `0x3f800000` | RV32IM returns the expected word; both Thumb targets trap |
| Unmodified and repaired controls | Direct Thumb sanitizer checks and target trap builds return the expected word |

The reproducible script also compares the allocated images of the actual target
exhaustive-checker executables. Its generated `decision.json` declares each check
and only promotes the conjunction when every control passes. Full ELF files may
differ in nonallocated metadata; the comparison includes entry points, allocated
section addresses, flags, types, sizes, and bytes.

The accepted claim has terminal form **FINITE_COUNTERMODEL**: equal preprocessing
and this sanitized host execution do not imply absence of C UB in the selected
ARM path. This is a finite, exact-source software experiment, not a Lean proof.
The host range is explicitly partial. No new full-domain qualification or live
entry acceptance is claimed. A target UBSan trap build is a demonstrated
mitigation for this witness, not proof that every class of C UB is covered.

The [pinned rules](https://github.com/conjectures-io/exact-integer-kernels-miner/blob/5a32428ad4aa23bce737d50a738ace24ddeeed2e/RULES.md#correctness-every-input)
assert that the host sanitizer check stands for the targets. The residual is a
sound host-to-target correspondence argument, or target-specific instrumentation
with a precisely declared coverage boundary. Additional host input coverage
alone does not discharge that obligation.

## Independent qualification

Hosted run [45732700953](https://github.com/metalogiclabs/mathgraph/actions/runs/45732700953)
passed all **25/25** declared checks at source commit
`63d45b4c68cd1fa9a7250cf40588991b4b260f8b`. The hosted verifier and measurement
fingerprints match the previously used official environment. Artifact
`15076629735` was independently downloaded; its provider SHA-256, ZIP CRC, and
all 37 file hashes were verified. Archive SHA-256:
`7262627c41aca79440c9b723e7df7f2f797657e10ac53d1672a40060ff392964`.
The small receipt is `evidence/abi-boundary-20261126.json`. The boundary remains
the declared experiment, including a partial host range, rather than full-domain
qualification of the deliberately faulty source.

## Replay

Use the kit's hash-pinned dependencies, then run:

```sh
python research/eik/abi_sanitizer_boundary.py \
  --kit /path/to/exact-integer-kernels-miner \
  --control /path/to/published-entry49.c --out /path/to/evidence
```

The executable experiment supplies unmodified, faulty, and repaired controls and
asserts the expected outcomes. The hosted replay is defined in
`.github/workflows/eik-abi-boundary-20261126.yml`. Source and evaluator identities,
raw diagnostics, gate reports, image comparisons, and a generated checksum
manifest are preserved in its artifact. Apparatus failures remain failures;
they are not counted as accepted or rejected numerical candidates.

## Lineage and optimization residual

The preceding fully qualified joint source remains separately warranted within
its recorded finite domain; it is not this deliberately faulty control. The
latest six split-quadratic candidates produced no performance winner in two
paired RV32IM draws. Hosted run
[45731111853](https://github.com/metalogiclabs/mathgraph/actions/runs/45731111853)
preserves the rejected sources, certificates, and measurements. Artifact
`15076144226` was independently SHA-256 and CRC verified:
`6005e9bb650f788eb0dfbd28fd9b644a50764c0477ac63dd4b8cc3eb800f885b`.

Four tail-rank pilots against the recovered published #49 source also failed to
improve the ARM score on the declared local draw. These are bounded performance
rejections, not incorrectness results. Their generators, exact interval
certificates, and reports are retained. A winning optimization is still UNKNOWN.

Across this and earlier representation-boundary cases, the reusable hypothesis
is to test whether evidence crosses the required boundary before increasing its
volume. Its proposed procedure is: identify the bridge, introduce a control
that breaks only that bridge, test whether the existing assurance detects it,
then verify a repair with both positive and negative controls. The individual
witness here is warranted; universality of that procedure is not claimed.
