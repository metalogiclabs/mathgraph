\\ Independent PARI/GP arithmetic check for the first CountI/CorG Selmer example.
\\ F = Q(zeta_5, sqrt(-59)); primitive generator zeta_5+sqrt(-59).
\\ Minimal polynomial is Res_z(Phi_5(z), (x-z)^2+59).
\\ Exact absolute field discriminant = 5^6 * 59^4.
\\ This computes Cl(F), NOT directly the strict Selmer group ShaU.

{
  P=x^8+2*x^7+239*x^6+358*x^5+21186*x^4+20890*x^3+824410*x^2+396600*x+11915405;
  print("POLY=",P);
  print("FIELD_DEGREE=",poldegree(P));
  nf=nfinit(P);
  print("DISCRIMINANT=",nf.disc);
  if(poldegree(P)!=8,error("unexpected field degree"));
  if(nf.disc!=189333765625,error("wrong field discriminant"));
  B=bnfinit(P,1);
  print("CLASS_NUMBER=",B.no);
  print("CLASS_GROUP_INVARIANTS=",B.cyc);
  C=bnfcertify(B);
  print("CERTIFIED=",C);
  if(C!=1,error("class group not unconditionally certified"));
  if(B.no%5==0,print("FIVE_CLASS_GROUP=PRESENT"),print("FIVE_CLASS_GROUP=TRIVIAL"));
  print("PASS: certified F=Q(zeta5,sqrt(-59)) class group");
}
