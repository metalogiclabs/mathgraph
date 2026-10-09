#!/usr/bin/env python3
"""WattBot: test the missing-document distinction without answer/model leakage.

All strategy selection is on development TRAIN questions. Frozen TRAIN holdout
is a reused confirmatory diagnostic, not independent Kaggle or scientific
evidence. Gold citations are never used to retrieve or reorder any contexts.
Never read or score the protected TEST labels.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import tempfile

import submit_full_reader as source
from holdout_probe import is_holdout
from train_probe import parse_refs
from wattbot import ranked, tokens

TOP_K = 6
SEARCH_LIMIT = 100
POLICIES = ("legacy", "cap1", "cap2", "cap3", "four_sources_first", "question_adaptive")
MULTI = frozenset(("compare", "comparing", "comparison", "versus", "vs", "both",
                   "another", "between", "different", "multiple", "two", "three",
                   "contradict", "combine", "combined", "together", "across"))


class FrozenBM25:
    """Cache invariant corpus statistics; preserve the legacy BM25 ordering."""
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.n = len(chunks)
        body = [Counter(tokens(c["text"])) for c in self.chunks]
        self.avg = max(1, sum(sum(x.values()) for x in body) / max(1, self.n))
        self.postings = defaultdict(list)
        df = Counter(t for freq in body for t in freq)
        for i, freq in enumerate(body):
            length_norm = 0.25 + 0.75 * sum(freq.values()) / self.avg
            for t, count in freq.items():
                self.postings[t].append((i, count, length_norm))
        self.idf = {
            t: math.log(1 + (self.n - frequency + .5) / (frequency + .5))
            for t, frequency in df.items()
        }

    def ranked(self, question, top_k=SEARCH_LIMIT):
        totals = defaultdict(float)
        for t in set(tokens(question)):
            for i, freq, length_norm in self.postings.get(t, ()):
                totals[i] += self.idf[t] * freq * 2.2 / (freq + 1.2 * length_norm)
        ordered = sorted(((score, i) for i, score in totals.items() if score > 0),
                         key=lambda x: (-x[0],
                                        self.chunks[x[1]]["ref_id"],
                                        self.chunks[x[1]]["page"], x[1]))
        return [dict(self.chunks[i], score=round(score, 8))
                for score, i in ordered[:top_k]]


def choose_pages(question, all_hits, policy):
    pages = [p for p in all_hits if p["page"] > 0]
    if policy == "legacy":
        return pages[:TOP_K]
    if policy == "question_adaptive":
        q = set(tokens(question))
        cap = 1 if q.intersection(MULTI) else 2
    else:
        cap = {"cap1": 1, "cap2": 2, "cap3": 3,
               "four_sources_first": 2}[policy]
    chosen = []
    counts = Counter()
    if policy == "four_sources_first":
        for hit in pages:
            if counts[hit["ref_id"]] == 0:
                chosen.append(hit)
                counts[hit["ref_id"]] = 1
                if len(chosen) == min(4, TOP_K):
                    break
    for hit in pages:
        if len(chosen) >= TOP_K:
            break
        if hit in chosen or counts[hit["ref_id"]] >= cap:
            continue
        chosen.append(hit)
        counts[hit["ref_id"]] += 1
    # Preserve ranked source order to distinguish only the set of candidates.
    positions = {id(p): i for i, p in enumerate(pages)}
    return sorted(chosen, key=lambda p: positions[id(p)])


def evaluate(rows, index):
    totals = {p: Counter() for p in POLICIES}
    grouped = {p: defaultdict(Counter) for p in POLICIES}
    for row in rows.to_dict("records"):
        refs = set(parse_refs(row["ref_id"]))
        if not refs:
            for p in POLICIES:
                totals[p]["unanswerable"] += 1
            continue
        question = str(row["question"])
        hits = index.ranked(question, SEARCH_LIMIT)
        kgroup = ("one" if len(refs) == 1 else
                  "two" if len(refs) == 2 else "three_plus")
        for p in POLICIES:
            selected = choose_pages(question, hits, p)
            found = {s["ref_id"] for s in selected}
            covered = len(refs.intersection(found))
            target = totals[p]
            target["questions"] += 1
            target["gold_refs"] += len(refs)
            target["retrieved_gold_refs"] += covered
            target["all_gold_present"] += int(covered == len(refs))
            target["any_gold_present"] += int(covered > 0)
            target["retrieved_source_distinct"] += len(found)
            g = grouped[p][kgroup]
            g["questions"] += 1
            g["all_gold_present"] += int(covered == len(refs))
            g["retrieved_gold_refs"] += covered
            g["gold_refs"] += len(refs)
    return {p: summarize(totals[p], grouped[p]) for p in POLICIES}


def summarize(t, group):
    count = max(1, t["questions"])
    def ratios(g):
        return {
            "questions": g["questions"],
            "complete_gold_set_share": round(g["all_gold_present"] / max(1, g["questions"]), 6),
            "gold_reference_recall": round(g["retrieved_gold_refs"] / max(1, g["gold_refs"]), 6),
        }
    return dict(ratios(t), any_gold_share=round(t["any_gold_present"]/count, 6),
                mean_distinct_sources=round(t["retrieved_source_distinct"]/count, 4),
                na_excluded=t["unanswerable"],
                by_gold_source_count={k: ratios(v) for k,v in group.items()})


def choose_dev_policy(dev_metrics):
    # Predeclare a dev-only selection objective: exact coverage first,
    # then multi-source coverage, and finally aggregate source recall.
    def objective(p):
        a = dev_metrics[p]
        g = a["by_gold_source_count"]
        multi = sum(g.get(k, {}).get("all_gold_present", 0)
                    for k in ())  # always zero; see weighted counter below
        multi_n = sum(g.get(k, {}).get("questions", 0)
                      for k in ("two", "three_plus"))
        multi_covered = sum(g.get(k, {}).get("complete_gold_set_share", 0)
                            * g.get(k, {}).get("questions", 0)
                            for k in ("two", "three_plus"))
        return (a["complete_gold_set_share"],
                multi_covered / max(1, multi_n),
                a["gold_reference_recall"],
                -POLICIES.index(p))
    return max(POLICIES, key=objective)


def self_test():
    sample = [
        {"ref_id": "a", "page": 1,
         "text": "The electricity demand was 1287 MWh. 2025 electricity."},
        {"ref_id": "a", "page": 2,
         "text": "The thermal demand was 2030 MWh. Electricity demand."},
        {"ref_id": "b", "page": 2,
         "text": "In 2025 home energy demand was 10.8 MWh."},
        {"ref_id": "c", "page": 0,
         "text": "Electricity demand analysis"},
        {"ref_id": "d", "page": 3,
         "text": "Energy demand and datacenter demand in 2025."},
    ]
    index = FrozenBM25(sample)
    for q in ("electricity demand 2025", "home energy 10.8", "absent source"):
        expected = ranked(q, sample, len(sample))
        result = index.ranked(q, len(sample))
        assert [(x["ref_id"],x["page"],x["score"]) for x in expected] == [
            (x["ref_id"],x["page"],x["score"]) for x in result], q
    x = index.ranked("demand electricity 2025")
    for p in POLICIES:
        chosen = choose_pages("Compare two papers on energy demand", x, p)
        assert len(chosen) <= TOP_K
        assert all(v["page"] > 0 for v in chosen)
        assert all(v in x for v in chosen)
    assert len({x["ref_id"] for x in choose_pages("two papers", x, "cap1")}) == len(
        choose_pages("two papers", x, "cap1"))
    assert is_holdout("anything") in (True,False)
    print("WATTBOT_SOURCE_REFINEMENT_SELF_TEST=PASS")


def run(official_zip):
    self_test()
    train, sources, _ = source.pinned_data(official_zip)
    dev = train[~train["id"].astype(str).map(is_holdout)]
    holdout = train[train["id"].astype(str).map(is_holdout)]
    if len(dev) != 182 or len(holdout) != 63:
        raise ValueError("Frozen development/holdout split has changed")
    with tempfile.TemporaryDirectory(prefix="wattbot_source_distinctions_") as tmp:
        docs, chunks, manifest = source.corpus(train, sources, Path(tmp))
        index = FrozenBM25(chunks)
        dev_scores = evaluate(dev, index)
        chosen = choose_dev_policy(dev_scores)
        # Holdout used only AFTER policy freeze. Never feed labels to retrieval.
        holdout_scores = evaluate(holdout, index)
    base = holdout_scores["legacy"]
    proposal = holdout_scores[chosen]
    result = {
        "kind": "frozen_train_citation_retrieval_only",
        "full_document_manifest": manifest,
        "source_index_size": len(chunks),
        "dev_rows": len(dev), "holdout_rows": len(holdout),
        "policy_selection": "development-only complete gold set > multi-reference recall > total recall",
        "chosen_policy": chosen,
        "dev_scores": dev_scores,
        "holdout_scores": holdout_scores,
        "holdout_change": {
            "complete_gold_set_delta": round(
                proposal["complete_gold_set_share"] - base["complete_gold_set_share"], 6),
            "gold_reference_recall_delta": round(
                proposal["gold_reference_recall"] - base["gold_reference_recall"], 6),
        },
        "boundary": "TRAIN labels only for post-retrieval diagnosis; reused holdout, never test labels; "
                    "gold citation in retrieved top-6 is an upper bound, not answer correctness.",
    }
    print("WATTBOT_SOURCE_REFINEMENT=" + json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--official-zip")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    elif args.official_zip:
        run(args.official_zip)
    else:
        parser.error("Provide --self-test or --official-zip")
