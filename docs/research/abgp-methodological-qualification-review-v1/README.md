# A/B/G/P Pre-Freeze Methodological Qualification

**Metalogic Labs review candidate** - qualification of the experiment mechanics only, not confirmatory scientific evidence.

**Status:** `QUALIFIED`  
**Confirmatory namespace used:** `0`  
**Full regression:** `200/200` tests

## Current review candidate

| Arm | Inferential unit / dependence | N | Floor | Minimum qualified power |
|---|---|---:|---:|---:|
| A | Independent acquisition -> sealed-future episode | 4,096 | 5 pp | 0.825254 |
| B | Ordered-direction world; 4 interventions nested | 1,015 / direction = 12,180 total | 15 pp | 0.800598 |
| G | Independent world; all doses jointly blocked | 421 | 15 pp | 0.801242 |
| P | Independent acquisition -> restart -> future episode; 4 fixed probes collapse to one episode outcome | 4,096 | 5 pp | 0.825254 |

## What changed before freeze

- **A:** fixed-language Bayes receives the same acquisition information; the verifier message remains non-identifying; the sealed future is independently seeded and has no verifier access.
- **B:** the 12 ordered grammar directions are separate strata. Four interventions are nested within each world. The arm is an intersection-union test over 12 directions x 3 controls = 36 component hypotheses; the arm p-value is the maximum component p-value.
- **G:** one relevance-label exchange is applied per world jointly across all nonzero doses. The exact world-blocked DP was independently cross-checked against brute-force world-level sign enumeration.
- **P:** one independently seeded acquisition is one inferential unit: acquire -> serialize -> hard restart -> four fixed held-out future probes -> one binary episode outcome. Nested probes never increase N.

## Power provenance

The larger counts were **not** selected because DEV showed a weak effect. They come from a pre-freeze qualification rule: at least 80% power at the preregistered minimum effect floor over the full feasible discordance envelope, using component alpha = 0.0125.

B uses a dependence-agnostic union-bound lower bound for simultaneous success of all 36 IUT components. G uses a deliberately conservative model in which lower doses contribute zero signal and power is guaranteed from the maximum-dose floor alone.

## Qualification evidence

- Frozen fixtures: **21** total - 4 planted-positive, 13 ordinary-explanation, 4 broken-mechanics.
- Fixture result: **all 21** matched their preregistered expected verdict.
- Independent statistical reference: **PASS** - McNemar, Holm, legacy G DP, and world-blocked G DP cross-checks.
- Qualification digest: `e1e01c892e1006bc68b507865a429a733a168cb3156e57815ba57dac6c6a9206`
- Qualification JSON SHA-256: `4e69329d127381661cc6ce49fffdbecc5c84e621efe0ba7efdbbd43d81517bcf`

## Review target

Please attack the inferential-unit definitions, dependence assumptions, and power calculations before freeze - especially any hidden shared ancestry in A/P, the B IUT construction, or the G world-level exchangeability argument.

The design remains `REVIEW_PENDING` and confirmatory execution remains disabled. A later confirmatory run would be a separate event and is not represented by this review package.

## Audit binding

The qualification digest and canonical qualification-JSON SHA-256 above bind this review note to the exact qualified artifact. The canonical JSON can be supplied separately if a line-by-line audit is useful; no personal-repository URL is required to review this package.
