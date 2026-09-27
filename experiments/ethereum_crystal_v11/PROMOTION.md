# Ethereum Crystal V11 — Promotion

**State:** WARRANTED / REUSABLE at the pinned go-ethereum package-integration boundary.

**Primary authority:** MathGraph run 36355203318, job 108721455645, artifact 10943641142, artifact digest `sha256:835f228df20298d5133952432c3e113978a2d2408c841b11f5d5f607646305ad`.

**Pinned authorities:**
- EELS: `ethereum/execution-specs@84e7d2c266e3319fc3882e72f379282bb1c40f2d`
- go-ethereum: `ethereum/go-ethereum@920c07774c65ebb3023536f85df642c44478b540`
- Parent native replication: V10 run 36354980547

The frozen Crystal dependency interface was evaluated on the same 1,112 held-out canonical BAL RLP records used by V9/V10. Before benchmarking, the Crystal view was checked field-for-field against go-ethereum's production `BlockAccessList` decoder for every held-out record.

Median go benchmark results:
- full geth BAL decode: 7,056,849 ns/op
- Crystal dependency view: 2,710,536 ns/op
- speedup: **2.603488x**
- full allocations: 7,842,088 B/op and 82,163 allocs/op
- Crystal dependency allocations: 4,146,728 B/op and 54,565 allocs/op
- allocation byte ratio: **0.528779**
- allocation call ratio: **0.664107**

The promoted reusable claim is therefore:

```
verified consequence-specific interface
→ exact field-level agreement with production protocol object
→ skip irrelevant materialization
→ measurable package-level reduction in decode work
```

This does **not** claim full-node end-to-end speedup, optimality inside geth, upstream merge readiness, or benefit in other clients. No upstream branch or PR was created.

**Next promotion boundary:** integrate the view into an actual client execution path or benchmark harness that exercises realistic BAL consumption in node context while preserving all protocol checks and measuring end-to-end latency/CPU/allocation effects.
