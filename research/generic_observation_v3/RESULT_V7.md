# V7 source-contract CRC evidence repair — LOCAL result, CI NOT QUALIFIED

Source authority: W3C PNG Third Edition https://www.w3.org/TR/png-3/ section 5.3 (chunk CRC covers chunk type and data, not length; present for every chunk) and 5.5 (reflected CRC-32). This is a bounded manually excerpted requirement; generic automatic extraction was not demonstrated.

Local experiment: 80 training cases (20 seeds x intact, IDAT payload corruption, IDAT CRC corruption, IEND CRC corruption); 400 holdout cases (100 distinct seeds x four types). Pillow parser vs bitwise CRC verifier showed 40 training mismatches. Repaired zlib.crc32-based chunk checker agrees with separate independently implemented bitwise reflected CRC-32 evaluator in all 400 holdout cases. No source-code algorithm is shared between verifier CRC loop and zlib CRC implementation. The harness, contract excerpt and tests remain authored together, so independence is limited.

Evidence run: local Python execution, not independently reproduced on GitHub Actions. Executable package exists in conversation artifact mathgraph_v7_source_contract.zip. This GitHub note does not substitute for code or a CI artifact.

Statuses:
- WARRANTED locally: test outcome under declared generated PNG corpus and source excerpt.
- CANDIDATE: source-authoritative obligation extraction and repair for arbitrary real APIs.
- UNKNOWN: provenance-authenticated automated specification parsing, autonomous construction of a checker, general PNG conformance, held-out untouched third-party transfer, source-authorized effect permissions, economic planner superiority.
- REJECTED: inference that Pillow parser acceptance certifies PNG-wide CRC integrity (V5).

Next experiment: commit source-pinned full standards snapshot digest and executable, run separate verifier on a frozen holdout corpus, then test source-clause withdrawal or mutation to ensure decision warrant retracts. Compare total search/checking cost against a directly informed CRC baseline.
