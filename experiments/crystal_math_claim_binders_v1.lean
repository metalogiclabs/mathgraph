inductive Tri where
  | a | b | c
  deriving BEq, DecidableEq, Repr

inductive Bit where
  | z | o
  deriving BEq, DecidableEq, Repr

def triAll : List Tri := [.a, .b, .c]
def bitAll : List Bit := [.z, .o]

def triIndex : Tri → Nat
  | .a => 0
  | .b => 1
  | .c => 2

def bitIndex : Bit → Nat
  | .z => 0
  | .o => 1

def pred3 (mask : Nat) (x : Tri) : Bool :=
  mask.testBit (triIndex x)

def rel3 (mask : Nat) (x y : Tri) : Bool :=
  mask.testBit (triIndex x * 3 + triIndex y)

def rel23 (mask : Nat) (b : Bit) (x : Tri) : Bool :=
  mask.testBit (bitIndex b * 3 + triIndex x)

def triOfNat (n : Nat) : Tri :=
  match n % 3 with
  | 0 => .a
  | 1 => .b
  | _ => .c

def fun3 (code : Nat) : Tri → Tri
  | .a => triOfNat code
  | .b => triOfNat (code / 3)
  | .c => triOfNat (code / 9)

def all3 (f : Tri → Bool) : Bool := triAll.all f
def any3 (f : Tri → Bool) : Bool := triAll.any f
def allBit (f : Bit → Bool) : Bool := bitAll.all f
def anyBit (f : Bit → Bool) : Bool := bitAll.any f

def impliesB (a b : Bool) : Bool := (!a) || b

-- Family 1: subset-style universal claim with three free predicates.
def f1_base (m : Nat) : Bool :=
  let p := m % 8
  let q := (m / 8) % 8
  all3 (fun x => impliesB (pred3 p x) (pred3 q x))

def f1_equiv (m : Nat) : Bool :=
  let p := m % 8
  let q := (m / 8) % 8
  all3 (fun y => pred3 q y || !(pred3 p y))

def f1_stronger (m : Nat) : Bool :=
  let p := m % 8
  let q := (m / 8) % 8
  let r := (m / 64) % 8
  all3 (fun x => impliesB (pred3 p x) (pred3 q x && pred3 r x))

def f1_weaker (m : Nat) : Bool :=
  let p := m % 8
  let q := (m / 8) % 8
  let r := (m / 64) % 8
  all3 (fun x => impliesB (pred3 p x && pred3 r x) (pred3 q x))

-- Family 2: existential overlap claim.
def f2_base (m : Nat) : Bool :=
  let p := m % 8
  let q := (m / 8) % 8
  any3 (fun x => pred3 p x && pred3 q x)

def f2_equiv (m : Nat) : Bool :=
  let p := m % 8
  let q := (m / 8) % 8
  !(all3 (fun z => !(pred3 p z) || !(pred3 q z)))

def f2_stronger (m : Nat) : Bool :=
  let p := m % 8
  let q := (m / 8) % 8
  let r := (m / 64) % 8
  any3 (fun x => pred3 p x && pred3 q x && pred3 r x)

def f2_weaker (m : Nat) : Bool :=
  let p := m % 8
  any3 (fun x => pred3 p x)

-- Family 3: binary-relation symmetry with nested binders.
def f3_base (e : Nat) : Bool :=
  all3 (fun x => all3 (fun y => impliesB (rel3 e x y) (rel3 e y x)))

def f3_equiv (e : Nat) : Bool :=
  all3 (fun a => all3 (fun b => rel3 e b a || !(rel3 e a b)))

def f3_stronger (e : Nat) : Bool :=
  f3_base e && all3 (fun x => rel3 e x x)

def f3_weaker (e : Nat) : Bool :=
  all3 (fun y => impliesB (rel3 e .a y) (rel3 e y .a))

-- Family 4: injectivity of a typed function Tri -> Tri.
def f4_base (code : Nat) : Bool :=
  all3 (fun x => all3 (fun y => impliesB (fun3 code x == fun3 code y) (x == y)))

def f4_equiv (code : Nat) : Bool :=
  (fun3 code .a != fun3 code .b) &&
  (fun3 code .a != fun3 code .c) &&
  (fun3 code .b != fun3 code .c)

def f4_stronger (code : Nat) : Bool :=
  all3 (fun x => fun3 code x == x)

def f4_weaker (code : Nat) : Bool :=
  fun3 code .a != fun3 code .b

-- Family 5: alternating quantifiers over two distinct finite types.
def f5_base (h : Nat) : Bool :=
  allBit (fun b => any3 (fun x => rel23 h b x))

def f5_equiv (h : Nat) : Bool :=
  allBit (fun b => !(all3 (fun x => !(rel23 h b x))))

def f5_stronger (h : Nat) : Bool :=
  any3 (fun x => allBit (fun b => rel23 h b x))

def f5_weaker (h : Nat) : Bool :=
  anyBit (fun b => any3 (fun x => rel23 h b x))

def signature (count : Nat) (f : Nat → Bool) : Nat :=
  (List.range count).foldl
    (fun acc i => if f i then acc + (2 ^ i) else acc)
    0

def emit (name : String) (count : Nat) (f : Nat → Bool) : IO Unit :=
  IO.println (name ++ "=" ++ toString (signature count f))

def main : IO Unit := do
  emit "f1.base" 512 f1_base
  emit "f1.equiv" 512 f1_equiv
  emit "f1.stronger" 512 f1_stronger
  emit "f1.weaker" 512 f1_weaker
  emit "f2.base" 512 f2_base
  emit "f2.equiv" 512 f2_equiv
  emit "f2.stronger" 512 f2_stronger
  emit "f2.weaker" 512 f2_weaker
  emit "f3.base" 512 f3_base
  emit "f3.equiv" 512 f3_equiv
  emit "f3.stronger" 512 f3_stronger
  emit "f3.weaker" 512 f3_weaker
  emit "f4.base" 27 f4_base
  emit "f4.equiv" 27 f4_equiv
  emit "f4.stronger" 27 f4_stronger
  emit "f4.weaker" 27 f4_weaker
  emit "f5.base" 64 f5_base
  emit "f5.equiv" 64 f5_equiv
  emit "f5.stronger" 64 f5_stronger
  emit "f5.weaker" 64 f5_weaker
