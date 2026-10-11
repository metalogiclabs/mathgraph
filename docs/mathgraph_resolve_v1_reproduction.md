# Reproduce Resolve record 002

Record `mg-living-warrant-openai-jpl-20261010` is a frozen historical snapshot.
Expected results are three documentary supports becoming `STALE`, three
propositions remaining `UNKNOWN`, and the exact JPL finite observation retaining
`WARRANTED_BOUNDED`. The modeled before-state is not proof that the withdrawn
arguments were mathematically correct.

## Exact offline inputs

The published [Resolve bundle schema](https://mathgraph.org/schemas/resolve-bundle-v1.schema.json)
and [Resolve trust-policy schema](https://mathgraph.org/schemas/resolve-trust-policy-v1.schema.json)
describe the transport structure. These schemas do not authenticate records or
replace the separately pinned trust policy and semantic replay. See the
[format contracts](resolve_bundle_trust_policy_v1.md) for the independent
structural/admission validation boundary.

Download the following resources before entering network isolation. Each public
file must be byte-identical to its canonical repository source.

| Input | Durable URL | SHA-256 |
| --- | --- | --- |
| Python consumer | [consumer.py](https://mathgraph.org/evidence/mg-living-warrant-openai-jpl-20261010/offline/consumer.py) | `27a9be606040cc94a47c9b903dfc1cb24a86cbbc4e05ce71040c6c3d6e8d527b` |
| Canonical bundle | [bundle.json](https://mathgraph.org/evidence/mg-living-warrant-openai-jpl-20261010/offline/bundle.json) | `957080db79555f982fd3a314c263cf5177ef506969229e856897f0b19ccc1d62` |
| Separate trust policy | [trust-policy.json](https://mathgraph.org/evidence/mg-living-warrant-openai-jpl-20261010/offline/trust-policy.json) | `09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a` |

Canonical sources are `conformance/resolve_v1/consumer.py`,
`conformance/resolve_v1/fixtures/bundle.json`, and
`conformance/resolve_v1/trust-policy.json`. Publication does not regenerate them.
Obtain the expected policy pin and trusted consumer through a separately trusted
channel. A hash supplied by the same untrusted download host is insufficient.

From a directory containing only these three files, use Python 3.11 or later:

```sh
python -I -S consumer.py --bundle bundle.json --policy trust-policy.json \
  --policy-sha256 09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a
```

Stdout is canonical UTF-8 JSON with one newline. Its deterministic SHA-256 is
`8c7b30e1eb2a24d2960e170d36652ca95aa71b41075f673abe394e154ae66668`.
The bundle embeds the exact 5,290-byte snapshot, 2,281-byte OpenAI history file,
and 4,321-byte JPL public record with independently checked member pins.

The command above performs replay but does not itself enforce network denial.
For actual local macOS isolation, from the repository run:

```sh
python conformance/resolve_v1/run_isolated.py --backend macos \
  --policy-sha256 09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a
```

The harness copies only the three inputs, uses `sandbox-exec`, checks IPv4/IPv6
denial and repository unavailability, audits stdlib imports, and compares two
replays. It fails if isolation cannot be enforced. The Linux CI harness instead
uses Docker `--network none`, read-only files, dropped capabilities, and an
unprivileged UID. It pulls the pinned manifest before isolation and records/runs
the resolved image identity. Read `conformance/resolve_v1/README.md` for that
exact environment contract. Do not substitute a successful online run for this
physical isolation evidence.

## Independent Node HTTP client

Save [resolve-consumer-v1.ts](https://mathgraph.org/examples/resolve-consumer-v1.ts)
after reviewing its source and authority constants. This release's exact client
transport SHA-256 is
`e7360df24b2fd0900c8ea88ccb1689163cec73a6c2e2347e4ab2b23b4d01bc2e`.
Obtain the expected code pin through an independently trusted channel before
executing downloaded code; this document from the same host cannot authenticate
that download by itself. Use Node 24.15 or later in
the Node 24 line; no package installation or TypeScript loader is required:

```sh
printf '%s  %s\n' e7360df24b2fd0900c8ea88ccb1689163cec73a6c2e2347e4ab2b23b4d01bc2e resolve-consumer-v1.ts | shasum -a 256 -c -
node resolve-consumer-v1.ts https://mathgraph.org
```

For a locally served built site, replace the origin with its loopback origin.
The client fetches only `/records/index.json` and the fixed record-002 snapshot,
scenarios, bundle, and policy paths. It validates independent authority pins,
decodes and checks exact bundle members, and recomputes closure using its own
work queue. It imports no website catalogue, producer, publisher, Python client,
or verifier implementation. Producer/scenario statuses are comparison assertions
only. Stdout is deterministic canonical JSON in the distinct
`mathgraph.resolve-http-report.v1` schema; its bytes are not the Python report.

This client requires HTTP access. It is not the three-input offline proof, a
hosted endpoint, or evidence of current applicability. It is an independently
implemented integration/reference client under the same owner.

## Qualification and limitations

The historical producer is commit `040456fc8862c79c8b384ce63846628274b678be`,
[Actions run 38025044631](https://github.com/metalogiclabs/mathgraph/actions/runs/38025044631).
The prior RealityGraph replay is commit
`9b3189a64825e2cb6ebc7b5c17f5f193bdf5cfe3`,
[run 38025236380](https://github.com/heathsanchez/realitygraph/actions/runs/38025236380).
The P0 independent offline gate is
[run 38086245988](https://github.com/metalogiclabs/mathgraph/actions/runs/38086245988).
These are historical qualifications, not claims that an unpushed local change
has already passed remote CI.

The scoped website workflow preserves record-001 receipt regeneration and adds
record-002 source/publisher checks, independent Python conformance, public-byte
identity, and the independent Node HTTP integration. From `website/`, after the
locked dependency installation, run:

```sh
npm run qualify
```

The HTTP test serves built static files on loopback and executes a copy of the
Node reference client from an otherwise empty directory. It verifies positive
outcomes and rejects altered pins/bytes, self-rehashed forged statuses, unsupported
schemas/kinds/relations, source/verifier/assumption/scope mismatch, and malformed
JSON. A rootless cycle remains `UNKNOWN`.

Current applicability remains `UNKNOWN`; freshness and revocation/supersession
remain `NOT_CHECKED`; no action is authorized. Neither client reruns the original
JPL Lean proof, refutes the OpenAI propositions, generalizes the 48-case result,
or establishes outside-organization adoption. See the
[threat model](mathgraph_resolve_v1_threat_model.md) for trust-channel and retained-
evidence limits.
