"""Authentic-source, finite-scope witness for a known Annals formalization gap.

Does not formalize an Annals paper, prove its theorem, or disambiguate author intent.
The 2026 AnnalsChallenge source itself identifies the missing l(F)>=2 hypothesis.
"""

from fractions import Fraction
from hashlib import sha256
from os import environ
from pathlib import Path


ANNALS_COMMIT = "e32eb1411db0d700ca874dd695aea92f78699db8"
ANNALS_BLOB_SHA256 = "7c78b2b9b74582e5a1e683307029e6be1c3df938009969cb9704201cee3280f9"
ANNALS_FILE = "AnnalsChallenge/AnnalsOfMathematics/2021-194-2-FractionalExpectationThresholds.lean"
ANNALS_PAPER = "https://annals.math.princeton.edu/2021/194-2/p02"


def locate_annals_source() -> Path:
    """Read only a pinned checkout, supplied by caller or CI."""
    if environ.get("ANNALS_CHECKOUT"):
        return Path(environ["ANNALS_CHECKOUT"]) / ANNALS_FILE
    here = Path(__file__).resolve()
    for candidate in (
        here.parents[2] / "external" / "AnnalsChallenge" / ANNALS_FILE,
        here.parents[3] / "AnnalsChallenge" / ANNALS_FILE,
    ):
        if candidate.is_file():
            return candidate
    return here.parents[2] / "external" / ANNALS_FILE


def bind_source(path: Path) -> dict:
    if not path.is_file():
        return {"state": "SOURCE_MISSING", "sha256": None, "theorem_proved": False}
    content = path.read_bytes()
    digest = sha256(content).hexdigest()
    if digest != ANNALS_BLOB_SHA256:
        return {"state": "SOURCE_DIGEST_DRIFT", "sha256": digest, "theorem_proved": False}
    text = content.decode("utf-8")
    guard = "(hl𝓕 : 2 ≤ l 𝓕)" in text
    # The source's theorem body is *sorry*; its noncomputable constant K also has sorry.
    admits = "theorem theorem_1_1" in text and " := by\n  sorry" in text
    return {
        "state": "SOURCE_BOUND",
        "sha256": digest,
        "source_commit": ANNALS_COMMIT,
        "has_formal_guard": guard,
        "has_sorry": admits,
        "theorem_proved": False,
        "paper_url": ANNALS_PAPER,
    }


def finite_singleton_countermodel() -> dict:
    """Explicit two-world Bernoulli model for X={0}, F={{0}}.

    For a singleton universe the event 'random subset belongs to F' is exactly
    the selected outcome, with probability p. Thus its 1/2-threshold is 1/2.
    No value of the paper's (finite) K or q_f can alter K*q_f*log(1)=0.
    The actual Mathlib definitions and paper's overall hypotheses are NOT
    reduced here: that semantic bridge is a declared residual.
    """
    universe = frozenset({0})
    empty = frozenset()
    power_set = (empty, universe)
    family = frozenset({universe})
    is_upper = all(
        not (a in family and a.issubset(b)) or b in family
        for a in power_set for b in power_set
    )
    minimal = [a for a in family if not any(b < a for b in family)]
    max_minimal_size = max(map(len, minimal))

    def event_probability(p: Fraction) -> Fraction:
        distribution = {empty: 1 - p, universe: p}
        return sum((prob for world, prob in distribution.items() if world in family), Fraction(0))

    critical_p = Fraction(1, 2)
    assert event_probability(Fraction(0)) == 0
    assert event_probability(critical_p) == critical_p
    assert event_probability(Fraction(1)) == 1
    # The symbolic probability expression is p; Lean separately checks it for all p.
    return {
        "universe": [0],
        "increasing_family": [[0]],
        "bernoulli_worlds": 2,
        "is_upward_closed": is_upper,
        "max_minimal_size": max_minimal_size,
        "critical_probability": critical_p,
        "log_l": 0,  # log(1)=0; Lean certificate checks the zero-factor obstruction.
        "rhs_at_any_finite_constant": 0,
        "unguarded_bound_holds": critical_p <= 0,
        "satisfies_formal_guard": 2 <= max_minimal_size,
    }


def assess(source_path: Path) -> dict:
    source = bind_source(source_path)
    if source["state"] != "SOURCE_BOUND":
        return {
            "terminal": "NAMED_OBSTRUCTION",
            "obstruction": source["state"],
            "source": source,
            "release_authorized": False,
        }
    witness = finite_singleton_countermodel()
    if source["has_formal_guard"] and source["has_sorry"] and not witness["unguarded_bound_holds"]:
        return {
            "terminal": "FINITE_COUNTERMODEL",
            "scope": "SINGLETON_REDUCED_UNGUARDED_FORMULA",
            "source": source,
            "witness": witness,
            "full_paper_theorem": "UNKNOWN",
            "paper_intent": "UNKNOWN_CONTEXT_DEPENDENT",
            "bridge_to_mathlib_definitions": "UNKNOWN_NOT_FORMALLY_CHECKED",
            "comparative_result": "TIE_WITH_EQUALLY_INFORMED_CONVENTIONAL_FINITE_ORACLE",
            "release_authorized": False,
        }
    return {
        "terminal": "NAMED_OBSTRUCTION",
        "obstruction": "SOURCE_OR_WITNESS_NOT_ADMISSIBLE",
        "source": source,
        "release_authorized": False,
    }
