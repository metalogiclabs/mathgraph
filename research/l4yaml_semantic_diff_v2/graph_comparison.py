"""Independent finite graph-identity check of MathGraph's Lean graph composer.

Runs against original JPL parseYamlRaw/parseYamlRawIx output on a pinned source
checkout. Uses independent ruamel.yaml Node identity (not JSON equality) as
the structural oracle, with PyYAML cycle identity as a second control.
No universal conformance or scientific warrant follows from finite agreement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import sys
import warnings


def require(p, message):
    if not p:
        raise ValueError(message)


def canonical_signature(root, get_children):
    """Canonical preorder encoding of object identity, including backedges."""
    seen = {}
    records = []
    def go(obj):
        key = id(obj)
        if key in seen:
            return seen[key]
        idx = len(records)
        seen[key] = idx
        records.append(None)
        kind, children = get_children(obj)
        if kind == "sequence":
            records[idx] = ("sequence", tuple(go(c) for c in children))
        elif kind == "mapping":
            records[idx] = ("mapping", tuple((go(k), go(v)) for k, v in children))
        else:
            require(kind == "scalar", "BAD_GRAPH_KIND")
            records[idx] = ("scalar",)
        return idx
    go(root)
    return tuple(records)


def source_graph_signature(graph):
    nodes = graph["nodes"]
    root = graph["root"]
    require(isinstance(nodes, list) and nodes and isinstance(root, int), "BAD_GRAPH")
    require(0 <= root < len(nodes), "BAD_ROOT")
    seen, records = {}, []
    def go(idx):
        require(type(idx) is int and 0 <= idx < len(nodes), "BAD_EDGE")
        if idx in seen:
            return seen[idx]
        outidx = len(records)
        seen[idx] = outidx
        records.append(None)
        n = nodes[idx]
        kind = n["kind"]
        if kind == "scalar":
            require(set(n) == {"kind", "json"} and isinstance(n["json"], str), "BAD_SCALAR")
            json.loads(n["json"])
            records[outidx] = ("scalar",)
        elif kind == "sequence":
            require(set(n) == {"kind", "items"} and isinstance(n["items"], list),
                    "BAD_SEQUENCE")
            records[outidx] = ("sequence", tuple(go(c) for c in n["items"]))
        elif kind == "mapping":
            require(set(n) == {"kind", "pairs"} and isinstance(n["pairs"], list),
                    "BAD_MAPPING")
            require(all(type(p) is list and len(p) == 2 for p in n["pairs"]), "BAD_PAIR")
            records[outidx] = ("mapping", tuple((go(k), go(v)) for k, v in n["pairs"]))
        else:
            raise ValueError("UNKNOWN_NODE_KIND")
        return outidx
    go(root)
    require(len(seen) == len(nodes), "UNREACHABLE_GRAPH_NODES")
    return tuple(records)


def ruamel_signatures(source, parser):
    from ruamel.yaml.nodes import ScalarNode, SequenceNode, MappingNode
    def children(n):
        if isinstance(n, ScalarNode): return ("scalar", None)
        if isinstance(n, SequenceNode): return ("sequence", n.value)
        if isinstance(n, MappingNode): return ("mapping", n.value)
        raise ValueError("UNKNOWN_RUAMEL_NODE_KIND")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        docs = list(parser.compose_all(source))
    return tuple(canonical_signature(n, children) for n in docs)


def normalized_projection(graph):
    nodes = graph["nodes"]
    active = set()
    def visit(idx):
        require(idx not in active, "CYCLIC_PROJECTION_NOT_ALLOWED")
        active.add(idx)
        n = nodes[idx]
        if n["kind"] == "scalar":
            result = json.loads(n["json"])
        elif n["kind"] == "sequence":
            result = [visit(x) for x in n["items"]]
        elif n["kind"] == "mapping":
            pairs = [(visit(k), visit(v)) for k, v in n["pairs"]]
            result = {}
            for k, v in pairs:
                require(not isinstance(k, (list, dict)), "UNSUPPORTED_COMPLEX_JSON_KEY")
                kk = "null" if k is None else ("true" if k is True else
                        "false" if k is False else str(k))
                result[kk] = v
        else:
            raise ValueError("BAD_PROJECTION_KIND")
        active.remove(idx)
        return result
    return visit(graph["root"])


def signature(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def assert_pyyaml_cycles():
    import yaml
    examples = ["&x [*x]", "&x {a: *x}"]
    for source in examples:
        n = yaml.compose(source, Loader=yaml.SafeLoader)
        if source.startswith("&x ["):
            require(n.value[0] is n, "PYYAML_SEQUENCE_NOT_CYCLIC")
        else:
            require(n.value[0][1] is n, "PYYAML_MAPPING_NOT_CYCLIC")


def check(oracle_path: Path, native_paths: list[Path],
          special_path: Path, report_path: Path, source_sha: str,
          ruamel_path: Path, pyyaml_path: Path):
    require(len(source_sha) == 40 and all(c in "0123456789abcdef" for c in source_sha),
            "BAD_SOURCE_SHA")
    sys.path.insert(0, str(ruamel_path.resolve()))
    sys.path.insert(0, str(pyyaml_path.resolve()))
    from ruamel.yaml import YAML
    from ruamel.yaml import __version__ as ruamel_version
    import yaml
    require(ruamel_version == "0.18.17", "RUAMEL_VERSION_DRIFT")
    require(yaml.__version__ == "6.0.3", "PYYAML_VERSION_DRIFT")
    parser = YAML(typ="safe", pure=True)
    parser.version = (1, 2)
    assert_pyyaml_cycles()

    oracle_bytes = oracle_path.read_bytes()
    oracle = json.loads(oracle_bytes)
    require(oracle["oracle_version"] == "0.18.17" and
            len(oracle["cases"]) == 532, "ORACLE_DRIFT")
    observed = []
    for path in native_paths:
        entries = [json.loads(x) for x in path.read_text().splitlines() if x]
        observed += entries
    require(len(observed) == 532, "NATIVE_COUNT_DRIFT")
    cases = oracle["cases"]
    family = defaultdict(lambda: {"count": 0, "graph_ok": 0, "value_ok": 0})
    graph_ok = value_ok = both_ok = 0
    negatives = []
    for source, row in zip(cases, observed):
        require(row["input"] == source["input"], "INPUT_IDENTITY_DRIFT")
        require(set(row) == {"input", "legacy", "indexed"}, "BAD_NATIVE_ROW")
        for path in ("legacy", "indexed"):
            require(row[path]["status"] == "ok", "NATIVE_REFUSED_VALID_ORACLE")
            require(set(row[path]) == {"status", "graphs"}, "BAD_GRAPH_OUTPUT")
        require(row["legacy"]["graphs"] == row["indexed"]["graphs"],
                "NATIVE_GRAPH_PATH_DISAGREEMENT")
        graphs = row["legacy"]["graphs"]
        oracle_graphs = ruamel_signatures(source["input"], parser)
        require(len(graphs) == len(oracle_graphs), "DOCUMENT_COUNT_MISMATCH")
        g = tuple(source_graph_signature(graph) for graph in graphs)
        ok_graph = g == oracle_graphs
        values = [normalized_projection(graph) for graph in graphs]
        expected_value = source["expected"]
        ok_value = (len(values) == 1 and signature(values[0]) == signature(expected_value))
        if len(values) != 1:  # The oracle expected value is one document (532-case grammar).
            ok_value = False
        f = family[source["suite"] + "." + source["family"]]
        f["count"] += 1
        f["graph_ok"] += int(ok_graph)
        f["value_ok"] += int(ok_value)
        graph_ok += ok_graph
        value_ok += ok_value
        both_ok += ok_graph and ok_value
        if not (ok_graph and ok_value) and len(negatives) < 16:
            negatives.append({"family": source["family"], "input": source["input"],
                              "graph": ok_graph, "value": ok_value,
                              "nodes": len(graphs[0]["nodes"]) if graphs else 0})

    specials = [json.loads(line) for line in special_path.read_text().splitlines() if line]
    expected = {
        "&x [*x]": "cyclic_sequence",
        "&x {a: *x}": "cyclic_mapping",
        "[&x [&x 1], *x]": "nested_rebinding",
        "[&x 1, *x, &x 9, *x]": "linear_rebinding",
        "[*x]": "undefined_alias",
        "&x [*x, *y]": "undefined_inside_cycle",
        "---\n&x 1\n---\n*x\n": "cross_document",
    }
    require({r["input"] for r in specials} == set(expected), "CONTROL_INPUT_DRIFT")
    controls = {}
    for row in specials:
        source = row["input"]
        mode = expected[source]
        require(row["legacy"] == row["indexed"], "CONTROL_NATIVE_PATH_DISAGREEMENT")
        resp = row["legacy"]
        if mode.startswith("undefined") or mode == "cross_document":
            require(resp["status"] == "error", "UNDEFINED_ALIAS_NOT_REJECTED")
            controls[mode] = "REFUSED"
            continue
        require(resp["status"] == "ok" and len(resp["graphs"]) == 1,
                "VALID_ANCHOR_REFUSED")
        graph = resp["graphs"][0]
        require(source_graph_signature(graph) == ruamel_signatures(source, parser)[0],
                "CONTROL_ORACLE_GRAPH_DISAGREE")
        root = graph["root"]
        ns = graph["nodes"]
        if mode == "cyclic_sequence":
            require(ns[root]["kind"] == "sequence" and ns[root]["items"][0] == root,
                    "SELF_SEQUENCE_IDENTITY_FALSE")
        if mode == "cyclic_mapping":
            require(ns[root]["kind"] == "mapping" and ns[root]["pairs"][0][1] == root,
                    "SELF_MAPPING_IDENTITY_FALSE")
        if mode == "nested_rebinding":
            require(ns[root]["kind"] == "sequence" and
                    ns[ns[root]["items"][0]]["kind"] == "sequence" and
                    ns[root]["items"][1] == ns[ns[root]["items"][0]]["items"][0],
                    "INNER_REBINDING_WRONG_NODE")
        if mode == "linear_rebinding":
            xs = ns[root]["items"]
            require(xs[0] == xs[1] and xs[2] == xs[3] and xs[0] != xs[2],
                    "LINEAR_REBINDING_WRONG_NODE")
        controls[mode] = "PASS"

    report = {
        "source_commit": source_sha, "source_edited": False,
        "status": "BOUNDED_WARRANTED" if both_ok == 532 else "CANDIDATE_PARTIAL",
        "population": 532, "graph_agreement": graph_ok,
        "acyclic_value_agreement": value_ok, "joint_agreement": both_ok,
        "families": dict(sorted(family.items())), "counterexamples": negatives,
        "controls": controls,
        "independent_composers": ["ruamel.yaml==0.18.17", "PyYAML==6.0.3"],
        "oracle_sha256": hashlib.sha256(oracle_bytes).hexdigest(),
        "native_sha256": {x.name: hashlib.sha256(x.read_bytes()).hexdigest()
                          for x in native_paths + [special_path]},
        "general_yaml_conformance": "UNKNOWN", "formal_correspondence_theorem": "UNKNOWN",
        "release_authority": "NOT_AUTHORIZED",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "graph_agreement",
                                             "acyclic_value_agreement", "joint_agreement",
                                             "controls")}, sort_keys=True))
    # Fail the strong experiment visibly, retaining report and logs, if discrepancies remain.
    require(graph_ok == 532 and value_ok == 532, "GRAPH_OR_VALUE_DISAGREEMENT")
    return report


def cli(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--oracle", type=Path, required=True)
    p.add_argument("--anchor", type=Path, required=True)
    p.add_argument("--ordinary", type=Path, required=True)
    p.add_argument("--special", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--ruamel-path", type=Path, required=True)
    p.add_argument("--pyyaml-path", type=Path, required=True)
    a = p.parse_args(argv)
    return check(a.oracle, [a.anchor, a.ordinary], a.special, a.report,
                 a.source_sha, a.ruamel_path, a.pyyaml_path)


if __name__ == "__main__":
    cli()
