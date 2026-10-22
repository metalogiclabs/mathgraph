# MathGraph spinning-column visual compass — portable embedded core v4

Status: **candidate implementation, conditional finite evidence only**. This
core does not command a drone, estimate continuous attitude, or validate a
physical camera. Prior Python jitter acquisition was frozen and independently
audited in [FINITE_JITTER_PROTOCOL.md](FINITE_JITTER_PROTOCOL.md).

## Execution boundary

* `finite_jitter_embedded.h/.c`: freestanding C99 with no heap, floating point,
  standard-library calls, or persistent global state. Input first-turn map is
  64 × `uint16_t` columns (128 bytes). The planner uses a 32-step horizon.
* Declared gyro prior candidates are exactly {0, 16, 32, 48} in an angular
  64-bin map. This support is externally provided, **not acquired from sensors**.
* Every observed 16-bit column differs from the corresponding first-turn map
  column in at most two bits; every sampling-time offset is independently
  bounded to ±1 angular bin. Changing scenes or violating these bounds voids
  the safety claim. The library accepts other small declared bounds for tests.
* For each candidate pair, an observation separates it only if all possible
  offset combinations have Hamming distance > twice the error budget. An
  exact minimum-cardinality set of future steps covers all candidate pairs;
  ties prefer the earliest last step, then lexicographically earliest steps.
  After every missing or acquired column, the caller must replan.
* `mg_filter` retains a candidate if **any** allowed offset explains the actual
  observed column within the declared error budget. Zero candidates means
  `CONFLICT`; multiple candidates means `UNKNOWN`. The caller must not emit a
  consequential correction unless it has authenticated evidence for a unique
  candidate. `ALREADY_UNIQUE` means a singleton was supplied, **not** that a
  sensor newly verified it.

## Distinct verification paths

1. C compiled with host GCC `-std=c99 -Wall -Wextra -Werror -O2`; Python
   `ctypes` compares **every step, abstention, heading filter, and comparison
   count** on 64 original Python development scenarios.
2. 1,920 additional randomized map/support/error/jitter planner comparisons
   check C output against the frozen Python implementation. Python itself was
   previously checked against an independently implemented exhaustive oracle.
3. A separate physical-source test checks survival of the actual synthetic
   candidate across each permitted ±1 slip and one-bit observation error;
   both first-turn and future readings independently incur a one-bit error.
   Ground truth is used **only** in this external audit, never by C.
4. The CI workflow builds a host freestanding object and an ARM Cortex-M4
   Thumb object, checks the host object has no undefined external symbols,
   reports `.text`, `.data`, `.bss`, and compiler-estimated stack usage. **An
   ARM build is compilation only, not execution or power/performance testing.**

Reproduce from the repository root:

```
python -m unittest discover -s experiments/uzh_rotation -p 'test_finite_jitter_embedded.py' -v
gcc -std=c99 -Wall -Wextra -Werror -Os -ffreestanding -fno-builtin \
  -fstack-usage -c experiments/uzh_rotation/finite_jitter_embedded.c -o /tmp/finite_jitter.o
size /tmp/finite_jitter.o
nm -u /tmp/finite_jitter.o
```

## Comparison and exclusions

This is **not** a measured flight controller. The strong equally informed
conventional baseline inspects each available future column, performs the same
worst-case noise/jitter filtering, and can resolve faster than a sparse plan.
MathGraph's only established advantage here is planning fewer camera reads
while retaining **conditional** worst-case separation; planning consumes more
pair checks, and correct refusal is not guaranteed if source fidelity fails.

Out of scope: acquisition of the four-heading prior, time calibration,
independent scene integrity detection, dynamic translation/parallax,
real-time scheduling, gyro bias estimation, physical line-camera optics,
sensor interface, motor timing, memory alignment on the eventual board,
electromagnetic interference, closed-loop stability, and real-world safety.
No proof of superiority to a similarly informed conventional optimal planner.
