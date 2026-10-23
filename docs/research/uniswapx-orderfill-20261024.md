# 2026-10-24 NZDT — UniswapX order-fill test

## Outcome

No profitable fill demonstrated. Read-only test, no trades, no signing/funding/deployments. Main unchanged. This is a conventional order-acquisition/eligibility diagnostic; the existing MathGraph planner was not invoked and no MathGraph-specific edge is inferred.

## Exact evidence

- Acquisition [run 40026922285](https://github.com/metalogiclabs/mathgraph/actions/runs/40026922285), source `ab98bc6bf466d54e38cc7e79c108679bb1db761f`, artifact 12532812547, ZIP SHA256 `b8024b06a4027671166b683627389f8062de869f4caceba233f404ea2f17de74`.
- Native evaluation [run 40027859500](https://github.com/metalogiclabs/mathgraph/actions/runs/40027859500), source `bc1afb8334300f0441914be831da37cad30153d4`, artifact 12534255157, ZIP SHA256 `70ac9992c9131cf70f861eefe72ec1feeaf1941b139e3f4babd081026a0f094f`.
- Both workflows completed successfully. Apparatus green is not profit.

## Live sample and actual settlements

150 valid HTTP-200 Base Dutch_V3 open-order polls, spaced at least two seconds, returned no open orders. Two non-contiguous windows: 2026-10-23 21:27:46.784–21:30:45.139 and 21:35:48.364–21:37:46.561 UTC (24 October NZDT). About 296.55 seconds total observation, not a continuous ten-minute experiment. No HTTP error or throttle counted as empty. This is not proof that a faster observer or longer window would see none.

The first window's recent-before, recent-after and filled lists were identical: 50 already-completed orders, API-created 18:04:35–21:16:02 UTC. They were NOT observed before execution. All 50 witness hashes, swapper EOA signatures and cosigner signatures matched with official SDK 3.1.5. Actual successful receipts and canonical reactor Fill events independently matched block/hash/time/swapper/nonce.

49/50 fills occurred before recorded decayStartBlock. 45/50 actual fillers matched the named exclusive filler; four others won during exclusivity and one after decay. Do not claim outsiders cannot participate. Every encoded order had a 25-bps soft-exclusivity override, omitted from the public JSON cosigner metadata. Median API-create-to-onchain-fill delay was two seconds, not public availability latency.

## Frozen direct-pool economic subset

All three exact native-USDC input / canonical-WETH output orders in the 50-order set were selected by token identity. Seven native ETH output orders were excluded. The original deployed OrderQuoter resolved each original signed order at fillBlock-1 with no state, balance, nonce, code, timestamp or block overrides. Required output exactly equaled the cosigned amount times 1.0025, rounded up. All three reverted at end-of-fill-block and again at current state.

At each same pre-fill block, quote exact output across four Uniswap v3 fee tiers and six tick spacings on each of three official Aerodrome quoter generations: 66 calls, 26 completed, 40 reverted/UNKNOWN.

| Input USDC | Cheapest completed procurement USDC | Gross margin before gas USDC |
|---:|---:|---:|
|8155.392823|8178.472133|-23.079310|
|2905.701231|2913.515911|-7.814680|
|11737.188001|11772.953811|-35.765810|

Every completed route had nonpositive gross. The best shortfalls were 26.89–30.47 bps of input. Swap fees/price impact included; gas and other nonnegative costs cannot rescue these fixed quotes. Do not infer the actual winning filler's economics.

## Boundary and lineage

WARRANTED bounded: raw observations, 50 canonical settlement matches, 26 negative gross quotes at exact historical states and native post-fill refusal. REJECTED only on the completed tested routes/states: profitable outsider direct-AMM filling. UNKNOWN: the 40 reverted configurations, other/split liquidity, inventory, prospective availability, complete execution costs, capture and all-market profitability. Historical signed orders were acquired after completion; this is a hindsight mechanism diagnostic, not an attainable-profit backtest.

OrderQuoter stops at a callback; full acquisition-and-delivery settlement was not simulated. RPC trust and source/deployed-bytecode equivalence remain assumptions, not chain-state proofs. The local DNS failure was bypassed through GitHub Actions; it was not a market negative. No new upstream writes or outreach.

Executed acquisition tests 10/10; evaluator arithmetic/scope tests 12/12. Local reruns used executed artifact sources. Separate raw-byte/ABI/integer audits passed 480 acquisition and 2286 evaluation assertions; cryptographic recovery itself was not independently reimplemented. Full report, raw replies, original artifact ZIPs, audits, negative-development logs and manifests delivered as the conversation evidence bundle.

## Highest-leverage residual

The four actual outsider early fills are a better next diagnostic than another arbitrary market search: reconstruct their true settlement/procurement paths, without assuming the fills were profitable; then freeze a method before new orders. A longer read-only availability sample could distinguish a quiet window from a persistent feed constraint. Neither result nor a funded strategy is claimed here.
