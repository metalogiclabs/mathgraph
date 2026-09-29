"""Incremental frontier extraction for the Crystal corpus linker.

A closed linker state should not be recomputed as a research problem when a new
corpus is added.  Instead, rescan only to construct a deterministic join, then
retain only candidates whose evidence touches the new corpus.  The old closed
state remains frozen authority.
"""

from __future__ import annotations

from typing import Any, Mapping


def extract_incremental_frontier(
    report: Mapping[str, Any],
    *,
    new_corpus: str,
) -> dict[str, Any]:
    equivalence = [
        dict(row)
        for row in report["top_equivalence_candidates"]
        if new_corpus in row.get("corpora", ())
    ]
    implication = [
        dict(row)
        for row in report["top_implication_candidates"]
        if (
            row.get("producer", {}).get("corpus") == new_corpus
            or row.get("consumer", {}).get("corpus") == new_corpus
        )
    ]
    ids = [
        *(str(row["candidate_id"]) for row in equivalence),
        *(str(row["candidate_id"]) for row in implication),
    ]
    if len(ids) != len(set(ids)):
        raise AssertionError("incremental frontier contains duplicate candidate ids")

    return {
        "schema": "mathgraph.incremental-corpus-linker-frontier.v1",
        "status": "CANDIDATE_FRONTIER_ONLY",
        "new_corpus": new_corpus,
        "equivalence_candidate_count": len(equivalence),
        "implication_candidate_count": len(implication),
        "candidate_count": len(ids),
        "equivalence_candidates": equivalence,
        "implication_candidates": implication,
        "candidate_ids": ids,
        "boundary": (
            "Only candidates touching the newly added corpus are reopened. "
            "Previously closed corpus relations remain frozen authority."
        ),
    }


def equivalence_report(frontier: Mapping[str, Any]) -> dict[str, Any]:
    """Present only the new equivalence frontier in classify_report shape."""
    return {
        "top_equivalence_candidates": list(frontier["equivalence_candidates"]),
    }
