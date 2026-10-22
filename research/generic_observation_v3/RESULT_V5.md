# V5 — semantic sufficiency falsifier

The V4 source-protocol search found `feed -> close` and classified 80/80 holdout samples from a narrow corruption generator. The broader inference that successful parser close certifies PNG chunk CRC integrity is **REJECTED**.

V5 creates 40 seeded images and three variants per image: intact; ancillary tEXt with wrong CRC; IDAT with wrong CRC but unchanged payload. A separate chunk parser recomputes all CRC32 fields; Pillow 11.3.0 ImageFile.Parser executes feed -> close as the tested candidate observation.

The local test found 40 false accepts for corrupted IDAT CRC and no mismatches on 80 other examples (40 intact and 40 ancillary-bad-CRC). This is a concrete separating counterexample to the proposition that parser success implies all chunk checksums are valid. The independent CRC oracle is structurally separate from Pillow and does not invoke its parser.

Epistemic states:
- **WARRANTED**: bounded V4 classifications for the original corruption family, and V5 counterexample on this tested runtime after CI passes.
- **REJECTED**: claim that V4's observation alone certifies global PNG chunk CRC integrity.
- **UNKNOWN**: fully source-authorized and effect-certified autonomous protocol synthesis.

No superior planner cost, physical measurement discovery, universal parser soundness or independent professional security review is claimed. The fully informed conventional CRC scanner is at least as sound on this declared task and does not require a method-selection search.

Research consequence: a decision-sufficient observation is warranted only after **semantic coverage** is independently certified relative to a source-authoritative goal, not merely observational discrimination on finitely many training examples. V4's selection remains real but its decoder cannot be promoted to an unbounded integrity claim.
