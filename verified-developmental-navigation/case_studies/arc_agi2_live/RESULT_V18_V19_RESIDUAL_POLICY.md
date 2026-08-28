# ARC residual-induced query policy — V18 to V19

## Frozen source and boundary

- ARC-AGI repository commit: `399030444e0ab0cc8b4e199870fb20b863846f34`
- Frozen tasks: `0c786b71`, `59341089`, `833dafe3`, `be03b35f`
- Candidate observation language: cumulative V17 language only
- Query budget: 8 per task
- Future verifier: exact one-step continuation audit inherited from V13
- No continuation search truncation in V18, V18b, or V19

## V18 — residual-induced query synthesis

The constructor receives only a verifier-returned unresolved positive/negative future collision. It may choose any executable observation atom that separates that pair. Atom order and tie-breaking are frozen.

Result:

- true residual: exact future quotient on 3/4 tasks
- held-out exact: 3/4
- no residual: 0/4
- shuffled residual: 0/4
- oracle ceiling: 4/4

On `be03b35f`, V18 reduced unresolved positive/negative future-conflicting pairs from 744 to 12 within the 8-query budget but did not close the quotient. Oracle required 7 queries.

Interpretation: real verified residuals causally guide useful distinction acquisition, but arbitrary choice among current-pair separators can waste query budget.

## V18b — generic active separator control

V18b adds no concepts, labels, or query budget. Among atoms separating the current verifier-returned collision, it chooses the atom maximizing the unlabeled `n0*n1` split of the current observational bucket.

Result:

- exact future quotient: 3/4
- `be03b35f`: 41 unresolved pairs after 8 queries

This is worse than V18's 12 unresolved pairs on the same task.

Interpretation: generic observational information gain is not equivalent to developmental value. A query can split the current state bucket well without efficiently resolving distinctions that determine verified futures.

## V19 — residual-history induced query policy

V19 retains only the ordered history of verifier-returned collision pairs. No global future labels enter query ranking.

At each step:

1. the verifier returns one unresolved positive/negative future collision;
2. candidate atoms must separate the current collision;
3. candidates are ranked by how many previously returned residual pairs they would also have separated;
4. residual-signature diversity is a secondary score;
5. SHA-256 is the deterministic tie-break.

The sham arm applies the same algorithm to a deterministic index-permuted residual history.

### Exact result

| task | V18 | V19 learned history | V19 sham | oracle |
|---|---:|---:|---:|---:|
| `0c786b71` | exact / 5 q | exact / 5 q | exact / 6 q | exact / 5 q |
| `59341089` | exact | exact / 3 q | exact / 5 q | exact / 2 q |
| `833dafe3` | exact / 5 q | exact / 5 q | exact / 6 q | exact / 5 q |
| `be03b35f` | fail / 12 residual | **exact / 7 q** | fail / 6 residual | exact / 7 q |

Summary:

- learned residual history: **4/4 exact**
- learned held-out: **4/4 exact**
- sham history: 3/4 exact
- V18 first-separator baseline: 3/4 exact

Strict gate:

`PASS_RESIDUAL_HISTORY_INDUCES_QUERY_POLICY`

On the previously unresolved task `be03b35f`, V19 closes the quotient in exactly 7 queries, matching the oracle query count, while the deterministic sham history still fails after 8 queries.

## What is established

Within the declared finite ARC carrier and frozen observation language:

1. verified future collisions force nontrivial distinctions;
2. true residuals guide distinction acquisition better than absent or shuffled residuals;
3. generic bucket-balancing information gain is insufficient;
4. retaining the history of verified residuals changes which future questions are selected;
5. that retained history closes a task the memoryless policy cannot close under the same query budget;
6. targeted corruption of the history restores failure on that task.

This supports the developmental transition

\[
\rho_t \to H_t \to q_{t+1}
\]

where `H_t` is not a hand-authored semantic concept but the retained history of verifier-returned residuals.

The next causal question is whether this learned query policy transfers to a source-distinct task family or changes later constructor discovery under a frozen constructor budget. V19 does not yet establish that stronger cross-episode compounding claim.
