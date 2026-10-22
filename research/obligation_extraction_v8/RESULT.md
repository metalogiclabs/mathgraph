# V8 prospective unfamiliar source — negative result

Frozen rule commit: `08f9ad82e1888cb397a263ecb88e864f6f104478` BEFORE selecting RFC 8259 target.
Target: RFC 8259 plain text from `https://www.rfc-editor.org/rfc/rfc8259.txt` SHA256 `61a5378f4255c720beb2a4b4a63b29540147c140f36988bf086291989b4cd2d7`.
GitHub Actions: https://github.com/metalogiclabs/mathgraph/actions/runs/39778372931 (SUCCESS = asserted expected obstruction, not successful extraction).

Source contains `MUST be encoded using UTF-8`, `MUST NOT add a byte order mark`, `MUST be lowercase`. Frozen extractor recognized **zero** obligations. No repair was built. The new source was identified after grammar freeze; target assertions and test harness were written after source selection, so this is not an independently administered blind test.

Epistemic states:
- WARRANTED (bounded): frozen presence-oriented rule did not recognize the tested normative obligations; the test documents the mismatch.
- REJECTED: universal claim that the V8 rule autonomously extracts arbitrary standards obligations.
- UNKNOWN: automatically learning typed obligations from unfamiliar specs, source-derived check synthesis, full authority/permission propagation.

Lineage: V7 CRC success on manually selected PNG source excerpt -> V8 unrecognized RFC 8259 rules. Do NOT supersede V7's bounded successes. Do NOT retune V8 and report retuned success as if it were blind.

Next cheapest decisive experiment: add *predeclared* typed obligation constructors (presence, prohibition, lexical format, equality), proof-check rule parsing with negative controls (MUST NOT, conditional clauses), freeze them before another genuinely unseen source, and require a separately implemented data checker and source withdrawal.
