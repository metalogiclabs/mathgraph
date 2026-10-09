#!/usr/bin/env python3
"""WattBot 2026: deterministic retrieval and bounded evidence validation.

This does NOT generate answers. It checks that proposed evidence is present in
pinned local source PDFs, and (optionally) checks arithmetic on cited literals.
It does NOT prove that a source quotation semantically entails an answer.
"""
from __future__ import annotations

import argparse
import ast
import csv
from collections import Counter
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

COLUMNS = (
    "id", "question", "answer", "answer_value", "answer_unit", "ref_id",
    "ref_url", "supporting_materials", "explanation",
)
TOKEN_RE = re.compile(r"[a-z]+|\d+(?:\.\d+)?", re.IGNORECASE)
NUM_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w.])")


def read_csv(path: str | Path) -> list[dict[str, str]]:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            with open(path, encoding=encoding, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Cannot decode CSV: {path}")


def jsonl(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: str | Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def norm(s: str) -> str:
    return " ".join(s.split()).casefold()


def tokens(s: str) -> list[str]:
    return TOKEN_RE.findall(s.casefold())


def chunks_from_pages(doc_id: str, url: str, pdf_path: Path, size: int = 2400,
                      overlap: int = 320) -> list[dict]:
    if size <= overlap or overlap < 0:
        raise ValueError("chunk size must exceed nonnegative overlap")
    try:
        import fitz  # type: ignore
    except ImportError as exc:
        raise RuntimeError("PDF ingestion requires pip install pymupdf") from exc
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    rows = []
    with fitz.open(str(pdf_path)) as pdf:
        for page_no, page in enumerate(pdf, 1):
            # Page-local chunks: evidence can never silently cross page bounds.
            body = " ".join(page.get_text(sort=True).split())
            if not body:
                continue
            start = 0
            while start < len(body):
                end = min(len(body), start + size)
                if end < len(body):
                    boundary = body.rfind(" ", start + size // 2, end)
                    if boundary > start:
                        end = boundary
                snippet = body[start:end].strip()
                if snippet:
                    rows.append({"ref_id": doc_id, "url": url, "page": page_no,
                                 "text": snippet, "pdf_sha256": digest})
                if end == len(body):
                    break
                start = max(start + 1, end - overlap)
    return rows


def metadata_index(path: str | Path) -> dict[str, dict[str, str]]:
    out = {}
    for row in read_csv(path):
        doc_id = row.get("id", "").strip()
        url = row.get("url", "").strip()
        if not doc_id or not url or doc_id in out:
            raise ValueError(f"Missing/duplicate ID or URL in metadata: {doc_id!r}")
        out[doc_id] = row
    return out


def ingest(metadata: str, pdf_dir: str, out: str) -> None:
    docs = metadata_index(metadata)
    chunks = []
    missing = []
    for doc_id, row in sorted(docs.items()):
        path = Path(pdf_dir) / f"{doc_id}.pdf"
        if not path.is_file():
            missing.append(doc_id)
            continue
        chunks.extend(chunks_from_pages(doc_id, row["url"], path))
    if missing:
        # No partial corpus: otherwise low recall can masquerade as abstention.
        raise ValueError(f"Missing {len(missing)} pinned PDFs in {pdf_dir}: {missing[:12]}")
    write_jsonl(out, chunks)
    print(f"Indexed {len(docs)} documents / {len(chunks)} chunks -> {out}")


def ranked(question: str, chunks: list[dict], top_k: int = 8) -> list[dict]:
    """Deterministic BM25 baseline, lexical only; no trained or hidden labels."""
    if top_k < 1:
        raise ValueError("top_k must be positive")
    q = set(tokens(question))
    if not q or not chunks:
        return []
    bodies = [tokens(c["text"]) for c in chunks]
    avg_len = max(1, sum(map(len, bodies)) / len(bodies))
    df = Counter(t for body in bodies for t in set(body))
    N = len(bodies)
    scored = []
    for i, body in enumerate(bodies):
        tf = Counter(body)
        length_norm = 0.25 + 0.75 * len(body) / avg_len
        score = sum(math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5)) *
                    tf[t] * 2.2 / (tf[t] + 1.2 * length_norm)
                    for t in q if tf[t])
        if score > 0:
            scored.append((score, i))
    scored.sort(key=lambda si: (-si[0], chunks[si[1]]["ref_id"],
                                 chunks[si[1]]["page"], si[1]))
    return [dict(chunks[i], score=round(s, 8)) for s, i in scored[:top_k]]


def retrieve(question_csv: str, chunks_path: str, out: str, top_k: int = 8) -> None:
    chunks = jsonl(chunks_path)
    questions = read_csv(question_csv)
    rows = [{"id": q["id"], "question": q["question"],
             "hits": ranked(q["question"], chunks, top_k)} for q in questions]
    write_jsonl(out, rows)
    print(f"Retrieved top {top_k} chunks for {len(rows)} questions -> {out}")


def as_fraction(value: str) -> Fraction:
    try:
        d = Decimal(str(value).replace(",", ""))
        if not d.is_finite():
            raise ValueError("nonfinite number")
        return Fraction(d)
    except (InvalidOperation, ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"Invalid numeric value: {value!r}") from exc


def calculate(expression: str, variables: dict[str, Fraction]) -> Fraction:
    """Exact rational evaluation of a restricted arithmetic grammar. No eval()."""
    def visit(node: ast.AST) -> Fraction:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Name) and node.id in variables:
            return variables[node.id]
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return as_fraction(str(node.value))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -visit(node.operand)
        if isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add): return left + right
            if isinstance(node.op, ast.Sub): return left - right
            if isinstance(node.op, ast.Mult): return left * right
            if isinstance(node.op, ast.Div): return left / right
        raise ValueError("Unsupported arithmetic expression")
    return visit(ast.parse(expression, mode="eval"))


def verify_derivation(candidate: dict, evidence: list[dict]) -> None:
    derivation = candidate.get("derivation")
    if not derivation:
        return
    variables = {}
    for name, spec in derivation["inputs"].items():
        if not name.isidentifier() or name.startswith("_"):
            raise ValueError("Unsafe variable name")
        idx = spec["evidence_index"]
        if type(idx) is not int or idx < 0 or idx >= len(evidence):
            raise ValueError("Derivation refers to nonexistent evidence")
        value = as_fraction(str(spec["value"]))
        # Ground *each numeric input* in a literal in the anchored quotation.
        observed = {as_fraction(m.group()) for m in NUM_RE.finditer(evidence[idx]["quote"])}
        if value not in observed:
            raise ValueError(f"Derivation input {name} not visible in evidence")
        variables[name] = value
    actual = calculate(derivation["expression"], variables)
    claimed = as_fraction(str(candidate["answer_value"]))
    if abs(actual - claimed) > abs(actual) / 1000 if actual else claimed != 0:
        raise ValueError(f"Arithmetic mismatch: exact {actual}; claimed {claimed}")


def verify_candidate(candidate: dict, question: dict, docs: dict,
                     chunks: list[dict]) -> dict[str, str]:
    if candidate.get("id") != question["id"]:
        raise ValueError("Candidate ID does not match question")
    value = str(candidate.get("answer_value", "")).strip()
    if not value:
        raise ValueError("Candidate must explicitly state answer_value or is_blank")
    explanation = str(candidate.get("explanation", "")).strip()
    if not explanation:
        raise ValueError("Submission explanations cannot be empty")
    ref_ids = candidate.get("ref_ids", [])
    evidence = candidate.get("evidence", [])
    if not isinstance(ref_ids, list) or not isinstance(evidence, list):
        raise ValueError("ref_ids and evidence must be JSON arrays")
    if value.casefold() == "is_blank":
        if ref_ids or evidence or candidate.get("derivation"):
            raise ValueError("Unanswerable response must have no evidence or derivation")
        return dict(zip(COLUMNS, (question["id"], question["question"],
                    candidate.get("answer", "Unable to answer from corpus."),
                    "is_blank", question.get("answer_unit") or "is_blank",
                    "is_blank", "is_blank", "is_blank", explanation)))
    if not ref_ids or len(ref_ids) != len(set(ref_ids)):
        raise ValueError("Non-blank answer requires distinct source IDs")
    if not evidence or set(ref_ids) != {e["ref_id"] for e in evidence}:
        raise ValueError("Citation set must match evidence sources exactly")
    for ev in evidence:
        doc_id, page, quote = ev["ref_id"], ev["page"], ev["quote"]
        if doc_id not in docs or type(page) is not int or page < 1 or not quote.strip():
            raise ValueError("Invalid evidence source, page or quotation")
        if not any(c["ref_id"] == doc_id and c["page"] == page and
                   c["url"] == docs[doc_id]["url"] and
                   norm(quote) in norm(c["text"]) for c in chunks):
            raise ValueError(f"Quote not anchored to pinned source {doc_id} p.{page}")
    verify_derivation(candidate, evidence)
    # This validates provenance and optional arithmetic, NOT semantic entailment.
    return dict(zip(COLUMNS, (question["id"], question["question"],
                candidate.get("answer", value), value,
                question.get("answer_unit") or "is_blank",
                repr(ref_ids), repr([docs[i]["url"] for i in ref_ids]),
                repr([e["quote"] for e in evidence]), explanation)))


def assemble(question_csv: str, metadata: str, chunks_path: str,
             candidates_path: str, out: str) -> None:
    docs = metadata_index(metadata)
    chunks = jsonl(chunks_path)
    candidates = jsonl(candidates_path)
    by_id = {c["id"]: c for c in candidates}
    questions = read_csv(question_csv)
    question_ids = [q["id"] for q in questions]
    if len(by_id) != len(candidates) or len(set(question_ids)) != len(questions) or set(by_id) != set(question_ids):
        raise ValueError("Require exactly one candidate for each question, with no extras")
    # Validate all before writing: never release a partial submission.
    predictions = [verify_candidate(by_id[q["id"]], q, docs, chunks) for q in questions]
    with open(out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(predictions)
    print(f"Validated {len(predictions)} rows -> {out} (not a leaderboard score)")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest="command", required=True)
    s = subs.add_parser("ingest", help="Parse locally cached, pinned PDFs; no bulk fetch")
    s.add_argument("--metadata", required=True)
    s.add_argument("--pdf-dir", required=True)
    s.add_argument("--out", required=True)
    s = subs.add_parser("retrieve", help="Write deterministic lexical evidence candidates")
    s.add_argument("--questions", required=True)
    s.add_argument("--chunks", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--top-k", type=int, default=8)
    s = subs.add_parser("assemble", help="Validate evidence-backed answer drafts")
    for arg in ("questions", "metadata", "chunks", "candidates", "out"):
        s.add_argument(f"--{arg}", required=True)
    s = subs.add_parser("score", help="Use the official Score.py, never a score imitation")
    s.add_argument("--official-scorer", required=True)
    s.add_argument("--train-ground-truth", required=True)
    s.add_argument("--train-predictions", required=True)
    a = p.parse_args(argv)
    if a.command == "ingest": ingest(a.metadata, a.pdf_dir, a.out)
    elif a.command == "retrieve": retrieve(a.questions, a.chunks, a.out, a.top_k)
    elif a.command == "assemble":
        assemble(a.questions, a.metadata, a.chunks, a.candidates, a.out)
    else:
        subprocess.run([sys.executable, a.official_scorer,
                        a.train_ground_truth, a.train_predictions], check=True)


if __name__ == "__main__":
    main()