"""Finite proof-versus-intent experiment. No natural-language interpretation claim.

The source intent is *independently and manually declared*, not inferred from
English or from the proof. Finite observations never establish global validity.
"""

from itertools import product


def _threshold_property(n: int) -> bool:
    return n + n > n + 1


def assess_threshold_claim(*, source_min: int, proof_min: int, upper_bound: int) -> dict:
    """Compare two declared domains on 0..upper_bound, propose a guard only."""
    if min(source_min, proof_min) < 0 or upper_bound < 0:
        raise ValueError("finite Nat scope and guards must be nonnegative")
    admitted = [n for n in range(upper_bound + 1) if n >= source_min]
    formal = [n for n in range(upper_bound + 1) if n >= proof_min]
    intent_failures = [n for n in admitted if not _threshold_property(n)]
    formal_failures = [n for n in formal if not _threshold_property(n)]
    # Among *threshold guards only*, find the weakest finite repair. This does
    # not change source intent or establish an infinite Nat proof of the repair.
    repairs = [k for k in range(source_min, upper_bound + 1)
               if all(_threshold_property(n) for n in range(k, upper_bound + 1))]
    return {
        "formal_finite_check": ("COUNTEREXAMPLE" if formal_failures else
                                "PASS" if formal else "UNKNOWN_VACUOUS_FORMAL_SCOPE"),
        "intent_finite_check": ("COUNTEREXAMPLE" if intent_failures else
                                "FINITE_SUPPORTED_ONLY" if admitted else
                                "UNKNOWN_NO_ADMITTED_SOURCE_CASES"),
        "counterexample": intent_failures[0] if intent_failures else None,
        "action_authorized": False,
        "minimal_repair_guard": (f"n >= {repairs[0]}" if repairs and intent_failures else None),
        "repair_status": ("CANDIDATE_REQUIRES_SOURCE_APPROVAL_AND_PROOF"
                          if repairs and intent_failures else "NO_REPAIR_WARRANTED"),
        "retained_proof_guard": f"n >= {proof_min}",
        "observed_source_cases": len(admitted),
        "observed_proof_cases": len(formal),
        "unobserved_infinite_tail": True,
    }


def identity(data: str) -> str:
    return data


def tiny_run_compress(data: str) -> str:
    if data in ("0000", "1111"):
        return "R" + data[0] + "4"
    return data


def tiny_run_decompress(data: str) -> str:
    if data in ("R04", "R14"):
        return data[1] * 4
    return data


def assess_compression_claim(compress, decompress) -> dict:
    """Independent finite intent: binary words length <= 4; runs of four shrink."""
    words = ["".join(bits) for n in range(5) for bits in product("01", repeat=n)]
    bad_roundtrips = [w for w in words if decompress(compress(w)) != w]
    size_targets = ["0000", "1111"]
    bad_sizes = [w for w in size_targets if len(compress(w)) >= len(w)]
    return {
        "roundtrip_finite_pass": not bad_roundtrips,
        "size_counterexample": bad_sizes[0] if bad_sizes else None,
        "release_authorized": False,
        "size_finite_check": "COUNTEREXAMPLE" if bad_sizes else "FINITE_SUPPORTED_ONLY",
        "roundtrip_counterexample": bad_roundtrips[0] if bad_roundtrips else None,
        "observed_binary_words": len(words),
        "size_target_words": len(size_targets),
        "unobserved_unbounded_inputs": True,
    }
