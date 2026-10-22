# V5: first-revolution coverage, conflicting captures and cautious acquisition

**Research state:** candidate, synthetic only. V4 C99 qualification remains
frozen at commit `c71bc0131e530cb5702508e6166fa1cf26d32ece` and its
independent holdout at `899de38c5a40e75a27278d3d3ecc7def48f51756`.

V4 implicitly assumed a fully populated 64-bin environmental map. This new
module removes that assumption. The first-turn camera supplies one 16-bit
column at a time; a **gyro-derived integer bin index is supplied by the
caller**, and its accurate assignment is presently an unverified assumption.
The map is frozen before any subsequent matching. Unknown map locations
remain unknown; the code never silently fills them with zero-valued columns.

## Finite implementation

`finite_partial_map.c/.h` provides:

* A 146-byte map struct (128-byte reference, 8-byte coverage mask, 8-byte
  quarantine mask, and two state bytes).
* `mg_map_capture`: marks newly seen first-turn columns; accepts consistent
  repeats and permanently quarantines a bin when two columns differ by more
  than two bits. Quarantine is not an authenticated source-identity proof.
* `mg_map_freeze`: prevents changes to source authority during downstream
  heading estimation. There is no later unverified self-repair of map holes.
* `mg_sparse_plan`: exact minimum set of future columns that **guarantees**
  separation with all valid ±1 timing offsets and ≤2 source-to-observation
  Hamming errors. If even one necessary reference window is unknown, it may
  decline a purported guarantee.
* `mg_sparse_next_probe`: when the guarantee fails, find an **opportunistic**
  observation that could eliminate a candidate if a particular allowed value
  arrives. Status `MG_POTENTIAL_PROBE = 5` is explicitly **not evidence** and
  authorizes nothing. Selection maximizes directed possible pair eliminations
  and uses the earliest time to break ties. After each actual observation the
  candidate set is filtered and a new plan is computed.
* `mg_sparse_filter`: cannot eliminate a hypothesis if one of its admissible
  reference-offset columns is missing. Source disagreement yields `CONFLICT`,
  and insufficient candidate separation yields `UNKNOWN`.

No future actual column or ground-truth heading is provided to either planner.

## Development matrix (four seeds × four true headings per condition)

All methods use exactly the same frozen partial map, bounds and measurements.
The conventional baseline reads **every available future column** and applies
the same conservative filter; it is not a naive or uncalibrated baseline.

| First-turn map condition | Guaranteed correct /16 | Active correct /16 | Continuous correct /16 | Active reads total | Continuous reads total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Full 64/64 | 16 | 16 | 16 | 32 | 196 |
| One missing unrelated bin | 16 | 16 | 16 | 32 | 196 |
| 3 random missing bins | 14 | 16 | 16 | 37 | 239 |
| 6 random missing bins | 10 | 14 | 15 | 43 | 275 |
| 12 random missing bins | 0 | 7 | 13 | 53 | 308 |
| All first-cue bins missing | 0 | 0 | 0 | 28 | 512 |
| Contradictory duplicate at bin 7, quarantined | 16 | 16 | 16 | 36 | 235 |

There were zero false authorized corrections in these 112 synthetic
development cases, but the safety finding is **conditional** on the exact
synthetic noise/gyro/index model. Active evidence-seeking recovers some
availability lost by the guaranteed-only method. It **does not dominate** the
equally informed continuous baseline: with 12 missing bins, active resolution
was 7/16 while continuous resolution was 13/16. The smaller observation count
there is not an apples-to-apples efficiency win because fewer cases resolve.
Planning also performs substantially more computations than scanning and
filtering individual observed columns.

## Independent checks and open obstruction

Native C tests compare minimum cover to an independently coded exhaustive
subset enumerator, and opportunistic capture choice to an independently coded
directed-exclusion oracle. Other tests check that the real synthetic candidate
survives all allowed timing slips and one-bit measurement errors, across
partial map masks. The CI workflow additionally compiles an ARM Cortex-M4
Thumb object, without claiming hardware execution.

The original 16/16 scene-identity spoof negatives **still apply**. A stable
source substitution that looks exactly like another allowed heading remains
observationally indistinguishable with only these camera and gyro inputs. No
version is flight-ready or a certified absolute compass. The next physical
residual is independently measured first-turn angular-bin error and actual
line-camera/gyro synchronization, preferably on repeated full-turn recordings
or a controlled rig.
