# V3 precommit — ARC-AGI-1 reachable-regime transfer

V1 and V2 on the pinned ARC-AGI-2 public evaluation set found **zero demonstration-consistent programs** in the frozen bounded languages. That is an informative representation obstruction, but it makes a routing comparison vacuous: if no continuation is reachable, family ordering cannot matter.

V3 therefore holds the V2 language and routing mechanism fixed and transfers them unchanged to the older ARC-AGI-1 benchmark, pinned at commit `399030444e0ab0cc8b4e199870fb20b863846f34` (400 training, 400 public evaluation tasks). The purpose is not to claim ARC-AGI-1 state of the art; it is to test the navigation mechanism in a real regime where the bounded language is expected to have nonzero reach.

Prospective boundary: routing is learned only from the 400 ARC-AGI-1 training tasks. Evaluation test outputs are used only after commitment, for scoring.

Primary navigation criterion remains unchanged: VDN must not reduce exact solve count relative to the global learned order and must reduce total verifier candidate checks on tasks solved by both arms.

The V2 fallback extension `structural_then_recolor` remains frozen. A developmental phase change requires at least one exact evaluation solve unavailable to the frozen base language, with no loss of base-reachable exact solves.