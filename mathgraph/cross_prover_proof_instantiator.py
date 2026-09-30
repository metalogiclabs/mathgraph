"""Bounded automatic Lean consumer instantiation above the structural selector.

This layer is deliberately small. It does not invent new constructor classes.
It translates a closed real-arithmetic PVS surface into a Lean proposition and
instantiates one of two already-warranted proof templates:

- explicit_witness: search a bounded integer witness, then let Lean check it;
- quantifier_witness_duality: refute a negated existential polynomial claim
  by unpacking its witness and invoking nlinarith with square nonnegativity.

Every generated consumer remains CANDIDATE until Lean kernel-checks it.
Unsupported schema/template combinations fail closed.
"""

from __future__ import annotations

import ast
import re
from typing import Any

from mathgraph.cross_prover_family_discovery import normalize_surface
from mathgraph.cross_prover_constructor_selector import select_constructor_schema


def pvs_surface_to_lean(surface: str) -> str:
    s=normalize_surface(surface)
    s=re.sub(r"FORALL \(([A-Za-z_]\w*): real\):",r"∀ \1 : ℝ,",s)
    s=re.sub(r"EXISTS \(([A-Za-z_]\w*): real\):",r"∃ \1 : ℝ,",s)
    s=s.replace(" IMPLIES "," → ")
    s=s.replace(" IFF "," ↔ ")
    s=s.replace(" AND "," ∧ ")
    s=s.replace(" OR "," ∨ ")
    s=re.sub(r"\bNOT\b","¬",s)
    s=s.replace("/=","≠")
    s=s.replace(">=","≥")
    s=s.replace("<=","≤")
    return s


_ALLOWED_AST=(
    ast.Expression,ast.BoolOp,ast.BinOp,ast.UnaryOp,ast.Compare,
    ast.Name,ast.Constant,
    ast.And,ast.Or,ast.Not,
    ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow,
    ast.USub,ast.UAdd,
    ast.Eq,ast.NotEq,ast.Gt,ast.GtE,ast.Lt,ast.LtE,
    ast.Load,
)


def _safe_eval_real_formula(body: str, var: str, value: int) -> bool | None:
    if re.search(r"\b(FORALL|EXISTS|IMPLIES|IFF)\b",body):
        return None
    expr=body.replace("^","**")
    expr=expr.replace(" AND "," and ").replace(" OR "," or ").replace(" NOT "," not ")
    expr=expr.replace("/=","!=")
    expr=re.sub(r"(?<![<>=!])=(?!=)", "==", expr)
    try:
        tree=ast.parse(expr,mode="eval")
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node,_ALLOWED_AST):
            return None
        if isinstance(node,ast.Name) and node.id!=var:
            return None
    try:
        return bool(eval(compile(tree,"<bounded-formula>","eval"),{"__builtins__":{}},{var:value}))
    except Exception:
        return None


def _top_exists(surface: str) -> tuple[str,str] | None:
    s=normalize_surface(surface)
    m=re.match(r"^EXISTS \(([A-Za-z_]\w*): real\):\s*(.*)$",s)
    if not m:
        return None
    return m.group(1),m.group(2).strip()


def _negated_exists(surface: str) -> tuple[str,str] | None:
    s=normalize_surface(surface)
    inner=None
    if s.startswith("NOT (") and s.endswith(")"):
        inner=s[5:-1].strip()
    elif s.startswith("NOT "):
        inner=s[4:].strip()
    if inner is None:
        return None
    m=re.match(r"^EXISTS \(([A-Za-z_]\w*): real\):\s*(.*)$",inner)
    if not m:
        return None
    return m.group(1),m.group(2).strip()


def _theorem_name(formula_name: str) -> str:
    safe=re.sub(r"[^A-Za-z0-9_]","_",formula_name)
    if not safe or safe[0].isdigit():
        safe="f_"+safe
    return "auto_"+safe


def instantiate_consumer(formula_name: str, surface: str) -> dict[str,Any]:
    pick=select_constructor_schema(surface)
    if pick["status"]!="CANDIDATE_CONSTRUCTOR_SELECTION":
        return {
            "status":"UNKNOWN_NO_CONSTRUCTOR_SELECTION",
            "formula_name":formula_name,
            "selection":pick,
        }

    schema=str(pick["schema"])
    statement=pvs_surface_to_lean(surface)
    theorem_name=_theorem_name(formula_name)

    if schema=="explicit_witness":
        parsed=_top_exists(surface)
        if parsed is None:
            return {
                "status":"UNKNOWN_UNSUPPORTED_AUTOMATIC_TEMPLATE",
                "formula_name":formula_name,
                "schema":schema,
                "reason":"explicit_witness template currently requires a top-level existential",
            }
        var,body=parsed
        witness=None
        for k in range(-8,9):
            ok=_safe_eval_real_formula(body,var,k)
            if ok is True:
                witness=k
                break
        if witness is None:
            return {
                "status":"UNKNOWN_NO_SMALL_INTEGER_WITNESS",
                "formula_name":formula_name,
                "schema":schema,
                "search_interval":[-8,8],
            }
        proof=f"""by
  refine ⟨({witness} : ℝ), ?_⟩
  norm_num"""
        return {
            "status":"CANDIDATE_GENERATED_CONSUMER",
            "formula_name":formula_name,
            "schema":schema,
            "theorem_name":theorem_name,
            "lean_statement":statement,
            "lean_proof":proof,
            "synthesis":{"kind":"bounded_integer_witness","witness":witness,"interval":[-8,8]},
        }

    if schema=="quantifier_witness_duality":
        parsed=_negated_exists(surface)
        if parsed is None:
            return {
                "status":"UNKNOWN_UNSUPPORTED_AUTOMATIC_TEMPLATE",
                "formula_name":formula_name,
                "schema":schema,
                "reason":"duality template currently requires top-level NOT EXISTS",
            }
        var,body=parsed
        and_count=len(re.findall(r"\bAND\b",body))
        if and_count==0:
            pattern=f"⟨{var}, h0⟩"
        elif and_count==1:
            pattern=f"⟨{var}, h0, h1⟩"
        else:
            return {
                "status":"UNKNOWN_UNSUPPORTED_AUTOMATIC_TEMPLATE",
                "formula_name":formula_name,
                "schema":schema,
                "reason":"duality template currently supports at most one top-level conjunction",
            }
        proof=f"""by
  rintro {pattern}
  nlinarith [sq_nonneg {var}]"""
        return {
            "status":"CANDIDATE_GENERATED_CONSUMER",
            "formula_name":formula_name,
            "schema":schema,
            "theorem_name":theorem_name,
            "lean_statement":statement,
            "lean_proof":proof,
            "synthesis":{"kind":"negated_existential_square_contradiction"},
        }

    return {
        "status":"UNKNOWN_UNSUPPORTED_AUTOMATIC_TEMPLATE",
        "formula_name":formula_name,
        "schema":schema,
        "reason":"selected constructor class has no automatic proof template in V1",
    }


def render_generated_consumers(rows: list[dict[str,Any]]) -> str:
    chunks=["import Mathlib","","namespace CrystalCrossProverProofInstantiator",""]
    for row in rows:
        if row.get("status")!="CANDIDATE_GENERATED_CONSUMER":
            continue
        chunks.extend([
            f"theorem {row['theorem_name']} : {row['lean_statement']} := {row['lean_proof']}",
            "",
        ])
    chunks.append("end CrystalCrossProverProofInstantiator")
    return "\n".join(chunks)+"\n"
