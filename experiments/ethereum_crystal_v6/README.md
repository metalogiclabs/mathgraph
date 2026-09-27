# Ethereum Crystal v6 — executable EELS gate

V6 closes the gap between source-derived EIP-7928 family transfer and actual execution of Ethereum's official test suite.

CI checks out the pinned EELS commit, installs its declared test environment, and executes selected official EIP-7928 tests covering the same semantic families used by Crystal v4/v5. Only after those tests pass does CI requalify the Crystal developmental and held-out-transfer gates.

This does **not** yet mean Crystal consumes serialized BAL fixtures directly. It establishes a chained evidence boundary:

`official executable Ethereum semantics green → Crystal acquisition green → held-out family reuse green`.

If the official test selection cannot execute at the pinned commit, V6 fails rather than falling back to source inspection.


## Integration residual update

The canonical EELS `fill` runner has now generated the selected Amsterdam EIP-7928 fixtures successfully (40/40 at the pinned commit). The next gate is schema discovery over those realized JSON artifacts followed by direct Crystal ingestion. A prior run stopped only because the inspector file was added one commit after the workflow began; that failure is infrastructure lineage, not semantic evidence.
