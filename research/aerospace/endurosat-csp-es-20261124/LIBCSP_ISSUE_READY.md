## Description

On `develop@5ba0ccf66ec0301e65160b41e035cb8a7c916949`, `csp_rtable_set()` returns success for the last configured slot, but the new route is absent from lookup and iteration.

This appears related to #350 and 5f8f0d07. I understand the intended full-table behavior is to accept the newest route by replacing the last slot. This report concerns that slot being invisible, including the first time the table reaches capacity.

## Steps to reproduce

Build current develop with routing tables enabled and the default capacity 10:

```sh
cmake -S . -B build -DCSP_USE_RTABLE=ON -DCSP_BUILD_SAMPLES=OFF -DBUILD_SHARED_LIBS=OFF
cmake --build build --target csp
gcc -Iinclude -Ibuild/include repro.c build/libcsp.a -pthread -o repro
./repro
```

`repro.c`:
```c
#include <csp/csp.h>
#include <csp/csp_rtable.h>
#include <stdio.h>

int main(void) {
	csp_iface_t iface = {.name = "TEST"};
	csp_conf.version = 2;
	csp_rtable_free();
	for (unsigned int i = 1; i <= CSP_RTABLE_SIZE + 1; i++) {
		int rc = csp_rtable_set(i, -1, &iface, CSP_NO_VIA_ADDRESS);
		printf("route %u: rc=%d, lookup=%s\n", i, rc,
		       csp_rtable_find_route(i) ? "found" : "NULL");
	}
	return 0;
}
```

## Expected behavior

The first ten distinct routes should be visible. An eleventh route may replace the tenth, consistent with the policy discussed in #350, but the new eleventh route should then be visible.

## Actual behavior

```text
route 1: rc=0, lookup=found
route 2: rc=0, lookup=found
route 3: rc=0, lookup=found
route 4: rc=0, lookup=found
route 5: rc=0, lookup=found
route 6: rc=0, lookup=found
route 7: rc=0, lookup=found
route 8: rc=0, lookup=found
route 9: rc=0, lookup=found
route 10: rc=0, lookup=NULL
route 11: rc=0, lookup=NULL
```

With `CSP_RTABLE_SIZE=1`, the first insertion also returns success while lookup returns NULL and iteration counts zero entries.

The insertion writes `rtable[rtable_inptr++]`, then clamps the active count to `CSP_RTABLE_SIZE - 1`. Lookup and iteration use `i < rtable_inptr`, so the last physical slot is never visited.

## Environment and verification

Linux x86-64, GCC 14.2.0, CMake 4.4.5, libcheck 0.15.2; Meson/waf not used. No sockets or hardware interfaces are opened by the reproduction.

[Native traces, source history and independent capacity checks](https://github.com/metalogiclabs/mathgraph/blob/027cad80d64c1ab8073432f60b3c3573288ee788/research/aerospace/endurosat-csp-es-20261124/ROUTE_AND_WIRE_RESULTS.md) cover capacities 1/2/10 and CSP versions 1/2. A candidate preserves last-slot replacement and changes 88 discrepant observations out of 114 to zero; withdrawal restores identical original traces.

I also prepared three regressions in the existing Check route suite. All 12 original tests plus the three regressions pass with the correction in both static and shared builds; all three regressions fail without it, while the original tests pass. Routing-disabled builds still pass 12/12. Optional ZeroMQ tests and hosted Clang jobs were not run.

Would a focused fix with these regressions, preserving the current replacement policy, be useful?

