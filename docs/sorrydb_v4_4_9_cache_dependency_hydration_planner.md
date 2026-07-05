# SorryDB v4.4.9 Cache Dependency Hydration Planner

v4.4.9 converts the v4.4.8 `OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY` result into an explicit controlled cache/dependency hydration plan.

It does not hydrate cache. It does not run Lean, Lake build, replay, proof checking, or dependency downloads.

## Boundary

The planner inspects the pinned hydrated source checkout and records whether the next cache hydration step is ready.

The expected ready condition is:

    CACHE_HYDRATION_READY

The recommended command is recorded but not executed:

    lake exe cache get

The optional baseline retry is also recorded but not executed:

    lake env lean MetaExamples/Fiddle.lean

## Bounded claim

v4.4.9 identifies whether the pinned hydrated source checkout is ready for controlled cache hydration and records the exact next command/postcondition.

## Does not claim

- cache hydration performed
- Lean replay success
- proof checking
- new proof discovery
- general SorryDB mining
- arbitrary proof repair
- upstream submission

## Next frontier

v4.4.10 should perform authorized controlled cache hydration reality, likely `lake exe cache get`, then retry baseline Lean contact.
