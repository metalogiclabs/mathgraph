# Independent finite comparison — 26 October 2026

**Status: REUSABLE within a frozen, constructed three-mutant domain.** Not a blind general-purpose coding benchmark, a state-of-the-art testing comparison, or a claim of superiority to optimized mutation testing.

**Preregistered before execution:** [BENCHMARK_PROTOCOL_20261026.md](./BENCHMARK_PROTOCOL_20261026.md), separate frozen-protocol commit `4c9009cedf362a9e50ba8437614c75b330ecd8fb`.

**Independent executable qualification:** [GitHub Actions #40268881457](https://github.com/metalogiclabs/mathgraph/actions/runs/40268881457), 32/32 Python tests, exact qualification source commit `159c418f576c17a34dc8bdaedcc0a5636474589e`. [Retained five-report package artifact #12627522966](https://github.com/metalogiclabs/mathgraph/actions/runs/40268881457/artifacts/12627522966), archive SHA256 `384d6a8b2f784b80a4f8bf89d9704ad9239e7596f7b36e5a0a067971e90b39ed`.

The same immutable `pallets/itsdangerous@672971d66a2ef9f85151e53283113f33d642dabd` encoding code and test-file Git hashes were checked. Three isolated injected faults (`standard_alphabet`, `unstripped_padding`, `trailing_zero_loss`) passed the original upstream tests. Independently executed native code and a standard-library oracle were compared across 1,026 predeclared byte inputs. The algorithm minimizes **synthetic** cost `1 + input byte length`, not runtime or model inference cost.

| Strategy | Chosen test count | Fully separates three mutants? | Synthetic cost |
| --- | ---: | --- | ---: |
| MathGraph minimum-cost separating basis | 2 | Yes (3/3) | **6** |
| Conventional mutation-aware weighted greedy, with identical mutant table | 2 | **Yes (3/3)** | **6 — ties MathGraph** |
| Fixed hand-selected boundary pair, inputs `00`, `ff` | 2 | No (2/3) | 4 |
| Fixed boundary trio, inputs `00`, `ff`, `000000` | 3 | Yes (3/3) | 8 |

Seeded uniform random property-test choices without replacement were run deterministically for **1,000 seeds, 0–999**, from the same finite domain:

| Random tests per seed | Seeds detecting all three faults | Full detection frequency | Mean synthetic cost |
| ---: | ---: | ---: | ---: |
| 2 | **19/1,000** | 1.9% | 6.022 |
| 4 | 60/1,000 | 6.0% | 12.102 |
| 8 | 151/1,000 | 15.1% | 24.166 |
| 16 | 314/1,000 | 31.4% | 48.174 |

The deterministic frequencies describe only the specified uniform sampling distribution and constructed mutants. They do not estimate defect detection in real-world software.

## Negative result and obstruction

The informed conventional greedy selector uses the same complete mutation-vs-oracle truth table and **matches the minimum**. MathGraph is **not superior to an equally informed mutation-testing baseline at choosing these tests**. Its practical distinction is the larger workflow: diagnose insufficient target evidence, acquire a separating observation, bind results to exact source and test bytes, withdraw stale authorization after edits, and return explicit UNKNOWN/REJECTED/WARRANTED states.

An intentionally withheld bug affecting only input `ffffffff` (hex) lies outside the input grammar and is not detected by the selected set. This is a concrete obstruction to any universal correctness claim.

## Reproduce

From the standalone distribution root after obtaining the exact pinned Pallets checkout and installing `pytest==8.4.2`:

```sh
MATHGRAPH_PINNED_UPSTREAM=upstream_itsdangerous python -m unittest -v test_paired_benchmark
python paired_benchmark.py --upstream-checkout upstream_itsdangerous --report frozen-baseline-report.json
```

**Consequence:** A fair next test requires prospectively selected unfamiliar tasks and independently held-out correct patches; do not describe these three constructed mutants as unseen.
