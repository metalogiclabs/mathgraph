# Property Preservation V2 — preregistration before checker implementation
Date 2026-10-21. Real source-changing resolver branch ancestor 8b09eaeabb0fc4801d7b974c500ec02dcecb3feb; production change originated at a47e4b9. Preserve production change and all production tests unchanged.

## One precise goal
Can an independently authored, SMALL, source-identity-bound equivalence checker warrant preservation of the **single evidence_is_live Boolean predicate** for every finite set of route evidence and qualified relation verifier receipts, without running the conventional broad Python regression?

This is property-specific. It does NOT establish whole resolve_graph correctness, every possible Python input, release safety, GitHub merge authorization, or a verified R7.2–CLC cross-language adapter.

## Frozen source shape and independent proof obligation
Old module Git blob ab4fc71cb90ee5c1c7435f0f32643673c0ee49d8 in main e48f094fa400c77ab07404645f6e12cfba7ebf45. New exact module blob 85de97a95f225ad564feb29faec24ce67f3f2e0e on research branch. Require byte-for-byte equality of full modules except previously reviewed evidence_is_live function. Reject any other change or unanticipated AST side effect.

Predicate contract for admitted, validated routes:
live = (ALL route evidence not withdrawn) AND
       (if no relation, TRUE; if relation, verifier not withdrawn AND ALL relation evidence not withdrawn).
All evidence receipt IDs are in externally validated scope. The checker does NOT attest source evidence authenticity.
Construct an independent, declarative truth table over all Boolean assignments for up to 3 route evidence, 1 verifier and 2 relation evidence, plus no-relation cases. Assert original and changed local implementations match contract for EVERY assignment, AND source edit is precisely the allowed replacement. Reject malicious mutation including 'ignore withdrawn evidence'. This exhaustive Boolean-domain theorem is finite and may be extended to arbitrary tuple lengths only with an independent inductive argument (NOT claimed here).
No unchanged tests should be edited or skipped silently.

## Decisions and fair baseline
Scoped protected decision only: WARRANTED_BOUNDED_LIVENESS_PREDICATE_PRESERVATION for finite enumerated cases + exact reviewed source rewrite. Requires code identity, independent contract checker pass, and policy receipt through real MathGraph resolve_graph in documentary scope. Withdraw either source authority/checker/policy -> UNKNOWN; independent claim remains.
Full app review/release stays UNKNOWN because broad suite deliberately not admitted in the candidate path.
Strong conventional baseline: EXACT same pinned fixtures and 5 same-machine repetitions of original broad targeted test suite (conformance/protocol_v1, conformance/resolve_v1, resolve publication, warrant core, living-warrants). Candidate: 5 repeats of checker IN SEPARATE fresh Python processes, excluding setup cost equally. Charge code identity/import/CI process and native checker time. Favor conventional if candidate slower. These test different scope; any measured time win must say PROPERTY-SCOPED ONLY, NOT full-suite replaceability.
After timing, independently run broad suite ONCE to verify changed source isn't currently contradicted; that run is a postdecision audit, counted separately and never hidden when making full-process cost statements. No claim that broad suite can safely be skipped for product release until higher-level preservation theorem and release authority.
If qualifying fixtures missing, FAIL-CLOSED; use existing offline pinned acquisition (history and two JPL zip artifacts) without altering requirements.
R7.2/CLC native old proven bridge remains unchanged; no re-proof needed.
