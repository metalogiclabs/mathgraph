# Draft — not submitted

Title: `rtable: successful insertions into the last slot are not visible`

## Description

On current develop (`5ba0ccf66ec0301e65160b41e035cb8a7c916949`), `csp_rtable_set()` returns `CSP_ERR_NONE` for the last configured slot, but the newly added route is not returned by `csp_rtable_find_route()` or `csp_rtable_iterate()`.

This appears related to #350 and 5f8f0d07. I understand that the intended full-table behavior is to accept the newest route by replacing the last slot. The problem below is that this slot is excluded from lookup, including the first time the table reaches capacity.

## Steps to reproduce

Build current develop with `CSP_USE_RTABLE=ON` and the default `CSP_RTABLE_SIZE=10`. With an empty table, insert ten distinct valid exact routes through a synthetic interface and query each route immediately. The retained standalone `route-capacity-probe.c` does this using only the routing-table APIs; it opens no sockets or hardware interfaces.

## Expected behavior

The first ten insertions should be visible. If an eleventh distinct route replaces the last entry, the eleventh should be visible and the previous tenth may be absent, consistent with the policy discussed in #350.

## Actual behavior

```text
capacity 10
insert 9:  return 0, iterator count 9, lookup found
insert 10: return 0, iterator count 9, lookup NULL
insert 11: return 0, iterator count 9, lookup NULL
```

With `CSP_RTABLE_SIZE=1`, the first insertion returns success, but iteration counts zero routes and lookup returns NULL.

The insertion writes `rtable[rtable_inptr++]`, then clamps `rtable_inptr` to `CSP_RTABLE_SIZE - 1`. Lookup and iteration use `i < rtable_inptr`, so the last physical slot is not visited.

## Verification

Native checks reproduce this on develop and the EnduroSat fork. Capacities 1, 2 and 10 and both protocol versions were exercised. A candidate correction preserves the existing last-slot replacement behavior while tracking all active entries. On develop, all 12 available original unit tests pass before and after; 114 selected state observations change from 88 discrepancies to zero. Withdrawing the candidate restores byte-identical original traces. The affected behavior is one shared implementation mechanism.

## Environment

- Linux x86-64; GCC 14.2.0; CMake 4.4.5; libcheck 0.15.2.
- Native static library; `CSP_USE_RTABLE=ON`, other options recorded in the evidence.
- Optional ZeroMQ library absent; its conditional tests were not run.
- Meson and waf not used.

Research evidence, raw output and candidate patch: https://github.com/metalogiclabs/mathgraph/tree/research/endurosat-csp-es-20261124/research/aerospace/endurosat-csp-es-20261124

Would a focused fix with regression tests preserving last-slot replacement be useful?

Before publication: recheck develop and related reports, replace the evidence branch URL with the immutable checkpoint commit, and attach the minimal reproduction. No issue or pull request has been submitted.
