# MathGraph Check — first public evidence record (read-only)

This release is an **agent-first, no-mutation publication projection** over the
already qualified L4YAML pinned-source CI artifacts. It is not a new proof,
reformalization, natural-language theorem translation or Palomar registration.

## Authority and scope

- Exact original JPL L4YAML source and Lean proofs:
  nasa-jpl/L4YAML@62bf7077910e888a0bc8adfc8e08a5f500ff3ca3
  (the merged serialization feature branch; *not* default main).
- Independent YAML test suite:
  yaml/yaml-test-suite@da267a5c4782e7361e82889e76c0dc7df0e1e870.
- Full compiled original CLI parser and named theorem import:
  [MathGraph Actions 38018495536](https://github.com/metalogiclabs/mathgraph/actions/runs/38018495536);
  artifact #11657687808, sha256:b75581017d6620481c77e52b350e8bb8631d11747a92789f7887cde527807086.
- Correctly decoded original Lean parser, 48/48 external acceptance cases and
  four extra guards: [MathGraph Actions 38020008793](https://github.com/metalogiclabs/mathgraph/actions/runs/38020008793);
  artifact #11657314389, sha256:61fc93815e3329c0490324f52897a94d3417044a5cf16a8e1e0f0109aa0e515e.

The publisher **checks the ZIP hashes before reading any supplied result**,
then validates original Git object pins, case counts, YAML source decoding,
generated guard-source digest, independent Lean theorem names/axiom sets,
native Lean version, "no output" guard evaluation, and non-promotion fields.
It **fails closed** if any receipt, input or protected status changes.

Do not generalize 48 case observations to the YAML language as a whole.
Do not mistake a successful Lean #guard evaluation for a kernel theorem
establishing source-intent fidelity. The original separately imported Lean
theorems establish only their explicitly declared scopes.

## Reproduce locally

Download the two exact ZIP artifacts from the Actions links above, then:

    python -m mathgraph_check.public_receipts \
      --v1-zip path/to/l4yaml-v1.zip \
      --v2-zip path/to/l4yaml-v2.zip \
      --out public/mathgraph-check

For the local read-only HTTP preview:

    python -m mathgraph_check.public_http \
      --release-dir public/mathgraph-check --port 8796

Open http://127.0.0.1:8796/ in a browser. This **does not deploy** the
public MathGraph.org site. The live website, DNS and user accounts are
unmodified; the branch's Actions run publishes a downloadable preview artifact.

## Smallest useful agent interface

A GET of /v1/records/mg-l4yaml-source-check-20261010 yields the exact frozen
record. GET /v1/records/mg-l4yaml-source-check-20261010/evidence yields the
source receipts. GET /v1/badges/mg-l4yaml-source-check-20261010.svg returns a
**neutral, explicitly scoped** badge reading "48/48 source cases".

A read-only POST to /v1/resolve:

    curl -s http://127.0.0.1:8796/v1/resolve \
      -H 'Content-Type: application/json' \
      -d '{
        "record_id":"mg-l4yaml-source-check-20261010",
        "source_commit":"62bf7077910e888a0bc8adfc8e08a5f500ff3ca3",
        "external_suite_commit":"da267a5c4782e7361e82889e76c0dc7df0e1e870",
        "goal":"finite_parser_acceptance"
      }'

returns "WARRANTED_BOUNDED" only for **exactly this** source and case scope;
the separate "recursive_anchor_behavior" goal returns the known source-bound
semantic separator. Any new version, broader problem or unsupported goal
returns **UNKNOWN**, not a guessed proof. See GET /v1/openapi.json.

No verifier executions, source fetching, network calls or repository writes
are triggered by agent queries. The WSGI preview binds only to loopback,
and query bodies are bounded to 8 KiB.

## Product design rules

- Page: restrained, accessible, responsive typography; readable evidence
  rather than animation or graph visualization.
- Badge: source-bounded numerical status, never a universal truth seal or
  implied JPL/NASA/Palomar endorsement.
- Ledger: original mislabelled YAML "fail" metadata and undecoded 26DV:0
  whitespace remain visible as negative development lineage.
- Meaning: proof truth, runnable checks, source fidelity, human digestion
  and generalization remain independently qualified.
- Longevity: immutable historical snapshot, with requalification against new
  source versions explicitly NOT CHECKED.

## Remaining gates

A real hosted endpoint and static site cutover require explicit deployment
and independent tests of public access, permissions, cache expiry and uptime.
A mature continuously updated consequence graph requires dynamic source change
tracking and revocation/reclosure. A verified general NL-to-Lean source fidelity
service requires real external source interpretation and independently measured
baseline outcomes. Nothing in this MVP claims those are already complete.

No upstream JPL changes, PRs, issues, mentions or messages have been made.

## Standalone integration branch

This isolated release PR is based directly on the existing MathGraph `main`,
not on the experimental Navier/JPL stacked research PRs. It deliberately
contains only the two dependency-free public evidence modules, release
checks, documentation and exact-archive CI. Unlike the research prototype,
the record integrity gate also pins the **expected published record hash**:
even an attacker who recomputes a JSON object's self-hash cannot change its
48-case scope while preserving its status as the qualified snapshot. Future
new records will require new independently verified release commitments.
