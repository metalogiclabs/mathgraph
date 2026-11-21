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

def class_number_reduced(D):
    # Standard reduced primitive positive definite binary quadratic
    # forms, for fundamental discriminants -7 and -11.
    forms=[]
    for a in range(1,isqrt((-D)//3)+2):
        for b in range(-a,a+1):
            if (b*b-D)%(4*a):continue
            c=(b*b-D)//(4*a)
            if a>c or gcd(a,gcd(abs(b),c)) != 1:continue
            if (abs(b)==a or a==c) and b<0:continue
            forms.append((a,b,c))
    assert forms=={-7:[(1,1,2)], -11:[(1,1,3)]}[D],forms
    return len(forms)


def live_case_coverage():
    """Source-defined counting CASE labels (except case V/Vs: companion script).

    Constructs actual Host.H subgroups for χ=1 and χ=primitive cubic mod7.
    Each case also needs a suitable coefficient DVR: ±1 already lies in Z_l;
    ζ3 is obtained in a finite extension of Z_5 or Z_7.
    Source-level arithmetic and finite-character test only, NOT Vlen.
    """
    q,d,exp=59,71,2
    n1=(1<<(exp+2))*q*d
    n3=(1<<(exp+2))*7*q*d
    # χ cubic mod7: primitive order-3 char, χ(3)=ζ3; χ(-1)=1.
    pow3={pow(3,j,7):j%3 for j in range(6)}
    assert len(pow3)==6
    def cubic7(x):
        return pow3[x%7]
    assert cubic7(3)==1 and cubic7(-1)==0
    assert class_number_reduced(-11)==1
    # For χ modulo7: ordC=3; pK=11; hStar=1; pOne=13.
    assert all(v<min(q,d) for v in (7,3,11,1,13))
    Bchi_one={3,7}
    Bchi_cubic={3,7,11,13}
    assert isprime(11) and 11%4==3 and 11>=7 and gcd(11,7)==1
    assert isprime(13) and 13%3==1 and gcd(13,2*7*11)==1
    assert n3==469168 and gcd(q*d,7)==1
    assert 2*3+1 < min(q,d) # Big(t=3), for BOTH hosts
    squares_q=sorted({x*x%q for x in range(1,q)})
    squares_d=sorted({x*x%d for x in range(1,d)})
    # χ=1 host: H imposes ±1 mod16; squares at both auxiliaries.
    h1=[crt((a2,aq,ad),(16,q,d)) for a2 in (1,15)
        for aq in squares_q for ad in squares_d]
    assert len(h1)==len(set(h1))==2030
    def legq(x):return quad_symbol(x,q)
    def legd(x):return quad_symbol(x,d)
    assert all(legq(a)==1 and legd(a)==1 for a in h1)
    # χ=cubic7 host also imposes χ7(a)=1.
    ker_cubic=[a for a in range(1,7) if cubic7(a)==0]
    assert ker_cubic==[1,6]
    h3=[crt((a2,a7,aq,ad),(16,7,q,d)) for a2 in (1,15)
        for a7 in ker_cubic for aq in squares_q for ad in squares_d]
    assert len(h3)==len(set(h3))==4060
    assert all(cubic7(a)==0 and legq(a)==1 and legd(a)==1 for a in h3)
    # Index 1: CountI l=5 e=1, ψ=Legendre59, odd.
    assert 5 not in Bchi_one and (2*1)%(5-1)!=0
    assert legq(-1)==-1 and 1<2
    # Index 2: CountII l=3 e=2, ψ=Legendre59 * Legendre71.
    # Order(ψ)=2; comp3ψ=1 (3 does not divide the conductor n1).
    assert 3 in Bchi_one and gcd(3,n1)==1
    assert legq(-1)*legd(-1)==1 and 2<3
    # Index 3: CountIII l=5 e=2, ψ=χ7, order3, even.
    assert 5 not in Bchi_cubic and (2*2)%(5-1)==0
    assert cubic7(-1)==0 and gcd(5,n3)==1 and 2<3
    # Index 4: CountIV l=7 e=2, ψ=χ7, comp7ψ=ψ,
    # hence chiP7ψ=ψ/(comp7ψ)=1, whose order (1) is odd.
    assert 7 in Bchi_cubic and n3%7==0
    assert cubic7(-1)==0 and 2<3
    # Index 5: CountZ l=5 e=2, ψ=1.
    assert 5 not in Bchi_one and (2*2)%(5-1)==0
    # CaseV/CountVs require large 2-power conductor and are separately
    # witnessed k=12..18 in countv_actual_host_character_contract.py.
    print(f"Counting leaves: trivial Host N={n1}, H_size={len(h1)}")
    print(f"Counting leaves: cubic7 Host N={n3}, H_size={len(h3)}")
    print("CountI live: l=5 e=1 ψ=Legendre59, odd")
    print("CountII live: l=3 e=2 ψ=Legendre59*Legendre71, even order2")
    print("CountIII live: l=5 e=2 ψ=cubic7, even order3")
    print("CountIV live: l=7 e=2 ψ=cubic7, chiP7 order1")
    print("CountZ live: l=5 e=2 ψ=1")
    print("PASS: five additional counting cases inhabited by exact Host characters")

def quartic_hits_actual_counti():
    # Two q with PARI/GP-certified Cl(F_q^+) ≅ C5.
    # This verifies all the lightweight CountI/CorG Host/GD arithmetic
    # constraints for q, d=167 and e=1,3; does NOT compute ShaU.
    d,ell,t=167,5,4
    assert isprime(d) and d%16==7 and d%5==2
    for q in (347,443):
        assert isprime(q) and q%8==3 and q%5 in (2,3)
        N=16*q*d
        assert gcd(q*d,1)==1 and gcd(7,N)==1
        assert 2*t+1<min(q,d)
        assert max(1,1,7,1,3)<min(q,d)
        squares_q=sorted({a*a%q for a in range(1,q)})
        squares_d=sorted({a*a%d for a in range(1,d)})
        H=[crt((a2,aq,ad),(16,q,d)) for a2 in (1,15)
           for aq in squares_q for ad in squares_d]
        assert len(H)==len(set(H))==(q-1)*((d-1)//2)
        assert all(quad_symbol(a,q)==1 for a in H)
        assert quad_symbol(-1,q)==-1
        assert quad_symbol(2,q)==-1
        assert quad_symbol(d,q)==1
        # 2 and d have faithful C4 Frobenius in the real quartic field
        # because their mod5 component has order 4 and their
        # quadratic ψq component is ±1.
        assert 2%5==2 and d%5==2
        a=crt((1,1,3),(ell,q,7))
        assert a%ell==1 and a%q==1 and a%7==3
        assert quad_symbol(a,q)==1 and quad_symbol(a,7)==-1
        assert gcd(7*q,ell)==1
        assert all(isprime(p) and (30*N*7)%p for p in (41,43))
        for e in (1,3):
            assert e<t and e>0 and e%2==1
            assert (2*e)%(ell-1)!=0 and ell not in (3,7)
        print(f"Fplus_5class_candidate q={q} d={d} N={N} "
              f"Host_H={len(H)} eta={a} CountI_e=1,3")
    print("PASS: both certified five-class primes satisfy CountI and GD arithmetic gates")


def main():
    q1,d=59,71
    ell,e,t,exp=5,1,2,2
    chi_conductor,ordC,pK,pOne=1,1,7,3
    hstar=class_number_reduced(-7)
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
    live_case_coverage()
    quartic_hits_actual_counti()
    print("BOUNDARY: NOT an exact Selmer length, CorG bound, or formal Lean witness")

if __name__=="__main__":
    main()
