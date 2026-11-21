\\ Second actual CountI host character: psi=(.|131), ell=5, e=1.
\\ Compare with q1=59 where the 5-class group vanished.
\\ F=Q(zeta5,sqrt(-131)); resultant Phi5(z), (x-z)^2+131.
\\ Class group of F is only a necessary input for exact ShaU,
\\ not the twisted Selmer group itself.
{
  P=x^8+2*x^7+527*x^6+790*x^5+103626*x^4+102970*x^3+9008218*x^2+4427016*x+292268861;
  print("POLY=",P);
  nf=nfinit(P);
  print("FIELD_DEGREE=",poldegree(P));
  print("DISCRIMINANT=",nf.disc);
  if(poldegree(P)!=8,error("unexpected field degree"));
  if(nf.disc!=4601561265625,error("wrong field discriminant"));
  B=bnfinit(P,1);
  print("CLASS_NUMBER=",B.no);
  print("CLASS_GROUP_INVARIANTS=",B.cyc);
  cert=bnfcertify(B);
  print("CERTIFIED=",cert);
  if(cert!=1,error("class group not unconditionally certified"));
  if(B.no%5==0,print("FIVE_CLASS_GROUP=PRESENT"),print("FIVE_CLASS_GROUP=TRIVIAL"));
  print("PASS: certified F=Q(zeta5,sqrt(-131)) class group");
}
