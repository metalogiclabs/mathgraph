#!/usr/bin/env python3
"""Exact arithmetic/Galois contract control for the RH claim's CorG/CountI.

Pinned sources:
  HeightAndVanishing/Counts.lean (GD, CorG, CountI)
  HeightAndVanishing/DirichletPrimeToLPartMulLPowerPart.lean (Host, X, CaseI)
  AutomorphicVarieties/StmtFields.lean (Bchi, pK, hStar, pOne)

Concrete test:
  base χ = PChar.one, h.ex=2, q1=59, d=71, Host.N=16*59*71
  e=1, t=2, ell=5, ψ quadratic Dirichlet character (Legendre mod 59)
  K=Q(sqrt(-7)), p=41, p'=43, Ls={5}, H=ker(ψ).
All GD arithmetic conditions including the *eta* noncontainment have a
concrete finite cyclotomic-Galois witness: exponent a=591 mod 5*59*7,
which fixes ζ5 and the quadratic field cut out by ψ59 but moves K.

This is an exact arithmetic + field-identification stress control.
It does NOT compute Chr.V', a Selmer group, or prove/refute CorG or CountI
as a Lean theorem. Complex and 5-adic character interpretation differs
by the choice of coefficient field; ±1 is available in either.
"""
from math import gcd, isqrt

def isprime(n):
    return n>1 and all(n%j for j in range(2,isqrt(n)+1))

def crt(residues, moduli):
    total=1
    for m in moduli: total *= m
    return sum(a*(total//m)*pow(total//m,-1,m)
               for a,m in zip(residues,moduli))%total

def quad_symbol(a,p):
    assert isprime(p)
    v=a%p
    if v==0:return 0
    x=pow(v,(p-1)//2,p)
    assert x in (1,p-1)
    return 1 if x==1 else -1

def class_number_minus7():
    # Standard reduced positive definite primitive binary quadratic
    # forms of fundamental discriminant -7, including boundary choices.
    D=-7
    forms=[]
    for a in range(1,isqrt((-D)//3)+2):
        for b in range(-a,a+1):
            if (b*b-D)%(4*a):continue
            c=(b*b-D)//(4*a)
            if a>c or gcd(a,gcd(abs(b),c)) != 1:continue
            if (abs(b)==a or a==c) and b<0:continue
            forms.append((a,b,c))
    assert forms==[(1,1,2)],forms
    return len(forms)

def main():
    q1,d=59,71
    ell,e,t,exp=5,1,2,2
    chi_conductor,ordC,pK,pOne=1,1,7,3
    hstar=class_number_minus7()
    Bchi={3,7}  # prime factors of 1*1*7*1*3 plus 3
    assert hstar == 1
    assert pK==7 and pOne==3
    assert isprime(q1) and q1%8==3
    assert isprime(d) and d%16==7
    assert gcd(q1*d,chi_conductor)==1  # Host.pair
    assert 2<=exp
    assert 2*t+1<min(q1,d)  # Host.Big t
    assert all(y<min(q1,d) for y in (chi_conductor,ordC,pK,hstar,pOne))
    N=(1<<(exp+2))*q1*d # Host.N
    assert N==67024 and N%2==0
    # ψ has order 2, is odd, and is trivial on the genuine Host.H.
    assert quad_symbol(-1,q1)==-1  # PsiEven e=1
    assert quad_symbol(3,q1) in (-1,1)
    assert ell not in Bchi and (2*e)%(ell-1)!=0 # CaseI
    assert ell!=2 and e>=1 and ell>1  # GD.l_odd / e_pos
    assert 2%ell!=0               # GD.ord: ell does not divide order ψ
    assert gcd(ell,N)==1         # comp ell ψ =1; GD.ine
    squares_q1=sorted({x*x%q1 for x in range(1,q1)})
    squares_d=sorted({x*x%d for x in range(1,d)})
    H=[crt((a2,aq,ad),(16,q1,d)) for a2 in (1,15)
       for aq in squares_q1 for ad in squares_d]
    assert len(H)==len(set(H))==2030
    assert all(quad_symbol(a,q1)==1 for a in H) # Host.IsChar ψ
    # K=Q(sqrt(-7)): discriminant -7, class number 1, imaginary degree 2.
    abs_disc=7
    assert ell!=7 and (abs_disc*hstar)%ell!=0
    assert gcd(abs_disc,N)==1
    # Required GD.eta: a Galois element in ker(cycMod ell 1) and
    # ker(chiP ell ψ)=ker ψ, but NOT in Gal(Qbar/K).
    g=crt((1,1,3),(ell,q1,7))
    assert g==591 and gcd(g,ell*q1*7)==1
    assert g%ell==1 and quad_symbol(g,q1)==1
    assert quad_symbol(g,7)==-1
    # Fixed CorG auxiliary primes: exclusion from 30*N*disc.
    p,pp=41,43
    assert isprime(p) and isprime(pp) and p!=pp
    assert (30*N*abs_disc)%p!=0 and (30*N*abs_disc)%pp!=0
    assert p<q1 and pp<q1 and p<d and pp<d
    # The test has nonempty GD eligibility; no claim about Vlen.
    print(f"Host: chi=1 ex={exp} q1={q1} d={d} N={N} Big(t={t})=YES")
    print(f"l={ell} e={e} ψ=Legendre({q1}) order=2 odd=YES CaseI=YES H_size={len(H)}")
    print(f"K=Q(sqrt(-7)) discriminant=-7 class_number={hstar} GD_coprime=YES")
    print(f"GD_eta_exponent={g} mod5={g%5} mod59={g%59} mod7={g%7}")
    print(f"CorG_auxiliary_primes={p},{pp} excluded_support=YES")
    print("PASS: real CorG/GD and Host/CaseI arithmetic antecedent witness")
    print("BOUNDARY: NOT an exact Selmer length, CorG bound, or formal Lean witness")

if __name__=="__main__":
    main()
