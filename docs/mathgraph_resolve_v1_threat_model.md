# Resolve v1 threat model

This profile publishes one historical resolution snapshot and its exact inputs.
It does not accept arbitrary mathematical claims, proof programs, URLs, uploads,
mutation requests, or action requests. The website is a static publisher and one
consumer of the protocol; it is not a trust root or required runtime service.

## Trust roots and integrity

The Python consumer requires a separate trust policy and its expected SHA-256
from outside the bundle. The Node 24 reference client carries separately reviewed
authority constants for the exact policy, bundle, record, scenarios, and member
bytes. Recipients must obtain trustworthy consumer code and expected pins through
their own channel. Downloading code, policy, and hashes from one compromised host
does not authenticate any of them.

The catalogue and hosting publication are unsigned. TLS and GitHub commit/run
references provide transport/provenance context under a recipient's repository
and key policy; they are not publisher signatures. A self-hash establishes only
internal consistency. Both consumers reject a changed record even when an attacker
recomputes its self-hash. Catalogue fields cannot replace the reference client's
compiled authority pins. JSON bytes, decoded bundle-member lengths/hashes,
canonical payload digests, and fixed provenance are independently checked.

The exact OpenAI notice authenticates the pinned documentary withdrawal only.
It is not a theorem verifier. The JPL public receipt is accepted at its exact
48-case scope under the declared policy; neither public consumer reruns the
original JPL Lean build or proves that all YAML inputs behave correctly.

## Substitution, replay, and time

Source substitution, different commits, forged receipt/verifier identities,
nonempty assumptions, and scope changes are rejected. Unknown schemas,
semantic kinds, field extensions, bundle transports, and unqualified relations
fail closed. Duplicate JSON keys and non-finite numbers are rejected. A route
cannot silently generalize finite evidence or convert documentary support into
formal mathematical support.

Replaying retained historical evidence is intentional. It must never imply that
the result is currently applicable. A fresh HTTP response or cached immutable
file proves no absence of subsequent withdrawal, revocation, or supersession.
The catalogue may describe its own entry as current; that is distinct from
current applicability of the evidence. Both record-002 consumers report:

- historical evidence qualification under the pinned policy;
- independently calculated historical support resolution;
- current applicability `UNKNOWN`;
- freshness and revocation/supersession `NOT_CHECKED`;
- immutable historical lifecycle;
- no action authorization and no new original Lean replay.

Historical withdrawal removes only support that depends on withdrawn receipts.
Alternative routes can survive; rootless cycles cannot create support. `STALE`
does not mean `REFUTED`. The public HTTP profile has no refutation verifier and
cannot issue a `REFUTED` mathematical claim. The separate Python conformance
suite's checked finite countermodel is synthetic, outside this historical bundle.

## UI and execution boundary

Astro renders the static default. The explorer selects precomputed, pinned
scenarios and displays dynamic labels with `textContent`; it does not derive new
statuses, evaluate proof code, or execute content from the graph. CSP and
same-origin resource rules add defense in depth. They do not make an XSS or host
compromise harmless, so consumers must not use the display as their authority.

The published TypeScript file is a local client, not a public service. It fetches
fixed paths from an explicitly supplied HTTP(S) origin, rejects credential-bearing
or path-bearing origins, rejects redirects, and applies response time/size limits.
It does not follow URLs supplied in untrusted evidence to arbitrary destinations.
It reads no credentials and performs no write, promotion, deployment, or message
operation. Fetching an origin chosen by a local user is not a server-side fetch
endpoint. No arbitrary execution or fetch feature is exposed by the website.

The Python three-file replay performs no network calls, but running the script
alone does not prove isolation. Qualification uses an OS deny-network sandbox
or a network-disabled container with an explicit negative connectivity probe.
Only the three input files are copied/mounted, alongside the trusted runtime.
The separate Node HTTP test intentionally has loopback network access and is
not an offline-isolation proof. Neither client authorizes downstream agents to
act on a historical status.

## Retention, reporting, and residual risks

Immutable evidence remains available for audit even when support is stale.
Corrections require new versioned evidence and explicit lifecycle treatment;
existing bytes and their recorded identity must not be silently replaced.
The canonical small bundle is retained in Git; bulky execution/build artifacts
remain external, with CI identities and hashes recorded as provenance.

This release does not establish a dedicated private security-reporting channel
or a response SLA. Contact repository maintainers to arrange a private channel
before sharing sensitive findings. A useful report identifies the exact commit,
artifact digest, affected boundary, expected versus observed outcome, and a
minimal non-sensitive reproduction. Do not include credentials or private data
in public issues. Reports themselves are unverified inputs until checked.

Residual risks include compromise of the trusted consumer/runtime or pin channel,
unsigned catalogue/host metadata, unavailable upstream CI artifacts, stale
external lifecycle information, shared ownership of producer and consumers,
implementation bugs, and resource exhaustion before or during parsing. Network
and input-size limits reduce some costs; they do not prove general denial-of-
service resistance. No signature, generalized semantic transport, autonomous
trust service, outside-organization adoption, or continuous monitoring is claimed.
