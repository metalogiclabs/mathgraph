"""Commercial falsification gate for MathGraph evidence continuity.

Grounded execution-time inputs from actual qualified runs:
Goldmark contract 39527316356 and Compose 39525969226.
Commercial variables are explicitly hypothetical, not customer telemetry.
"""
import json, argparse
from decimal import Decimal
def calculate(verify_s, candidate_s, competitor_s, volume, labor_s, dollar_per_hour):
    # Full lifecycle cost must include setup, engineering time, false escalation, and licensing.
    # We expose them as explicit costs, rather than inventing measured savings.
    def dollars(seconds): return Decimal(str(seconds))*Decimal(str(volume))*Decimal(str(dollar_per_hour))/Decimal(3600)
    return {"full_seconds":verify_s, "mathgraph_seconds":candidate_s, "strong_baseline_seconds":competitor_s,
            "volume":volume,"labor_seconds_per_change":labor_s,
            "difference_vs_baseline_dollars":str(dollars(competitor_s-candidate_s)),
            "human_labor_dollars":str(dollars(labor_s)),
            "beats_baseline":candidate_s<competitor_s}
def main():
    # measured independent equivalence test excludes process overhead; the competitor
    # can apply the *same* mathematical identity, so it is not a defensible advantage.
    goldmark=calculate(.192695,.000021,.000021,100000,0,60)
    # a conventional strong hash cache makes the same reuse decision for docs-only
    compose=calculate(10.36096,.0054,.0054,100000,0,60)
    report={"schema":"mathgraph.commercial-differentiation-gate.v1",
            "goldmark_de_morgan_equivalence":goldmark,
            "compose_docs_unchanged_source":compose,
            "actual_product_advantage":"NOT_DEMONSTRATED",
            "notes":["100000 changes and $60/h are sensitivity assumptions, not customers",
                     "Comparator is strongest equally informed conventional mechanism",
                     "No native semantic cross-revision scope-transport win over comparator",
                     "Zero difference does not imply zero potential future business value",
                     "Real economics require measured setup, human cost, false positives, verification misses, CI queue delay, adoption and willingness-to-pay",
                     "A passing CI job is not a passing commercial differentiation gate"]}
    assert not goldmark["beats_baseline"] and not compose["beats_baseline"]
    print(json.dumps(report,indent=2,sort_keys=True))
if __name__=="__main__":main()
