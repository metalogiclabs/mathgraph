\\ Search live CountI/CorG prime q1 ≡3 mod8 for class group 5-torsion
\\ in the real cyclic-quartic fixed field of conjugation of
\\ F=Q(zeta5,sqrt(-q1)).
\\ Real generator y=sqrt(-q1)*(zeta5-zeta5^-1) has polynomial
\\ P_q(x)=x^4-5*q*x^2+5*q^2. degree 4, cyclic C4, contains Q(sqrt5).
\\ Only finite q in [11,500] and q%8=3; a positive hit is a
\\ CANDIDATE unramified eigenspace, NOT a strict ShaU counterexample.
\\ bnfcertify is required for every q with 5|h.

{
  count=0;
  hits=0;
  forprime(q=11,500,
    if(q%8==3,
      P=x^4-5*q*x^2+5*q^2;
      B=bnfinit(P,1);
      h=B.no;
      count++;
      print("q1=",q," hplus=",h," fivepart=",gcd(h,5));
      if(h%5==0,
        hits++;
        cf=bnfcertify(B);
        print("FIVE_HIT: q1=",q,
              " hplus=",h,
              " group=",B.cyc,
              " dplus=",B.disc,
              " certified=",cf);
        if(cf!=1,error("uncertified positive 5-class group"));
      );
    )
  );
  print("SEARCH_TOTAL=",count);
  print("FIVE_HITS=",hits);
  print("PASS: verified live CountI quartic class-group sample");
}
