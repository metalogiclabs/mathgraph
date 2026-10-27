# Autonomous source-only separating-observation experiment

Preregister first, unblind later. This technical protocol is public,
but contains no private collaborators, strategy, correspondence or plans.

Five independent source-authored ACSL contracts are selected from a pinned
C-to-verifiable-Rust repository, before inspecting Qwen target bytes.
The targets were checked only for path existence.

MathGraph's deterministic **source-only** extractor recognizes narrow ACSL
behavior/result families (present vs absent, including Boolean 0/1 and
index/sentinel contracts), discovers sortedness and declared minimum length,
and constructs a maximum of three separating observations per source.
It must **abstain** rather than guessing on a contract it cannot read.
The original C executable remains the reference; independent contract
predicates bound which results may be authorized.

After this source-only commit, lock the generated probe set and result schema
before opening target code. Test every authorized input exhaustively within
the declared small domains, and separately test only the sparse probes.
A strong conventional differential reviewer sees the same C, target,
constraints and executable evidence and can flag identical defects.

Positives (correctly preserved contracts) and negatives (target-specific
counterexamples) both count; unsupported contracts and non-executable
generated targets are UNKNOWN, not defects. Observe runtime output and
source mutation without changing upstream. A source-generated probe is not
a proof of completeness. Economic advantage is UNKNOWN unless measured.
