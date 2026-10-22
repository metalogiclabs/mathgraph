# V6 — contract-directed counterexample and evidence repair

## Qualified run
https://github.com/metalogiclabs/mathgraph/actions/runs/39724599787
Commit 2a87e6acd3d21b240644f37e148f3d28afae1b05. CI passed.

## Source and design
Pillow==11.3.0 ImageFile.Parser for an apparent successful observation, and designer-supplied PNG chunk CRC32 integrity predicate. Eight-state abstraction is not claimed. Diagnostic grammar frozen in experiment source: parser, parser + structure, parser + CRC, direct CRC contract. Images generated as 8x8 grayscale PNGs; training seeds 0..15, holdout 100..199 with intact, IDAT payload flip, IDAT CRC flip, and IEND CRC flip.

## Results
64 training cases. Parser and parser+structure each disagree with supplied contract 32 times. Parser+CRC and direct contract disagree zero times. Selected parser+CRC under ordered candidate grammar. 400 held-out classifications match the supplied contract. Withdrawing crc_check grant is modeled as returning UNKNOWN_NO_WARRANT; NOT demonstrated as a separately verified permission enforcement implementation.

## Epistemic boundary
WARRANTED: bounded counterexample-triggered selection of a more discriminating evidence combination, matching a supplied CRC integrity contract on declared synthetic train and holdout data.
REJECTED: universal claim that parser success alone proves PNG CRC integrity.
UNKNOWN: independently source-derived checksum semantics, sound authorization model, proof for arbitrary inputs, native transfer, efficiency advantage.
The contract oracle and the CRC feature use the same underlying zlib CRC computation, so their agreement is **not independent algorithmic verification**. The fully informed direct CRC baseline ties correctness and avoids repair search cost. The mechanism chooses from designer-supplied hypotheses, not unconstrained physical observation invention.

## Next decisive experiment
Freeze external-source contract extraction separately from candidate evidence construction; validate against an independently authored verifier and public mutation corpus; insist on source provenance, permission rejection, and full cost accounting. Counterexample preservation and evidence withdrawal should be verifiable by a checker that does not share the CRC function.
