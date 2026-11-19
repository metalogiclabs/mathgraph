# RFC 9484 / connect-ip-go source-native finite trial — verified outcome
Date: 2026-11-20 NZDT. Research scope only; external adjudication and competitiveness remain UNKNOWN.

## Provenance
- Source-side selection: OSS-Fuzz v0.5 frozen sample rank 4, selected repository quic-go/connect-ip-go.
- Normative input: published RFC 9484 §4.7.3, https://www.rfc-editor.org/rfc/rfc9484.html#section-4.7.3, only the declared route ordering/overlap subset. Case choice occurred **after source inspection** and is not a blind discovery trial.
- Native source: quic-go/connect-ip-go@9ee608a68fbbc6c377d13da4df2a269580b78909; capsule.go Git blob 45ca29b4eff3b59deb44e1dbcd1757a7948568fd. Original tracked source was not modified.
- Freeze: protocol commit 90b2f9f6a005c8aeb04f02383543f12baeccc29e (before new native trial).
- First exact-source native CI: https://github.com/metalogiclabs/mathgraph/actions/runs/44629860917 at 68bbe462702843903f639c8fad358fe3dbb82e02 — SUCCESS.
- Expanded unique-domain + diagnosis-controls CI: https://github.com/metalogiclabs/mathgraph/actions/runs/44630445619 at afc055ad905868cb404bd628a58b82bb35f2f60d — SUCCESS.
- CI artifact #14581580737 ZIP SHA-256 independently rehashed: d555fcfaf602bf4f934ae9c824bc56763d9a90cb4a466dae71e04737c3ec009b.
- Oracle JSON SHA-256: f348a61ed431b7edf168024f2cf6c53762bd18fdf3b069eade6ff28ace1d0224. Its intentional mutation was rejected by checksum. Neither hash authenticates an owner or establishes independent requirement interpretation.

## Exact evidence
- Finite inputs: 10,337 evaluations of which **9,924 are distinct route lists** (413 repeats among the LCG-produced three-route examples); both counts must appear in summaries.
- 8,664 MUST_ABORT structural violations: original Go validator and original capsule wire parser rejected all.
- 1,387 structurally valid positive controls: original Go accepted all (not an RFC obligation to accept all policy-compatible advertisements).
- 286 IP-protocol-zero overlap cases: original Go rejected all; RFC permits the receiver to validate this condition optionally, so these are **NOT false-positive defects**.
- Original upstream Go test suite passed. Source SHA and original capsule.go blob checked before and after native run. Only an untracked external test helper was temporarily added to CI checkout.
- Pairwise conventional reference checker **TIED 10,337/10,337** oracle labels; no independently staffed reviewer, no hidden answer or measured reviewer time.
- Four investigator-authored synthetic diagnostic controls PASS: protocol-field omission shows a consequential loss witness; deliberately wrong decoder despite full source shows fidelity failure; both mechanisms can coexist; irrelevant debug-label removal is harmless. Conventional scripted diagnosis TIED 4/4. These are **not actual upstream defects**.

## Trust and interpretation boundaries
- The primary tests directly invoke the original native Go route validator and parsing functions. Parsing errors are used as a *proxy* for abort; the full HTTP request-stream abort contract was NOT executed or warranted.
- Study oracle was derived from published RFC by MathGraph investigators; no two independent domain experts approved the interpretation. G1 independently adjudicated requirement is **UNKNOWN**.
- Strong conventional *human* baseline, blinded adjudicator, seeded-case authorship independent of MathGraph, prospective first discovery, full human/compute cost comparison and generalization are **NOT_RUN/UNKNOWN**.
- No defect from this trial was shown. No novel upstream issue, PR, owner-approved repair or production deployment has been claimed.
- This test does not evaluate a general typed-traversal strategy against conventional adaptive planning. A scripted tie is an informative negative, not a unique MathGraph benefit.

## Decision
WARRANTED_BOUNDED: exact historical native finite behaviour and archive identity.
CANDIDATE: a reusable source→representation→decoder diagnostic profile and four synthetic repair classifications.
UNKNOWN: independent human P interpretation, authentic request-stream abort, full specification conformance, method superiority, new discovery and operational action authority.

Next decisive experiment: have two independent protocol experts adjudicate one exact RFC requirement, appoint a qualified external conventional investigator, run a *held-out* source-native test with independently authored mutations, total measured costs and arm-blind repair-class scoring. Do not reuse this exposed test as a blind third-domain win.
