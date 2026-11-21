\\ Identify the actual Gal(Fplus/Q)=C4 action on Cl(Fplus)[5]
\\ and local Frobenius obstructions for CountI e=1 or e=3.
\\ Fplus=Q(y), y^4 -5q*y^2 +5q^2=0,
\\ y=sqrt(-q)*(zeta5-zeta5^-1).
\\ Sigma: zeta5 -> zeta5^2, sqrt(-q)->sqrt(-q)
\\ acts on y as sigma(y)=y^3/q-3y, order 4.
\\ θ_e(sigma)=2^(-e) mod5; e=1 -> 3, e=3 -> 2.
\\ Use bnrgaloismatrix(bnrinit(B,1),sigma) to find
\\ actual class group character, and bnfisprincipal for primes.

{
  for (j=1,2,
    q=if(j==1,347,443);
    P=x^4-5*q*x^2+5*q^2;
    B=bnfinit(P,1);
    if(B.no!=5,error("unexpected quartic class number"));
    cf=bnfcertify(B);
    if(cf!=1,error("class group lacks unconditional certificate"));
    sigma=x^3/q-3*x;
    R=bnrinit(B,1);
    A=bnrgaloismatrix(R,sigma);
    action=lift(Mod(A[1,1],5));
    if(action!=2 && action!=3,error("unexpected order-four class group action"));
    e=if(action==3,1,3);
    print("QUARTIC_q=",q," class_group=",B.cyc,
          " certified=",cf," aut_action=",action," matching_e=",e);
    for (ip=1,4,
      prime=if(ip==1,2,if(ip==2,5,if(ip==3,q,167)));
      dec=idealprimedec(B,prime);
      print("PRIME_q=",q," p=",prime," number_of_primes=",#dec);
      for (i=1,#dec,
        class=bnfisprincipal(B,dec[i])[1];
        print("CLASS_q=",q," p=",prime," i=",i," exponent=",class);
        if(class!=[0]~,error("local prime has nonzero five-class"));
      );
    );
    print("PASS: quartic class eigenspace and local prime classes, q=",q);
  );
}
