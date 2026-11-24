# Current follow-up: header controls and routing-table visibility

2026-11-24. This extends the earlier dedup-backport checkpoint without changing its credit, source boundary or results. No external issue, pull request, comment or email has been submitted in this iteration.

## What is warranted

**WARRANTED, bounded native discrepancy:** with a configured routing-table capacity of 10, the tenth distinct exact route is reported successfully inserted but is absent from both lookup and iteration. This reproduces in current EnduroSat `develop@135807773e7fd9aea9f68f027e296e9f54d75830` and upstream libcsp `develop@5ba0ccf66ec0301e65160b41e035cb8a7c916949`. Both implementations share the relevant code lineage; this is one mechanism, not independent discoveries in two companies.

**WARRANTED, bounded causal repair:** a small candidate separates the number of active entries from the index of the last replaceable slot. It allows all N configured entries to be searched and preserves the existing policy of replacing the last entry on a new insertion into a full table. Updating an existing entry continues to update that entry.

| Native check | Original | Candidate | Withdrawal |
|---|---:|---:|---:|
| EnduroSat original author tests | 22/22 pass | 22/22 pass | 22/22 pass |
| Upstream libcsp original author tests | 12/12 pass | 12/12 pass | 12/12 pass |
| Selected route observations, EnduroSat | 88/114 discrepant | 0/114 discrepant | 88/114 discrepant |
| Selected route observations, libcsp | 88/114 discrepant | 0/114 discrepant | 88/114 discrepant |

Each repository's 114 observations span capacities 1, 2 and 10 and protocol versions 1 and 2. Observation rows are correlated queries/controls of the same state, not independent inputs or discoveries. All twelve before/withdrawal traces are byte-identical. Original source bytes are restored. The route repair was tested alone: it does not incorporate the separate dedup backport.

**REJECTED within the selected host boundary:** no discrepancy was found in the original header encoder/decoder. Two actual CMake builds, using the system endian implementation and the project's portable endian implementation, each pass 952 independent golden-byte encodes, 952 independent decodes and 20 short-header rejection controls. Payload lengths 0, 1, 17 and 256 and both CSP versions and CSPv1 little-endian fixup modes are covered. This is selected boundary coverage, not exhaustive header verification or 16-bit MCU execution.

## Contract, alternative interpretations and history

The public `csp_rtable_set` contract returns success or an error, and CMake describes `CSP_RTABLE_SIZE` as the number of routing-table elements. The demonstration uses distinct valid exact node addresses and one synthetic interface, without sockets, hardware drivers or network I/O.

The full-table policy was **not invented for this experiment**. In [issue #350](https://github.com/libcsp/libcsp/issues/350), maintainer johandc confirmed that the most recently inserted direct route should be accepted when the table is full, replacing the last entry. The [2025 change 5f8f0d07](https://github.com/libcsp/libcsp/commit/5f8f0d07b7cafabde56c26cf086d7d98343555f2) likewise describes preserving last-route replacement. That policy permits replacing the previous last route at capacity; it does not explain reporting success while the newest route remains invisible. The independent oracle expressly models replacement, rather than requiring rejection at capacity or preservation of an evicted last entry.

Related history is material. Issue #350 reported an out-of-bounds insertion problem in 2022 and was closed. The 2025 change altered the clamp to `CSP_RTABLE_SIZE - 1`. Current insertion writes the last physical slot and clamps the active count to N-1; lookup and iteration both stop before that slot. Source comparison links the current invisible-slot mechanism to this lineage. No historical binary was executed. Do not report this as an unrelated first-ever routing problem, or assert that maintainers have never encountered it.

Targeted current public searches for `rtable_inptr`, `CSP_RTABLE_SIZE`, routing-table full/capacity, last-route and off-by-one terminology found #350 and other different issues, with no matching newer report identified. Private history and exhaustive novelty remain UNKNOWN. Both current develop heads were pinned and checked. The follow-up is a candidate focused upstream discussion about a still-observable postcondition failure, with explicit acknowledgement of #350 and 5f8f0d07.

At capacity one, a first insertion already returns success while iteration reports zero entries and lookup returns NULL. At capacity ten, routes one through nine remain visible, while routes ten and eleven are invisible despite success. These are ordinary unit-level correctness observations; no deployment or operational consequence is established.

## Native experiment and independent oracles

`route-capacity-probe.c` calls the actual library's `csp_rtable_set`, `csp_rtable_find_route`, `csp_rtable_iterate` and `csp_rtable_free`. It records insertion, lookup, full-table replacement, update, post-update preservation, NULL-interface rejection and clear behavior. `route-qualify.py` builds both repositories with the original CMake files, routing tables enabled, static linking and capacities 1/2/10. Its Python state model is an ordered finite list with the maintainer-established last-slot replacement rule. The model does not copy the C counter/clamp implementation. All host addresses used by the experiment are valid in both protocol versions.

`wire-probe.c` executes the actual library's header functions. `wire-matrix.py` derives golden bytes by concatenating declared field widths from the pinned source's header diagrams, then supplies those bytes independently to decoding. It does not obtain decode inputs from the actual encoder. Thus its calculation is independent of the implementation's shift/mask code, but the layout authority is still the project's own declared layout; this is not independent protocol-standard validation. Native payload-preservation and short-frame rejection controls are also checked.

A deliberately injected **test-sensitivity control** swaps CSPv1 source/destination offsets in both encoding and decoding. All 952 native round trips still pass, while 712 independent encode/decode expectations fail. This is an injected common-mode error, not a defect found in upstream source. It demonstrates why matched round trips alone do not validate this property. The original source was never replaced by the mutation; the mutant is a separate compiled source file with a retained digest. Native and portable original-build outputs are byte-identical.

`wire-receipt.json`, `route-receipt.json`, command records, patches and raw outputs preserve exact source identities and results. The source trees were restored after all intervention arms. A separate arithmetic replay recomputed each selected route expectation from raw records. This is same-researcher separate-code verification, not independent third-party review.

## Reproduction and scope

Use the dependencies and directory layout described in `README.md`. Additionally clone libcsp into sibling `libcsp-current/` and check out `5ba0ccf66ec0301e65160b41e035cb8a7c916949`. Run:

```sh
python3 enduro-evidence/run-wire.py
python3 enduro-evidence/route-qualify.py
```

The scripts retain exact command arguments. Portable-endian execution is on the same x86-64 Linux host, with `HAVE_ENDIAN_H=OFF` selecting the real portable source; it is not an emulator or target claim. Route qualification enables `CSP_USE_RTABLE=ON` explicitly in upstream, whose default is OFF, and uses the fork's supported routing-table functionality. At the small capacities, the focused probe runs; full original author suites run at capacity 10, where their existing fixtures fit.

One preliminary upstream author-test build could not find the locally installed `check.h` because that project's target did not propagate its non-system include directory. Explicit compiler and linker search paths corrected the environment; no project source/build file was altered for that correction. The preliminary default upstream build had routing tables disabled and was not used as routing evidence. Failures from that setup remain recorded separately. Optional ZeroMQ-dependent tests are excluded by the absent library; full integration/transport workflows and other platforms are unqualified.

## Maintainer fit and practical next action

Upstream libcsp is the clearer immediate contribution route: its contribution guide explicitly asks that older/fork findings be reproduced on develop and directs fixes there. MIT license, contribution guide, coding and commit conventions, issue templates and current tests were inspected. No separate PR template, root security policy or code-of-conduct file was present in the inspected checkout. Templates ask for text logs, exact environment and expected/actual behavior. The successful #1036 discussion shows a maintainer accepting a focused fix after static/shared test details were corrected; bot approval alone is not human acceptance.

The prepared `ROUTING_ISSUE_DRAFT.md` follows that narrow style and cites the prior history. EnduroSat's issues remain disabled despite welcoming contribution documentation, so duplicating reports there is not the current recommendation. Neither maintainers' acceptance of this finding nor a paid engagement is established. No external submission is authorized by this checkpoint.

The highest-leverage residual is maintainer review of the current capacity postcondition and the small compatible correction. A reviewable repair and reproduction already exist. The smallest next authorized engineering action is to retain these materials; when submission is authorized, recheck current source/issues and send one focused upstream report. Do not bundle the separate dedup backport, header negative result or promotional claims into it.

Reuse is narrow: a successful write needs an independent read/iteration postcondition; a paired encoder/decoder can share a mistake. Both are familiar testing principles. This iteration demonstrates their selected practical application, not a new general law, prospective comparative advantage or commercial demand.
