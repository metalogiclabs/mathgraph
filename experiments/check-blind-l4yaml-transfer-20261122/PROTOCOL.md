# MathGraph Check: prospective blinded L4YAML transfer experiment

Status: **CANDIDATE / NOT_RUN**. This file establishes the test boundary, not a discovery claim.

## Question

Can MathGraph Check discover a previously undisclosed claim/evidence mismatch
in a frozen L4YAML revision, without receiving the known failure witness,
the repaired patch, or the evaluator's expected result?

## Separation

- Investigator input: a pinned clean repository checkout, its public requirements,
  ordinary build/test instructions, and a fixed 104-prompt catalogue.
- Investigator must not receive: private holdout cases, historical defect descriptions,
  repair commits, or any evaluator labels.
- Evaluator: independently runs every submitted reproducer against exact source
  and separately determines whether it was already publicly documented.
- If the investigator has access to prior L4YAML audit context or the public
  history containing the defect, **do not call the result blind**. Record
  contamination explicitly and downgrade to a non-blind transfer evaluation.

## Pre-registration

Before investigation, freeze: source commit, catalogue commit, checker commit,
runtime/toolchain, allowed investigation time and calls, hidden witness identities,
and evaluation script hash. Do not change these after observing outcomes.

## Outcome contract

- WARRANTED discovery: a new, independently reproducible discrepancy against a
  stated requirement, with exact source revision, actual consumer, evidence
  artifacts, and a defensible novelty assessment.
- REJECTED candidate: the concrete proposed witness fails reproduction or
  contradicts the governing requirement.
- UNKNOWN: unavailable toolchain, missing source, ambiguous requirement,
  unexecuted candidate, or contamination that prevents the proposed blind claim.
- NOT_RUN: no investigation performed.

Record false positives, UNKNOWNs, time/cost, and all attempted candidates,
including failed ones. Report no detection rate from one repository.

## Minimum next experiment

1. Select and freeze a revision **not used in the five retained qualification
   profiles**; exclude their exact fixtures and all previously known witnesses.
2. Have a separate evaluator commit holdout identities and checksums before
   investigator execution.
3. Run the unchanged MathGraph Check against that frozen revision.
4. Preserve complete tool invocation, raw observations and case provenance.
5. Independently replay any candidate against actual consumers.
6. Compare with existing CI, and document whether ordinary checks already
   reported the same discrepancy.

## Important constraint

The existing MathGraph Check is a finite profile replay command, not an
autonomous general-purpose investigator. Without an explicitly defined
investigation procedure or operator, a zero-new-finding outcome cannot
measure autonomous discovery ability. The prospective trial must not
relabel known fixture replay as discovery.
