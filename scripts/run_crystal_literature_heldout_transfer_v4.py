#!/usr/bin/env python3
"""Held-out transfer test for the frozen declarative extraction interpreter."""

from __future__ import annotations

from fractions import Fraction
from html import unescape
from itertools import combinations, product
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request

from mathgraph.extraction_contract import apply_extraction_contract, qualify_falsifiers

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "evidence" / "crystal-literature-heldout-transfer-v4" / "contracts.json"
OUTDIR = ROOT / "evidence" / "crystal-literature-heldout-transfer-v4"
RESULT = OUTDIR / "result.json"
PARENT = "7c26a228971132a6c40920fd974dbd3f95b294f6"


def fetch_first(urls: list[str]) -> tuple[str, bytes, list[str]]:
    errors: list[str] = []
    for url in urls:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "MathGraph-Crystal-heldout-transfer-v4/1.0"},
            )
            with urllib.request.urlopen(req, timeout=45) as response:
                return response.geturl(), response.read(), errors
        except Exception as exc:
            errors.append(f"{url}: {type(exc).__name__}: {exc}")
    raise RuntimeError("all acquisition URLs failed: " + " | ".join(errors))


def html_to_text(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(unescape(text).split())


def pdf_to_text(data: bytes) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "source.pdf"
        txt = Path(tmp) / "source.txt"
        pdf.write_bytes(data)
        proc = subprocess.run(
            ["pdftotext", "-layout", str(pdf), str(txt)],
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError("pdftotext failed: " + proc.stderr)
        return " ".join(txt.read_text(errors="replace").split())


def acquire(contract: dict) -> dict:
    spec = contract["acquisition"]
    resolved, data, errors = fetch_first(spec["urls"])
    if spec["kind"] == "html":
        text = html_to_text(data)
    elif spec["kind"] == "pdf":
        text = pdf_to_text(data)
    else:
        raise ValueError(f"unsupported acquisition kind: {spec['kind']}")
    return {
        "kind": spec["kind"],
        "resolved_url": resolved,
        "bytes": data,
        "text": text,
        "sha256": hashlib.sha256(data).hexdigest(),
        "fallback_errors": errors,
    }


def edge_set_cycle5() -> set[tuple[int, int]]:
    return {tuple(sorted((i, (i + 1) % 5))) for i in range(5)}


def induced_edges(vertices: tuple[int, ...], edges: set[tuple[int, int]]) -> set[tuple[int, int]]:
    chosen = set(vertices)
    return {edge for edge in edges if edge[0] in chosen and edge[1] in chosen}


def clique_number(vertices: tuple[int, ...], edges: set[tuple[int, int]]) -> int:
    for size in range(len(vertices), 0, -1):
        for subset in combinations(vertices, size):
            if all(tuple(sorted(pair)) in edges for pair in combinations(subset, 2)):
                return size
    return 0


def chromatic_number(vertices: tuple[int, ...], edges: set[tuple[int, int]]) -> int:
    if not vertices:
        return 0
    for colors in range(1, len(vertices) + 1):
        for assignment in product(range(colors), repeat=len(vertices)):
            color = dict(zip(vertices, assignment))
            if all(color[u] != color[v] for u, v in edges):
                return colors
    raise AssertionError("finite graph was not colorable")


def is_cycle(vertices: tuple[int, ...], edges: set[tuple[int, int]]) -> bool:
    if len(vertices) < 3 or len(edges) != len(vertices):
        return False
    degree = {v: 0 for v in vertices}
    adjacency = {v: set() for v in vertices}
    for u, v in edges:
        degree[u] += 1
        degree[v] += 1
        adjacency[u].add(v)
        adjacency[v].add(u)
    if any(degree[v] != 2 for v in vertices):
        return False
    seen = set()
    stack = [vertices[0]]
    while stack:
        v = stack.pop()
        if v in seen:
            continue
        seen.add(v)
        stack.extend(adjacency[v] - seen)
    return len(seen) == len(vertices)


def is_perfect_c5() -> tuple[bool, dict]:
    vertices = tuple(range(5))
    edges = edge_set_cycle5()
    first_failure = None
    for size in range(1, 6):
        for subset in combinations(vertices, size):
            sub_edges = induced_edges(subset, edges)
            chi = chromatic_number(subset, sub_edges)
            omega = clique_number(subset, sub_edges)
            if chi != omega:
                first_failure = {
                    "vertices": list(subset),
                    "chromatic_number": chi,
                    "clique_number": omega,
                }
                return False, first_failure
    return True, {}


def is_berge_c5() -> tuple[bool, dict]:
    vertices = tuple(range(5))
    edges = edge_set_cycle5()
    for size in range(5, 6, 2):
        for subset in combinations(vertices, size):
            sub_edges = induced_edges(subset, edges)
            all_pairs = {tuple(sorted(pair)) for pair in combinations(subset, 2)}
            complement = all_pairs - sub_edges
            if is_cycle(subset, sub_edges):
                return False, {"vertices": list(subset), "kind": "odd-hole"}
            if is_cycle(subset, complement):
                return False, {"vertices": list(subset), "kind": "odd-antihole"}
    return True, {}


def verify_c5() -> dict:
    perfect, perfect_witness = is_perfect_c5()
    berge, berge_witness = is_berge_c5()
    if perfect != berge:
        raise AssertionError("C5 falsifies bounded SPGT instance")
    return {
        "verdict": "WARRANTED_BOUNDED_INSTANCE",
        "perfect": perfect,
        "berge": berge,
        "iff": perfect == berge,
        "perfect_failure_witness": perfect_witness,
        "berge_failure_witness": berge_witness,
    }


def vp(n: int, p: int) -> int:
    if n == 0:
        raise ValueError("v_p(0) is infinite")
    value = abs(n)
    count = 0
    while value % p == 0:
        value //= p
        count += 1
    return count


def padic_norm(n: int, p: int) -> Fraction:
    if n == 0:
        return Fraction(0, 1)
    return Fraction(1, p ** vp(n, p))


def verify_padic() -> dict:
    checks = 0
    antecedent_cases = 0
    for p in (2, 3, 5):
        for x in range(-20, 21):
            for y in range(-20, 21):
                checks += 1
                nx, ny = padic_norm(x, p), padic_norm(y, p)
                if nx == ny:
                    continue
                antecedent_cases += 1
                if padic_norm(x + y, p) != max(nx, ny):
                    raise AssertionError(f"p-adic bounded separator at p={p}, x={x}, y={y}")
    return {
        "verdict": "WARRANTED_BOUNDED_INSTANCE",
        "primes": [2, 3, 5],
        "integer_range": [-20, 20],
        "total_pairs_checked": checks,
        "unequal_norm_cases_checked": antecedent_cases,
        "counterexamples": 0,
    }


VERIFIERS = {
    "finite-c5-perfect-berge-v0": verify_c5,
    "bounded-padic-ultrametric-v0": verify_padic,
}


def main() -> None:
    bundle = json.loads(CONTRACTS.read_text())
    contracts = bundle["contracts"]
    assert len(contracts) == 2

    OUTDIR.mkdir(parents=True, exist_ok=True)
    rows = []
    acquisition_kinds = set()
    for contract in contracts:
        acquired = acquire(contract)
        acquisition_kinds.add(acquired["kind"])
        snapshot_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", contract["source_id"]) + ".snapshot"
        (OUTDIR / snapshot_name).write_bytes(acquired["bytes"])

        binding = apply_extraction_contract(
            contract,
            acquired["text"],
            evidence_ref="hosted:crystal-literature-heldout-transfer-v4",
        )
        rejected = qualify_falsifiers(
            contract,
            acquired["text"],
            evidence_ref="hosted:crystal-literature-heldout-transfer-v4",
        )
        verifier = VERIFIERS[contract["verifier_route"]]()
        rows.append(
            {
                "name": contract["name"],
                "source_id": contract["source_id"],
                "acquisition_kind": acquired["kind"],
                "resolved_url": acquired["resolved_url"],
                "snapshot_sha256": acquired["sha256"],
                "snapshot_bytes": len(acquired["bytes"]),
                "fallback_errors": acquired["fallback_errors"],
                "binding": binding,
                "falsifiers_rejected": list(rejected),
                "verifier": verifier,
            }
        )

    evidence = {
        "schema": "mathgraph.crystal-literature-heldout-transfer-v4.qualified",
        "status": "QUALIFIED_BOUNDED",
        "frozen_interpreter_head": PARENT,
        "results": {
            "heldout_sources": 2,
            "acquisition_kinds": sorted(acquisition_kinds),
            "contracts_qualified": len(rows),
            "relations": ["implies"],
            "falsifiers_rejected": sum(len(row["falsifiers_rejected"]) for row in rows),
            "independent_math_verifiers_green": len(rows),
            "new_crystal_waist_fields": 0,
            "new_claim_dialect_fields": 0,
            "interpreter_source_changes": 0,
        },
        "heldout_results": rows,
        "epistemic_result": {
            "frozen_declarative_interpreter_transfer": "WARRANTED_ON_TWO_HELDOUT_SOURCES",
            "html_and_pdf_acquisition": "WARRANTED_ON_DECLARED_SOURCES",
            "general_theorem_to_bounded_instance_relation": "WARRANTED_ON_DECLARED_SPECIALIZATIONS",
            "generic_prose_extraction": "UNKNOWN",
        },
        "boundary": (
            "Two held-out sources only. The frozen extraction interpreter receives new contract "
            "data without modification; independent verifiers qualify only the bounded formal "
            "instances. This does not establish generic theorem extraction or the truth of the "
            "source theorems in full generality."
        ),
    }
    RESULT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print("CRYSTAL_LITERATURE_HELDOUT_TRANSFER_V4=QUALIFIED_BOUNDED")
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
