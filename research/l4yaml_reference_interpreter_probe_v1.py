"""Independent third-party YAML parser observation (not normative formal warrant).

A real PyYAML SafeLoader is the second executable observer for the exact
recursive-anchor separator already present in the JPL Lean model. It is not
used to supply labels to, or replace, the official yaml-test-suite.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


CASES = [
    ("recursive-sequence", "&x [*x]\n", "ACCEPT_SELF_CYCLE", 0),
    ("recursive-sequence-with-scalar", "&x [item, *x]\n", "ACCEPT_SELF_CYCLE", 1),
    ("sibling-alias", "- &x item\n- *x\n", "ACCEPT", None),
    ("missing-alias", "*x\n", "REJECT", None),
    ("cross-document-alias", "---\n&x item\n...\n---\n*x\n", "REJECT", None),
    ("quoted-alias-looking-text", 'message: "*x"\n', "ACCEPT", None),
    ("literal-alias-looking-text", "message: |\n  *missing\n", "ACCEPT", None),
]


def run(out: Path) -> dict[str, Any]:
    results = []
    for label, source, expected, index in CASES:
        try:
            docs = list(yaml.safe_load_all(source))
            observed = "ACCEPT"
            if expected == "ACCEPT_SELF_CYCLE":
                if len(docs) != 1 or not isinstance(docs[0], list) or docs[0][index] is not docs[0]:
                    observed = "ACCEPT_WITHOUT_EXPECTED_CYCLE"
                else:
                    observed = "ACCEPT_SELF_CYCLE"
        except yaml.YAMLError as exc:
            observed = "REJECT"
            diagnostic = type(exc).__name__
        else:
            diagnostic = None
        if observed != expected:
            raise AssertionError(f"reference interpreter disagrees at {label}: {observed!r} != {expected!r}")
        results.append({
            "id": label, "input_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "expected_from_named_control": expected,
            "observed": observed, "diagnostic": diagnostic,
        })
    output = {
        "schema": "mathgraph.third-party-yaml-observer-v1",
        "interpreter": "PyYAML SafeLoader",
        "interpreter_version": yaml.__version__,
        "cases": len(results),
        "agreements": len(results),
        "normative_yaml_language_certification": "NOT_PROVED",
        "jpl_parser_observation": "NOT_RUN_BY_THIS_PROBE",
        "source_to_event_completeness": "UNKNOWN",
        "third_party_observations": results,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print("MATHGRAPH_REFERENCE_YAML_SELF_CYCLE_CORROBORATION_GREEN")
    return output


if __name__ == "__main__":
    run(Path("evidence/l4yaml-label-audit/reference-observer.json"))
