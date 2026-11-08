# MathGraph Check signed projection review — bounded admission design

## Purpose

A self-computed hash of a proposed claim does not make it independently
reviewed. Supply a verifiable boundary between an untrusted candidate
observation collision and an independently approved finite claim packet.

## Approaches

1. **Chosen:** a small read-only Ed25519-signed review envelope checked against
   an out-of-band trusted reviewer public key. This makes review provenance
   machine-checkable without hosting or distributing secret signing keys.
2. A protected-host policy registry alone could provide the same boundary in
   one deployment, but cannot be independently checked if the packet leaves the
   host. Existing hosted expectations can continue using their trusted policy.
3. Recompute a SHA-256 from a PR-authored policy: rejected, because a producer
   can self-approve its own fabricated protected verdicts.

## Contract

- `admitSignedProjectionReview(subject,envelope,trustedKeys)` accepts an exact
  GitHub source subject, signed finite claim, review metadata and reviewer key ID.
- Review metadata must name a nonempty evidence reference and exact SHA-256
  digest. A signature covers the complete canonical claim, source subject,
  reviewer identity and evidence reference/digest.
- Public verification keys come from an out-of-band trusted host allowlist;
  neither the envelope nor its referenced code supplies their own trust roots.
- The admitted claim runs through `checkProjectionClaim` with exact source and
  finite-universe binding. A bad signature, unknown reviewer, changed source,
  missing receipt or finite non-collision remains `UNKNOWN`.
- A valid signature **attests reviewer approval of a particular finite packet**;
  it does not re-execute Lean, validate the referenced proof bytes, prove a
  universal positive theorem, or imply customer ownership of a requirement.
- Authenticated `githubSnapshot` may accept the separately supplied signed
  envelope and trusted keys. The authenticated current GitHub subject is
  authoritative; bad signatures produce an explicit UNKNOWN finding. Signed
  and existing raw host-policy injection cannot be combined in one readback.
- No webhook, first-party runner, published Check Run, deployment, or merge is
  changed in this slice. Production trust-pinning and proof-byte verification
  remain separate work.
