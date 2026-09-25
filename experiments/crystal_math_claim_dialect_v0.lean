def f1_base (p q r : Bool) : Bool := p
def f1_equiv (p q r : Bool) : Bool := p && (q || !q)
def f1_stronger (p q r : Bool) : Bool := p && q && !r
def f1_weaker (p q r : Bool) : Bool := p || r

def f2_base (p q r : Bool) : Bool := !p
def f2_equiv (p q r : Bool) : Bool := !(p || false)
def f2_stronger (p q r : Bool) : Bool := (!p) && r
def f2_weaker (p q r : Bool) : Bool := (!p) || q

def f3_base (p q r : Bool) : Bool := p || q
def f3_equiv (p q r : Bool) : Bool := q || p
def f3_stronger (p q r : Bool) : Bool := p && (!q)
def f3_weaker (p q r : Bool) : Bool := (p || q) || r

def f4_base (p q r : Bool) : Bool := p && q
def f4_equiv (p q r : Bool) : Bool := q && p
def f4_stronger (p q r : Bool) : Bool := (p && q) && r
def f4_weaker (p q r : Bool) : Bool := p || (q && r)

def f5_base (p q r : Bool) : Bool := (p && !q) || ((!p) && q)
def f5_equiv (p q r : Bool) : Bool := ((!q) && p) || (q && (!p))
def f5_stronger (p q r : Bool) : Bool := ((!p) && q) && r
def f5_weaker (p q r : Bool) : Bool := ((p && !q) || ((!p) && q)) || r

def eval8 (f : Bool → Bool → Bool → Bool) : List Bool :=
  [ f false false false
  , f false false true
  , f false true false
  , f false true true
  , f true false false
  , f true false true
  , f true true false
  , f true true true
  ]

def emit (name : String) (f : Bool → Bool → Bool → Bool) : IO Unit :=
  IO.println (name ++ "=" ++ reprStr (eval8 f))

def main : IO Unit := do
  emit "f1.base" f1_base
  emit "f1.equiv" f1_equiv
  emit "f1.stronger" f1_stronger
  emit "f1.weaker" f1_weaker
  emit "f2.base" f2_base
  emit "f2.equiv" f2_equiv
  emit "f2.stronger" f2_stronger
  emit "f2.weaker" f2_weaker
  emit "f3.base" f3_base
  emit "f3.equiv" f3_equiv
  emit "f3.stronger" f3_stronger
  emit "f3.weaker" f3_weaker
  emit "f4.base" f4_base
  emit "f4.equiv" f4_equiv
  emit "f4.stronger" f4_stronger
  emit "f4.weaker" f4_weaker
  emit "f5.base" f5_base
  emit "f5.equiv" f5_equiv
  emit "f5.stronger" f5_stronger
  emit "f5.weaker" f5_weaker
