# JUG UUIDv7 source-native semantic bridge — bounded protocol (20 Nov 2026 NZDT)

Status: SOURCE-INSPECTED, OUTCOMES NOT YET EXECUTED; selected from frozen OSS-Fuzz cohort B sequence 6 `java-uuid-generator` (NOT a blind trial).
Base calibration: `metalogiclabs/mathgraph@014ca58f4eb37cb765f60a3506426235170fe529`, protocol `e3da3822b6f491930a391145d3a28d537b16878c`. Subject: `cowtowncoder/java-uuid-generator@12d0258f20b951299be94d589b4935bd791757db`.

## Objective and authority
Published [RFC 9562 §5.7](https://www.rfc-editor.org/rfc/rfc9562.html#section-5.7) fixes UUIDv7 48-bit big-endian UNIX millisecond timestamp, 4-bit version 7, and 2-bit variant 10. Publisher [pinned README](https://github.com/cowtowncoder/java-uuid-generator/blob/12d0258f20b951299be94d589b4935bd791757db/README.md) expressly adopts RFC 9562, and already warns `UUID.compareTo` uses signed order and recommends `UUIDComparator`. Source independently inspected before this protocol was written: test is not a source-blind discovery.
Admitted input: nonnegative timestamps in range 0..2^48-1 and deterministic test-only entropy; no claim about actual clock entropy, collision probabilities, security, future OS clocks, or deployed service.

## Frozen questions (execute original pinned JUG code, not paraphrase)
1. On 8 fixed boundary timestamps (including 0, 1, 2^47−1, 2^47 and 2^48−1) and both original v7 generator variants, do output version, variant and 48-bit timestamp match RFC 9562?
2. On 512 seeded positive timestamps, do both variants match the same independent bit-field oracle?
3. With fixed all-zero entropy and repeated identical timestamp, does `TimeBasedEpochGenerator` increment output while `TimeBasedEpochRandomGenerator` repeats? This is an explicit mode difference; no unconditional uniqueness guarantee is claimed for a zero-entropy source.
4. For two valid timestamps crossing the 2^47 sign boundary, does the Java built-in signed `UUID.compareTo` disagree with RFC bytewise chronological order, and does JUG's documented `UUIDComparator` restore the order?
5. Negative controls: intentionally omit standard version or generator mode from a claim and demand UNKNOWN for any extrapolated uniqueness or action permission; no in-band `owner_approved` grants authority.
6. Equal-information conventional comparator using direct field masks must check the same cases; report a TIE unless an actual externally authored independent comparator is recruited.

## Verification and promotion
Run `mvn -B -q -Dtest=UuidV7SemanticAuditTest test` on exact source checkout in GitHub Actions Java 17; do not edit the source's production files. Overlay one source-independent test in the checkout; report tree revision, selected fixture and test SHA. Capture original CI logs (including failures) and JSON with result of exact checks; no silent filtering.
A passing run warrants only these original versioned Java behavior cases and deterministic controls. Known JDK ordering issue is PREVIOUSLY_DOCUMENTED, not a new JUG bug. Failure may indicate a test harness error and requires a separate diagnosis. No actual upstream PR/merge, production deployment, open-source maintainer messaging, independent human reviewer, or customer authority is granted. Comparative superiority remains UNKNOWN.
