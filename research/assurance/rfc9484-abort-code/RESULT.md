# 2026-11-20 — CONNECT-IP malformed Capsule → HTTP/3 cancellation code

**Status:** WARRANTED_BOUNDED for native source-to-transport-API observations; **CANDIDATE** independently published RFC-to-HTTP/3 error-code correspondence finding; **UNKNOWN** external owner interpretation, full QUIC on-wire behavior, upstream triage/repair and comparative advantage. PRIVATE study record, not an upstream bug report or repair approval.

## Objective and authoritative sources

The previous RFC 9484 finite trial established that the pinned upstream ROUTE_ADVERTISEMENT validator rejects mandatory-invalid inputs and optionally chooses to reject protocol-zero overlap. This study tested the *next boundary*: whether an error actually propagates from original Capsule parsing through the genuine Conn read goroutine to the HTTP/3/QUIC stream-abort API, with the type of error required by the governing standards.

- Original implementation: [quic-go/connect-ip-go@9ee608a68fbbc6c377d13da4df2a269580b78909](https://github.com/quic-go/connect-ip-go/commit/9ee608a68fbbc6c377d13da4df2a269580b78909); original conn.go Git blob e988c047bcdba848c3a23114645380a4d4ddf6fb; original capsule.go Git blob 45ca29b4eff3b59deb44e1dbcd1757a7948568fd.
- Original dependency: quic-go/quic-go v0.65.0 defines H3_EXCESSIVE_LOAD 0x107 and H3_MESSAGE_ERROR 0x10e; http3.RequestStream.CancelRead delegates to the underlying QUIC read cancellation.
- Published external obligation: [RFC 9484 §4.7.3](https://www.rfc-editor.org/rfc/rfc9484.html#section-4.7.3) (route advertisement receive / mandatory abort); [RFC 9297 §3.3](https://www.rfc-editor.org/rfc/rfc9297.html#section-3.3) (Capsule processing errors treated as malformed/incomplete HTTP); [RFC 9114 §4.1.2](https://www.rfc-editor.org/rfc/rfc9114.html#section-4.1.2) (detected malformed HTTP/3 messages must be stream errors of type H3_MESSAGE_ERROR). The independent published standards exist; two independent human interpretations of their applicability to this exact caller have NOT been obtained.

## Exact experiment

A research-only Go test was injected as a single untracked source file into a clean pinned original checkout. All original tracked upstream source and module bytes remained unchanged. Original Go 1.26.0 package tests ran successfully. The native test exercised original newProxiedConn, readFromStream, HTTP/3 CapsuleParser, parseRouteAdvertisementCapsule and cancellation calls through a QUIC-error-code-recording mockStream. It did NOT open a real QUIC network socket or capture wire frames.

Final research head: [5a994f148fbd9a9715ad09acdbbbe4c79706426f](https://github.com/metalogiclabs/mathgraph/commit/5a994f148fbd9a9715ad09acdbbbe4c79706426f). Hosted [GitHub Actions #44633227950](https://github.com/metalogiclabs/mathgraph/actions/runs/44633227950) completed SUCCESS. Earlier source-native witness [#44632686585](https://github.com/metalogiclabs/mathgraph/actions/runs/44632686585) also SUCCESS; the final run adds a queue-excessive-load countercontrol, rather than pretending it was preregistered before seeing the first observation.

| Original input | Exact original native behavior | Scope |
| --- | --- | --- |
| ROUTE_ADVERTISEMENT malformed IP version 5 | Parse error "invalid IP version: 5"; both CancelRead and CancelWrite with 0x107, NOT 0x10e | Strongest source-grounded standards-comparison candidate: definitely malformed Capsule payload |
| Same-protocol overlapping ordered ranges | Parse/validation error and both cancellation calls with 0x107 | RFC 9484 requires abort; exact HTTP error-code interpretation independently unadjudicated |
| Protocol-zero plus specific-protocol overlap | Receiver voluntarily detects and rejects, cancellation calls 0x107 | Receiver-side validation is OPTIONAL; rejection itself is not a defect |
| Different specific protocols using same address | No error-coded read/write abort, both routes installed in model | Positive non-overlap control |
| Empty route advertisement | Graceful no-error-coded abort; no routes | RFC allows zero routes, negative control |
| 129 valid empty ADDRESS_ASSIGN capsules, receive queue capacity 128 | Queue-full error and both cancellation calls with 0x107 | Resource-exhaustion control, potentially appropriate use of H3_EXCESSIVE_LOAD |

The original Conn implementation does abort read and write when parsing fails; therefore the initial "no abort" hypothesis is **REJECTED**. The observed issue is the **loss of error-category distinction at the error→transport-code boundary**: both malformed and overloaded conditions are reduced to the same unconditional H3_EXCESSIVE_LOAD code. A global edit replacing all H3_EXCESSIVE_LOAD codes with H3_MESSAGE_ERROR would incorrectly eliminate the resource-exhaustion classification, so any hypothetical repair requires scoped error typing. This is a proposed diagnosis, not a tested complete repair.

## Preserved evidence

- Original-source and test-only namespace, exact Git blob SHA and Go dependency version checked before native replay.
- 5 positive/negative route-capsule controls plus one independently added queue-overload control passed.
- Final CI artifact 14583310353, SHA256 7bf36e84ef81fcf2cca32e6b7108eacba9cbcd1a977d3b1a5f32580ec210756e, separately downloaded and rehashed (provider SHA matched, ZIP CRC clean). Original native log contains the numeric codes and error causes. Previous first-source witness is distinct, not counted as another independent defect.
- One earlier test-only representation error was corrected: printing http3.ErrCode values with %#x invoked their Stringer and produced ASCII-code hex for the symbolic name. Cast to uint64 to print true 0x107 and 0x10e. That was presentation/test harness correction only.
- Read-only GitHub issue searches at snapshot found no direct matches for four narrow source/error-code queries; no blind novelty adjudicator and no fixed full tracker/changelog search, so upstream novelty is **UNKNOWN**.

## Explicit limits and cheapest next decisive experiment

The Go test measures calls to the transport API using a source-derived mock, not actual HTTP/3 QUIC on-wire reset frames. The cited standards suggest H3_MESSAGE_ERROR for invalid Capsule payloads, but interpreting their error-code requirement for every semantic route violation or buffer saturation requires independent expert adjudication. The selected source and witness were inspected before this test; this is NOT a source-blind discovery trial and the conventional human reviewer is NOT_RUN. No upstream defect report, fix PR, owner contact, live operational requirement or permission grant was made. No production/checker code, Cloudflare or existing draft PR #261/#279–#282 changed.

**Next narrow evidence gate:** run a real local QUIC/HTTP/3 loopback capture on the same exact source at an independently adjudicated malformed Capsule (plus a real queue-overload and valid route control); show the actual STOP_SENDING/RESET_STREAM error code. Separately ask qualified HTTP/3 and capsule-format interpreters whether RFC 9297 §3.3 / RFC 9114 §4.1.2 requires 0x10e in this context, and retain UNKNOWN if not. If source and normative meaning both support the claim, propose a minimal typed-error mapping and demonstrate preservation of the legitimate 0x107 resource limit before any upstream action.

**Research consequence:** Green source-native parser tests do not establish correct external error signalling. This is a deeper source→parser→transport bridge and a possible self-contained production-facing discrepancy; equally informed conventional comparison and time/cost advantage are still UNKNOWN.
