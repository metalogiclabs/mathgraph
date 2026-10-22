# ECRot Brandenburg source alternative evidence

**Retrospective source audit, not a visual navigation result.** Original ECRot Brandenburg second scene was frozen as a different-scene holdout before acquisition but is now exposed. Its original ROS1 bag SHA256 is 3d8e3284670c94b52919228c2a133586e8e592c07f3a6e1e127fee6acd747455; verified in https://github.com/metalogiclabs/mathgraph/actions/runs/39870666780.

Five timestamp groups repeat. At least one equal-time pair has different serialized IMU data, so deleting “duplicate samples” on timestamp alone is unjustified. The companion exact-source auditor preserves all observed y-gyro readings per timestamp. For positive time increments, the minimum/maximum source observations give exact bounds on trapezoidal integrated gyro angle at every prefix. A separately formulated exhaustive oracle computes the same extrema by enumerating all possible recorded-source choices.

If every source-allowed signed gyro prefix is below 2*pi in magnitude, the dataset is REJECTED as evidence of even one complete gyro-estimated first revolution. This is a bounded model of source-reported choices, not a physical gyro error bound. Neither physical heading, camera–gyro synchronization nor flight hardware has been verified. Both a conventional and evidence-aware matcher may use the same source gate; MathGraph superiority remains UNKNOWN.

No later observations or true headings are used to choose candidate rates. All negative outcomes are retained, with correction authorization permanently withheld for this source audit.
