"""Check receipts emitted by the actual native graph builder, not a second ID allocator.

The underlying L4YAML raw trees and scanner are unmodified. For every successful
document, a fresh ID must be minted by a nodeStart receipt, the IDs must cover
exactly the emitted nodes, and an aliasTo receipt must resolve to the latest
preceding anchor binding. Projection of those receipts to &name/*name must
match the original scanner source-token order.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path


def require(ok, message):
    if not ok:
        raise ValueError(message)


def inspect_graph(graph):
    require(set(graph) == {"root", "nodes", "receipts"}, "GRAPH_FIELDS_DRIFT")
    nodes, receipts = graph["nodes"], graph["receipts"]
    require(type(nodes) is list and type(receipts) is list, "BAD_GRAPH_RECEIPTS")
    require((len(nodes) == 0 and graph["root"] is None) or
            (type(graph["root"]) is int and graph["root"] < len(nodes)),
            "BAD_ROOT")
    active = {}
    starts = 0
    projected = []
    alias_count = 0
    for event in receipts:
        require(type(event) is dict and event.get("event") in ("nodeStart", "aliasTo"),
                "UNKNOWN_RECEIPT")
        if event["event"] == "nodeStart":
            require(set(event) == {"event", "id", "anchor"}, "NODE_RECEIPT_DRIFT")
            id_ = event["id"]
            require(type(id_) is int and id_ == starts and 0 <= id_ < len(nodes),
                    "NOT_ACTUAL_FRESH_NODE_ID")
            starts += 1
            anchor = event["anchor"]
            require(anchor is None or (type(anchor) is str and anchor),
                    "INVALID_RECEIPT_ANCHOR")
            if anchor is not None:
                active[anchor] = id_
                projected.append("&" + anchor)
        else:
            require(set(event) == {"event", "name", "target"},
                    "ALIAS_RECEIPT_DRIFT")
            name, target = event["name"], event["target"]
            require(type(name) is str and name, "INVALID_ALIAS_NAME")
            require(type(target) is int and name in active and target == active[name],
                    "ALIAS_NOT_LATEST_DECLARED_NODE")
            require(target < starts and target < len(nodes), "ALIAS_TARGET_NOT_ALLOCATED")
            projected.append("*" + name)
            alias_count += 1
    require(starts == len(nodes), "UNRECORDED_NODE_ALLOCATION")
    return projected, starts, alias_count


def inspect_row(row, original):
    require(set(row) == {"input", "scanner", "legacy", "indexed"},
            "WITNESS_ROW_FIELDS_DRIFT")
    require(row["input"] == original, "INPUT_IDENTITY_DRIFT")
    require(row["legacy"] == row["indexed"], "PARSER_WITNESSES_DIVERGE")
    v = row["legacy"]
    require(type(v) is dict and v.get("status") in ("ok", "error"),
            "BAD_WITNESS_RESULT")
    if v["status"] == "error":
        require(set(v) == {"status", "error"}, "BAD_ERROR_FIELDS")
        return "REFUSED", 0, 0
    require(set(v) == {"status", "graphs"} and type(v["graphs"]) is list,
            "BAD_GRAPH_SUCCESS")
    require(type(row["scanner"]) is list, "SCANNER_REFUSED_ACCEPTED_GRAPH")
    projected = []
    nodes = aliases = 0
    for graph in v["graphs"]:
        events, n, a = inspect_graph(graph)
        projected.extend(events)
        nodes += n
        aliases += a
    require(projected == row["scanner"], "SOURCE_TO_ALLOCATED_ID_EVENT_DRIFT")
    return "MATCH", nodes, aliases


def main():
    p = argparse.ArgumentParser()
    for k in ("oracle", "anchor", "ordinary", "special", "report"):
        p.add_argument("--" + k, required=True, type=Path)
    p.add_argument("--source-sha", required=True)
    args = p.parse_args()
    require(len(args.source_sha) == 40 and
            all(ch in "0123456789abcdef" for ch in args.source_sha),
            "SOURCE_COMMIT_NOT_IMMUTABLE")
    oracle_data = args.oracle.read_bytes()
    cases = json.loads(oracle_data)["cases"]
    require(len(cases) == 532, "CASE_SET_CHANGED")
    stats = {"cases": 0, "matched": 0, "allocated_nodes": 0, "aliases": 0}
    digest = {}
    exemplar = None
    for suite, path in (("anchor", args.anchor), ("ordinary", args.ordinary)):
        rows = [json.loads(line) for line in path.read_text().splitlines() if line]
        expected = [case for case in cases if case["suite"] == suite]
        require(len(rows) == len(expected), "WITNESS_COUNT_DRIFT")
        digest[suite] = hashlib.sha256(path.read_bytes()).hexdigest()
        for row, case in zip(rows, expected):
            result, nodes, aliases = inspect_row(row, case["input"])
            require(result == "MATCH", "VALID_CORPUS_GRAPH_REFUSED")
            stats["cases"] += 1
            stats["matched"] += 1
            stats["allocated_nodes"] += nodes
            stats["aliases"] += aliases
            if exemplar is None and aliases:
                exemplar = (row, case["input"])
    require(stats["matched"] == 532 and stats["aliases"] > 0, "NO_LIVE_ALIAS_CONTROL")

    specials = [json.loads(line) for line in args.special.read_text().splitlines() if line]
    expected_controls = {
        "&x [*x]": "MATCH",
        "&x {a: *x}": "MATCH",
        "[&x [&x 1], *x]": "MATCH",
        "[&x 1, *x, &x 9, *x]": "MATCH",
        "[*x]": "REFUSED",
        "&x [*x, *y]": "REFUSED",
        "---\n&x 1\n---\n*x\n": "REFUSED",
    }
    require({r["input"] for r in specials} == set(expected_controls),
            "SPECIAL_SET_CHANGED")
    for row in specials:
        result, _, _ = inspect_row(row, row["input"])
        require(result == expected_controls[row["input"]],
                "SPECIAL_CONTROL_FAILED:" + repr(row["input"]))

    # Intentionally falsify an observed alias receipt; checker MUST reject
    # this corrupted evidence. Never treat a successful weak checker as proof.
    require(exemplar is not None, "NO_CORRUPTION_TARGET")
    row, source = exemplar
    counterfeit = copy.deepcopy(row)
    changes = 0
    for path_name in ("legacy", "indexed"):
        modified = False
        for graph in counterfeit[path_name]["graphs"]:
            for item in graph["receipts"]:
                if item["event"] == "aliasTo" and not modified:
                    item["target"] += 9999
                    changes += 1
                    modified = True
                    break
            if modified:
                break
    require(changes == 2 and counterfeit["legacy"] == counterfeit["indexed"],
            "TAMPER_NOT_PATH_CONSISTENT")
    try:
        inspect_row(counterfeit, source)
    except ValueError:
        tampering_rejected = True
    else:
        tampering_rejected = False
    require(tampering_rejected, "TAMPERED_ALIAS_WITNESS_ACCEPTED")

    result = {
        "status": "BOUNDED_WARRANTED",
        "source_commit": args.source_sha,
        **stats,
        "negative_controls": {"aliased_target_tamper": "REJECTED",
                              "invalid_aliases": 3},
        "raw_ast_source_identity": "PINNED_NATIVE_EXECUTION",
        "arbitrary_source_to_trace_theorem": "UNKNOWN",
        "complete_ast_to_graph_theorem": "UNKNOWN",
        "general_yaml_conformance": "UNKNOWN",
        "release_authority": "NOT_AUTHORIZED",
        "oracle_sha256": hashlib.sha256(oracle_data).hexdigest(),
        "witness_sha256": digest,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in
        ("status", "cases", "matched", "allocated_nodes", "aliases")},
        sort_keys=True))


if __name__ == "__main__":
    main()
