# V2 derived-channel falsification

This note records a failed stronger interpretation of V2 rather than retroactively rewriting V2.

## What was tested

V2's frozen schema allowed only raw-coordinate masks:

`BASE`, `Expose(x)`, `Expose(y)`, `Expose(x,y)`.

Within that schema, exhaustive enumeration correctly classifies the 256 Boolean targets as 4 / 12 / 12 / 228 and gives the minimal raw-coordinate mask for each target.

We then widened the observation grammar to **all 16 Boolean channels**

`h : {0,1}^2 -> {0,1}`

of the hidden pair `(x,y)`, and searched one-channel representations before two-channel representations.

## Result

For the 24 targets depending on exactly one hidden coordinate, the enlarged search always finds a one-channel observation behaviorally equivalent to the corresponding raw coordinate. There are 0 surprises.

For the 228 targets that V2 labels `Expose(x,y)`, the stronger claim fails:

- 60/228 are formable through a single derived Boolean channel;
- 168/228 require two Boolean channels in this enlarged grammar.

Therefore `Expose(x,y)` is not absolutely minimal for all 228 targets. It is minimal only relative to V2's declared raw-coordinate schema.

## Why this matters

This is not a defect to hide. It identifies the representation dependence in V2's notion of identity/minimality. Literal coordinates are too intensional: different observation functions can induce exactly the distinctions needed by the target.

That residual motivated V3, which removes named coordinate and derived-channel vocabulary from the developmental constructor and searches directly over quotient partitions. In that formulation the object is the induced distinction structure itself.

So the experimental lineage is:

`V2 raw-coordinate minimality`

`-> counterexample under wider channel grammar`

`-> quotient/partition identity`

`-> V3 coordinate-free coarsest refinement synthesis`.

This is the intended scientific interpretation: verified counterevidence changed the representation used by the next experiment.