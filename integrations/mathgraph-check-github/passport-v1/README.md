# MathGraph Check Assurance Passport

A standalone interactive report for the bounded group-identity GitHub App demonstration. It uses the MathGraph design shell and embeds all required data, styles and verification code; no package install or model API calls are required.

Run `node --test passport.test.mjs` and `node build.mjs` in this directory. Open `dist/MathGraph_Check_Passport.html` in a JavaScript-capable browser. Optional public GitHub head refresh requires network access; unavailable or expired observations remain unknown.

## Evidence and trust boundary

`trusted-manifest.mjs` pins 24 file digests separately from mutable input data. Twenty-three files are public Git blobs from evidence commit a07a6300b71ba9bafa64a0d09abac20d5a15655e, including the native transfer matrix. The remaining file is a dated operator readback of public PR heads, not part of that historical commit. Build verifies the public blob hashes and the fixed SHA256 manifest before issuing a report.

The report checks integrity and consistency of retained records. It does not execute Lean again, authenticate the issuer cryptographically, or certify arbitrary mathematical claims. Editing the verifier or its reviewed pins is outside the input-integrity boundary. Independently compare source and generated-report digests when distributing it.

The qualified repair is PR #245 from source PR #242. PR #243 is a separate negative/withdrawal control. Historical verification and present source applicability are separate states. Live head observations expire after five minutes and are reassessed on rendering, focus and visibility return.

Four constructed group identities were repaired in a finite native matrix; predictions matched 10/12 because two anticipated repairs already compiled. No autonomous learning, general repair capability or model advantage is claimed. Human review decides merges.

## Validation

Six Node tests cover retained receipts, missing or tampered input, forged proof with regenerated manifest, wrong bindings/axioms/model-call assertions, stale or malformed source observations, and independent SHA256 vectors. Desktop browser checks exercised source refresh, proof details, pasted changed-proof rejection and restoration. Responsive layout was inspected in a 390×844 iframe (375 CSS-pixel content width), not on a physical phone. The optional refresh displayed matching observed heads for #242/#245 and a changed source for #243.
