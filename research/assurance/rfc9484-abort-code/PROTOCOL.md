# RFC 9484 → capsule error → HTTP/3 stream code diagnostic

Date: 2026-11-20 NZDT. Research-only; source-inspected hypothesis, NOT blind independent discovery or approved upstream bug.
Source: quic-go/connect-ip-go@9ee608a68fbbc6c377d13da4df2a269580b78909 (conn.go Git blob e988c047bcdba848c3a23114645380a4d4ddf6fb; capsule.go blob 45ca29b4eff3b59deb44e1dbcd1757a7948568fd).
Dependency: quic-go/quic-go v0.65.0 (go.mod exact SHA; http3/error_codes.go defines 0x107 H3_EXCESSIVE_LOAD and 0x10e H3_MESSAGE_ERROR).
Normative chain: RFC 9484 §4.7.3; RFC 9297 §3.3 mandates treating malformed Capsule Protocol processing as malformed/incomplete HTTP message; RFC 9114 §4.1.2 and §8.1 require stream error H3_MESSAGE_ERROR for a detected malformed HTTP/3 message.
Hypothesis after reading original source: an invalid IP-version byte in a ROUTE_ADVERTISEMENT Capsule causes the original conn.go read goroutine to call CancelRead and CancelWrite with H3_EXCESSIVE_LOAD (0x107), not H3_MESSAGE_ERROR (0x10e). The original code does cancel both directions, so “failure to abort” is NOT the hypothesis.

Predeclared tests:
1) malformed capsule IP-version byte 5: native actual parse of bytes, newProxiedConn goroutine, record both CancelRead and CancelWrite error codes and close cause.
2) valid ROUTE_ADVERTISEMENT with a single IPRoute: parsed and delivered through Conn.Routes; no error-coded abort before graceful shutdown.
3) a correctly formed capsule with same-protocol overlapping routes: error and stream cancellation; normative code applicability may be less clear than malformed byte and MUST remain separate.
4) a protocol-zero/protocol-6 overlapping capsule: original receiver MAY validate and choose abort; do not label its choice nonconforming.
5) a malformed no-route? empty route advertisement permitted (zero or more); should be accepted.

Use the authentic original Go 1.26.0 package (including full dependency and mockStream defined in original conn_test.go). Copy a test-only Go file into an ephemeral checkout; do not mutate tracked originals. Verify exact Git commits/blob hashes before and after; run original go test ./... and the targeted probe.
Report source behavior as bounded. A caller invoking CancelRead/CancelWrite with 0x107 instead of 0x10e is a potential external-standard correspondence discrepancy, but full QUIC wire-level framing, error-code policy, owner interpretation and other error-handling layers remain UNKNOWN without further verification. Do not issue upstream defect claim or repair without independent source/spec adjudication. Strong conventional reviewer superiority NOT_RUN. Preserve both positive and negative controls and failed harness runs.
