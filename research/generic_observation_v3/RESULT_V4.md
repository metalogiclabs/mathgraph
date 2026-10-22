# Observation protocol V4 — qualified finite behavioral acquisition

## Objective and immutable precursor
V3 method-only admission remains unchanged (`frozen_admission.py`, commit `9d087d55e1f5a9665e750cde9785e9758b0ecd05`). V3 failed for Pillow with zero admitted methods, run #39698322525.

## New bounded capability
Protocol V4 enumerates all public Pillow ImageFile.Parser methods with <=1 required positional input and depth <=2 method sequences. Its grammar passes the synthetic PNG byte string to every single-required-argument method. It has no abstract safety or permission model. The user/designer preselected the PNG integrity task, library class, depth, input type, and damage generator.

## Evidence
GitHub Actions run #39700910090, commit `c7799efd8593baff660ea993296314f8fa050785`: SUCCESS.
- Old method-only rule `[]`.
- New grammar 3 candidate methods, 12 sequences.
- Unique winning sequence `feed → close` on eight training pairs.
- Intact trace: feed OK then close OK (PngImageFile); corrupted trace: feed OK then close ERROR (OSError).
- Held-out classifications 80/80 matched an independent PNG chunk CRC32 implementation.

## Epistemic states
WARRANTED (bounded): selected and exercised a short stateful observation protocol that separated this declared synthetic PNG class, with independent oracle agreement on 80 holdout observations.
REJECTED: V3 method-only transfer to the same interface.
CANDIDATE: reusable protocol-acquisition architecture.
UNKNOWN: safety/effect authority derived from source; correctness on arbitrary PNGs; decision sufficiency for more general defects; genuine independent scientific measurement; planner advantage.

## Crucial caveat
An exception from Pillow close is an empirical observation, not a soundness certificate. CRC32 of PNG chunks and successful image decoding are different predicates on general input; broader PNGs may make these disagree. No solver cost accounting or comparable fully informed planner was qualified.

## Highest-leverage next test
Derive protocol effect/permission constraints from pinned authoritative source, use operations with typed transitions and negative-effect controls, and compare a frozen search strategy with an equally informed exhaustive search. Test untouched third-party API with a verifier which does not import its parser.
