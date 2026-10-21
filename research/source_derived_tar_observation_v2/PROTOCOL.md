# Source-derived TAR observation — V2 qualification boundary

## Objective
Transfer V1's bounded observation selection from ZIP to a new source, without hard-coding the winning API method name.

## Source
CPython tag v3.13.7; `Doc/library/tarfile.rst` (Git blob SHA `5532ffa1ad27f57765c3d18b55ece72f4e579e19`). Qualified run SHA-256 for retrieved documentation: `4583c05650270e76281708abb98f6f6fd32292a39cc845d594d7d569e3aa3474`.

## Outcome
Workflow #39686895735 PASS, commit 3551338. Parsed candidates `getmembers`, `getnames`; separation 10/10 vs 0/10 respectively. The selector chose `getmembers`; 100/100 held-out classifications matched an independently implemented USTAR-header oracle. Removing the chosen observation grant reestablishes an obstruction in this constrained grammar.

## Declared limitations / non-claims
- Source-admission pattern **is domain-specific** ('Return the members'); not independently synthesized from generic API contract semantics.
- The task (executable bit), paired synthetic observations, and safety rule are designer-chosen.
- The admitted call is run on generated in-memory archives; this is NOT a proof of observational purity for arbitrary objects or external systems.
- The oracle is independent of the selected tarfile API but the test oracle and selection are checked within one CI job, not independently authored jobs.
- Only two methods are admitted; constrained exhaustive search wins with identical cost.
- This is NOT a physical sensor discovery, scientific finding, novel theorem, or commercial superiority demonstration.
- Access is to the pinned docs but runtime interpreter 3.13 is pinned by minor version, not the exact upstream patch version.
- No authority semantics or data permissions were mined from the external source. Permission withdrawal is a modeled control.

## Evidence status
WARRANTED: bounded source-informed API selection/heldout transfer within reported grammar.
CANDIDATE: automatic discovery of a useful operation on a genuinely unfamiliar third-party API.
UNKNOWN: source-derived permissions and safety proof, unanticipated primitive acquisition, planner advantage, transfer without targeted documentation string.

## Cheapest decisive next experiment
Freeze a domain-agnostic parser on a separate branch and pre-register a new source and target after the parser is frozen. Require source-grounded effect/permission classification and negative-control APIs; independent verifier and informed baseline. Reject automatic-acquisition claims if source-conditional parsing rules or intervention templates are hand-tuned after target revelation.
