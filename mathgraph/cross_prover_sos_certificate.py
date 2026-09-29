"""Exact bounded SOS certificate compiler for cross-prover polynomial claims.

V1 is intentionally tiny: two real variables, integer coefficients, degree ≤ 2,
and a single perfect-square linear certificate. It exists to test whether a
verified source proposition can be compiled into a consumer-checkable semantic
certificate rather than re-running open-ended proof search.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import isqrt
from typing import Any, Mapping, Sequence

from mathgraph.crystal import SemanticObject, canonical_bytes

Monomial = tuple[int, int]
Polynomial = dict[Monomial, Fraction]


def _add(a: Polynomial, b: Polynomial) -> Polynomial:
    out=dict(a)
    for m,c in b.items():
        out[m]=out.get(m,Fraction(0))+c
        if out[m]==0:
            del out[m]
    return out


def _scale(k: Fraction, p: Polynomial) -> Polynomial:
    return {m:k*c for m,c in p.items() if k*c != 0}


def _mul(a: Polynomial, b: Polynomial) -> Polynomial:
    out: Polynomial={}
    for (ax,ay),ac in a.items():
        for (bx,by),bc in b.items():
            m=(ax+bx,ay+by)
            out[m]=out.get(m,Fraction(0))+ac*bc
    return {m:c for m,c in out.items() if c}


def _pow(p: Polynomial, n: int) -> Polynomial:
    if n < 0:
        raise ValueError("negative exponent")
    out={(0,0):Fraction(1)}
    for _ in range(n):
        out=_mul(out,p)
    return out


def polynomial_from_ast(ast: Mapping[str, Any]) -> Polynomial:
    if "var" in ast:
        if ast["var"]=="x":
            return {(1,0):Fraction(1)}
        if ast["var"]=="y":
            return {(0,1):Fraction(1)}
        raise ValueError("unsupported variable")
    if "const" in ast:
        return {(0,0):Fraction(int(ast["const"]))}
    op=ast.get("op")
    if op=="add":
        out: Polynomial={}
        for arg in ast["args"]:
            out=_add(out,polynomial_from_ast(arg))
        return out
    if op=="mul":
        out={(0,0):Fraction(1)}
        for arg in ast["args"]:
            out=_mul(out,polynomial_from_ast(arg))
        return out
    if op=="pow":
        return _pow(polynomial_from_ast(ast["base"]),int(ast["exp"]))
    raise ValueError(f"unsupported polynomial AST op {op!r}")


def claim_difference(claim: Mapping[str, Any]) -> Polynomial:
    prop=claim["proposition"]
    if prop.get("op")!="ge":
        raise ValueError("V1 accepts only polynomial >= polynomial")
    return _add(
        polynomial_from_ast(prop["left"]),
        _scale(Fraction(-1),polynomial_from_ast(prop["right"])),
    )


def _sqrt_fraction(q: Fraction) -> Fraction | None:
    if q < 0:
        return None
    n=isqrt(q.numerator)
    d=isqrt(q.denominator)
    if n*n != q.numerator or d*d != q.denominator:
        return None
    return Fraction(n,d)


@dataclass(frozen=True)
class LinearSquareCertificate:
    x: Fraction
    y: Fraction
    constant: Fraction = Fraction(0)
    weight: Fraction = Fraction(1)

    def polynomial(self) -> Polynomial:
        linear: Polynomial={}
        if self.x:
            linear[(1,0)]=self.x
        if self.y:
            linear[(0,1)]=self.y
        if self.constant:
            linear[(0,0)]=self.constant
        return _scale(self.weight,_mul(linear,linear))

    def to_dict(self) -> dict[str, Any]:
        def f(q: Fraction) -> str:
            return str(q.numerator) if q.denominator==1 else f"{q.numerator}/{q.denominator}"
        return {
            "type":"weighted_linear_square",
            "x":f(self.x),
            "y":f(self.y),
            "constant":f(self.constant),
            "weight":f(self.weight),
        }


def discover_linear_square_certificate(
    claim: Mapping[str, Any],
) -> LinearSquareCertificate | None:
    p=claim_difference(claim)
    # V1: homogeneous binary quadratic q = a x² + b xy + c y².
    if any(m not in {(2,0),(1,1),(0,2)} for m in p):
        return None
    a=p.get((2,0),Fraction(0))
    b=p.get((1,1),Fraction(0))
    c=p.get((0,2),Fraction(0))
    sx=_sqrt_fraction(a)
    sy_abs=_sqrt_fraction(c)
    if sx is None or sy_abs is None:
        return None
    for sy in (sy_abs,-sy_abs):
        cert=LinearSquareCertificate(sx,sy)
        if cert.polynomial()==p:
            return cert
    return None


def verify_certificate(
    claim: Mapping[str, Any], cert: LinearSquareCertificate
) -> bool:
    return cert.weight >= 0 and cert.polynomial()==claim_difference(claim)


@dataclass(frozen=True)
class SumOfSquaresCertificate:
    """Exact rational SOS for a homogeneous binary quadratic."""

    components: tuple[LinearSquareCertificate, ...]

    def polynomial(self) -> Polynomial:
        out: Polynomial={}
        for component in self.components:
            out=_add(out,component.polynomial())
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "type":"sum_of_weighted_linear_squares",
            "components":[x.to_dict() for x in self.components],
        }


def discover_binary_quadratic_sos(
    claim: Mapping[str, Any],
) -> SumOfSquaresCertificate | None:
    """Discover an exact rational Cholesky/SOS certificate when one exists.

    For q = a*x^2 + b*x*y + c*y^2 with rational coefficients:
      q = a*(x + b/(2a)*y)^2 + (c-b^2/(4a))*y^2   when a > 0.
    The degenerate a=0 case is accepted only when b=0 and c>=0.
    """

    p=claim_difference(claim)
    if any(m not in {(2,0),(1,1),(0,2)} for m in p):
        return None
    a=p.get((2,0),Fraction(0))
    b=p.get((1,1),Fraction(0))
    cq=p.get((0,2),Fraction(0))

    components: list[LinearSquareCertificate]=[]
    if a < 0:
        return None
    if a == 0:
        if b != 0 or cq < 0:
            return None
        if cq > 0:
            components.append(
                LinearSquareCertificate(
                    x=Fraction(0), y=Fraction(1), weight=cq
                )
            )
    else:
        slope=b/(2*a)
        residual=cq-(b*b)/(4*a)
        if residual < 0:
            return None
        components.append(
            LinearSquareCertificate(
                x=Fraction(1), y=slope, weight=a
            )
        )
        if residual > 0:
            components.append(
                LinearSquareCertificate(
                    x=Fraction(0), y=Fraction(1), weight=residual
                )
            )

    cert=SumOfSquaresCertificate(tuple(components))
    if not verify_sos_certificate(claim,cert):
        return None
    return cert


def verify_sos_certificate(
    claim: Mapping[str, Any], cert: SumOfSquaresCertificate
) -> bool:
    return (
        all(component.weight >= 0 for component in cert.components)
        and cert.polynomial()==claim_difference(claim)
    )


def _lean_rat(q: Fraction) -> str:
    if q.denominator==1:
        return str(q.numerator)
    return f"({q.numerator} / {q.denominator} : ℝ)"


def _lean_linear(component: LinearSquareCertificate) -> str:
    terms: list[str]=[]
    if component.x:
        if component.x==1:
            terms.append("x")
        elif component.x==-1:
            terms.append("-x")
        else:
            terms.append(f"{_lean_rat(component.x)} * x")
    if component.y:
        if component.y==1:
            term="y"
        elif component.y==-1:
            term="-y"
        else:
            term=f"{_lean_rat(component.y)} * y"
        terms.append(term)
    if component.constant:
        terms.append(_lean_rat(component.constant))
    if not terms:
        return "0"
    expr=terms[0]
    for term in terms[1:]:
        if term.startswith("-"):
            expr += " - " + term[1:]
        else:
            expr += " + " + term
    return f"({expr})"


def render_lean_sos_proof(cert: SumOfSquaresCertificate) -> str:
    if any(component.constant for component in cert.components):
        raise ValueError("V2 renderer supports homogeneous certificates only")
    lines=["by"]
    facts=[]
    for i,component in enumerate(cert.components):
        linear=_lean_linear(component)
        if component.weight==1:
            lines.append(
                f"  have hs{i} : 0 ≤ {linear} ^ 2 := sq_nonneg {linear}"
            )
        else:
            weight=_lean_rat(component.weight)
            lines.append(f"  have hw{i} : 0 ≤ ({weight}) := by norm_num")
            lines.append(
                f"  have hs{i} : 0 ≤ ({weight}) * {linear} ^ 2 := "
                f"mul_nonneg hw{i} (sq_nonneg {linear})"
            )
        facts.append(f"hs{i}")
    if facts:
        lines.append(f"  nlinarith only [{', '.join(facts)}]")
    else:
        lines.append("  norm_num")
    return "\n".join(lines)+"\n"


def render_lean_certificate_proof(cert: LinearSquareCertificate) -> str:
    if cert != LinearSquareCertificate(Fraction(1),Fraction(-1)):
        raise ValueError("V1 Lean renderer supports only the discovered AM-GM certificate")
    return """by
  have hs : 0 ≤ (x - y) ^ 2 := sq_nonneg (x - y)
  nlinarith only [hs]
"""


def compile_certificate_capability(
    claim: Mapping[str, Any],
    cert: LinearSquareCertificate,
    source_authority: Mapping[str, Any],
) -> SemanticObject:
    if source_authority.get("status") != "WARRANTED_BOUNDED_CROSS_PROVER_SEMANTIC_LINK":
        raise ValueError("consumer certificate requires warranted cross-prover source authority")
    if not verify_certificate(claim, cert):
        raise ValueError("invalid SOS certificate")
    payload=canonical_bytes({
        "canonical_claim":claim,
        "certificate":cert.to_dict(),
        "source_semantic_object":source_authority["compiled"]["semantic_object_id"],
        "source_authority_run":source_authority["authority"]["run_id"],
        "pvs_provenance":source_authority["pvs"],
        "lean_consumer_boundary":{
            "certificate_check":"square_nonnegative + normalized arithmetic only",
            "proof_object_transport":False,
        },
    })
    return SemanticObject(
        "cross-prover.consumer-certificate@1",
        1,
        payload,
        (
            "logic.closed-proposition.truth@1",
            "real.polynomial.amgm2@1",
            "certificate.sum-of-squares@1",
        ),
    )
