# Independent Resolve v1 historical replay

This is a separately implemented Python standard-library consumer. It does not
import MathGraph Check, the producer kernel, the publisher, the website, Discover,
or Develop. The replay needs exactly `consumer.py`, `bundle.json`, and
`trust-policy.json`, plus Python 3.11 or later. No installation is needed.

## Trust boundary

The consumer implements the deliberately narrow record-002 historical profile.
It requires a trust policy supplied separately from the bundle and its SHA-256
supplied by the caller. The reviewed policy pin for this release is:

```text
09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a
```

A recipient must obtain that expected pin through their own trusted channel.
Computing a digest from a newly received policy does not authenticate that policy.
Neither the bundle nor an embedded record can replace it. This profile also
rejects policy contents outside the explicitly supported historical authority.
The commit/run references are provenance under this policy, not cryptographic
publisher signatures. Hashes detect substitution relative to admitted pins.

The policy admits three documentary receipts only as modeled historical support
for original publications, and one qualified JPL finite-parser receipt at its
exact 48-case scope. The OpenAI notice is documentary evidence of withdrawal;
it proves neither the truth nor falsity of the three mathematical propositions.
The bundled public JPL record refers to earlier Lean qualification. This replay
does not rerun Lean or inspect the original archive proof objects.

## Canonical bundle contract

`mathgraph.resolve-bundle.v1` contains only `schema`, `provenance`, and `members`.
Each named member contains only `encoding: base64`, `data`, `size`, and `sha256`.
The bytes are checked independently against the separate policy, including byte
length and SHA-256. The member-provided hash never admits the member itself.

| Member | Bytes | Transport SHA-256 |
| --- | ---: | --- |
| `record.json` | 5,290 | `0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87` |
| `history.md` | 2,281 | `41c2a2d470014b3628695c7aabf5fd0c93f6f687621fca172062f22b59ed6a1e` |
| `jpl-record.json` | 4,321 | `7b59ee76a39995f35a0feb0f4d91a3c6ab1234393143480c4f3e361a79fee703` |

Bundle SHA-256:
`957080db79555f982fd3a314c263cf5177ef506969229e856897f0b19ccc1d62`.

Bundle, policy, and output use UTF-8 JSON, sorted object keys, compact separators,
unescaped non-ASCII characters, and one final newline. Member bytes are preserved
exactly, not reserialized. Internal record payload hashes exclude the hash field
and final newline. Duplicate keys at any depth, non-finite numbers, ambiguous
types, unsupported fields/versions/transports, and unauthorized source identities
fail closed. This is a declared profile, not a general JSON canonicalization
standard or a general-purpose evidence container.

## Resolution contract

Every claim and receipt has an explicit identity, kind, and scope. Receipt
admissions additionally specify verifier identity, source, empty assumptions,
and outcome. V1 supports no implicit assumptions, scope generalization,
cross-kind transport, or relation extensions. Unknown references are rejected;
a declared premise without support remains `UNKNOWN`.

Routes are conjunctive, and separate routes to the same claim are alternatives.
Starting with every claim `UNKNOWN`, the consumer repeatedly admits conclusions
whose receipts remain admitted and whose premises have support, until no new
claim changes. Rootless cycles establish nothing. The modeled-before and
withdrawn-after closures are calculated separately; loss of previous support
is reported as `STALE`. Producer statuses are compared only after this
calculation and cannot seed it.

The report separates `historical_evidence_qualification`, `historical_resolution`,
`current_applicability`, `freshness`, `revocation_or_supersession`, `lifecycle`,
and `action_authorization`.
Offline current applicability is always `UNKNOWN`, freshness is `NOT_CHECKED`,
revocation or supersession is `NOT_CHECKED`, and no action is authorized.
Historical qualification does not imply current
applicability. RealityGraph's prior replay has independent implementation but
the same owner; it is not independently owned external adoption.

Synthetic tests are separate from the historical bundle. They cover alternative
routes, conjunctive dependencies, removed routes, localized descendants,
unrelated support, missing support, cycles, and exact scope matching. A synthetic
`REFUTED` result requires a complete two-element magma table, an in-carrier
assignment that actually violates commutativity, exact scope
`magma:commutative:order=2`, and explicitly allowed verifier
`finite-magma-noncommutative-v1`. A hash or label alone fails. This finite
countermodel is solely a conformance witness; no OpenAI refutation is invented.

## Run and regenerate

From a directory containing only the three inputs:

```sh
python -I -S consumer.py --bundle bundle.json --policy trust-policy.json \
  --policy-sha256 09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a
```

That command alone does not enforce network isolation. Qualification requires
the host harness below, which first copies the three inputs, then probes the
same sandbox/container configuration used for two deterministic replays:

```sh
python conformance/resolve_v1/run_isolated.py --backend macos \
  --policy-sha256 09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a
```

macOS uses `/usr/bin/sandbox-exec` with deny-default and explicit network denial.
Only OS/runtime library locations and the three-input directory are readable;
directory metadata is available to the loader. The probe confirms that repository
content cannot be read and that IPv4 and IPv6 connectivity is denied. Nested
sandbox environments may refuse sandbox creation; run the harness from a host
context where macOS can enforce it. Failure is fatal; there is no skip/fallback.

Linux CI prepares the runtime and dependencies before isolation. It resolves
`python:3.11-slim@sha256:e529028263dbe6910a2d96f7d2b8f5266385e917fd45d286ef166977c094a51e`
to an immutable local image ID, records the full inspection,
then passes that ID to `run_isolated.py --backend docker --image-id sha256:…`.
The container uses `--network none`, a read-only root, dropped capabilities,
an unprivileged UID, and only a read-only mount of the three-file directory.
No host repository, credentials, source archives, services, or Docker socket
are mounted. The local macOS run does not test Docker. A successful remote
dedicated workflow is still required before catalogue/UI integration.

Stdout is only the deterministic replay report. Stderr is the isolation
attestation, including the probe, actual image identity (Linux), import origins,
replay arguments, repeatability, and report hash. `--audit-imports` also checks
that every imported file is from the interpreter's standard-library prefix,
excluding site-packages. The harness itself stays outside the replay directory.

Expected replay SHA-256:
`8c7b30e1eb2a24d2960e170d36652ca95aa71b41075f673abe394e154ae66668`.

```sh
python -m unittest discover -s conformance/resolve_v1 -p test_consumer.py -v
python scripts/package_mathgraph_resolve_v1.py --history /path/to/pinned/history.md --check
```

The packager only copies exact, pinned bytes and fixed provenance into canonical
JSON. Without `--check` it regenerates the bundle. It performs no resolution and
imports neither the consumer nor the producer. Acquire the history file before
isolation; no replay command downloads anything.
