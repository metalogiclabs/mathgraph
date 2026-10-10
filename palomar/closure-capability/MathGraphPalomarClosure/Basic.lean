namespace MathGraphPalomarClosure

inductive Token where
  | LT | LE | AND | OR | A | B | C | D
  deriving DecidableEq, Repr

inductive Pos where
  | p0 | p1 | p2 | p3
  deriving DecidableEq, Repr

/-- The old presentation symmetry: cyclic transport of coordinates. -/
def shift : Pos → Pos
  | .p0 => .p1
  | .p1 => .p2
  | .p2 => .p3
  | .p3 => .p0

def shiftN : Nat → Pos → Pos
  | 0, p => p
  | n + 1, p => shiftN n (shift p)

structure Rewrite where
  pos : Pos
  src : Token
  dst : Token
  deriving DecidableEq, Repr

/-- Capability identity modulo transformations already present in the old language. -/
def OrbitEq (r s : Rewrite) : Prop :=
  ∃ n : Nat, n < 4 ∧
    shiftN n r.pos = s.pos ∧
    r.src = s.src ∧
    r.dst = s.dst

def r0LTLE : Rewrite := ⟨.p0, .LT, .LE⟩
def r2LTLE : Rewrite := ⟨.p2, .LT, .LE⟩
def r3ANDOR : Rewrite := ⟨.p3, .AND, .OR⟩

/-- A finite state is a token at each of four coordinates. -/
abbrev State := Pos → Token

def pred : Pos → Pos
  | .p0 => .p3
  | .p1 => .p0
  | .p2 => .p1
  | .p3 => .p2

/-- Old-language state transport corresponding to the cyclic symmetry. -/
def rotate (s : State) : State := fun p => s (pred p)

/-- Apply a one-site rewrite. If the source token is absent at that position, it is a no-op. -/
def replaceAt (p : Pos) (src dst : Token) (s : State) : State :=
  fun q =>
    if q = p then
      if s q = src then dst else s q
    else s q

/-- Regime 1: old cyclic transport plus the retained LT→LE capability class. -/
inductive Step1 : State → State → Prop where
  | rot (s : State) : Step1 s (rotate s)
  | ltle (s : State) (p : Pos) : Step1 s (replaceAt p .LT .LE s)

inductive Reach1 : State → State → Prop where
  | refl (s : State) : Reach1 s s
  | tail {x y z : State} : Reach1 x y → Step1 y z → Reach1 x z

/-- Regime 2 adjoins the second AND→OR capability class. -/
inductive Step2 : State → State → Prop where
  | rot (s : State) : Step2 s (rotate s)
  | ltle (s : State) (p : Pos) : Step2 s (replaceAt p .LT .LE s)
  | andor (s : State) (p : Pos) : Step2 s (replaceAt p .AND .OR s)

inductive Reach2 : State → State → Prop where
  | refl (s : State) : Reach2 s s
  | tail {x y z : State} : Reach2 x y → Step2 y z → Reach2 x z

/-- The second-generation source state. -/
def start : State
  | .p0 => .A
  | .p1 => .LT
  | .p2 => .B
  | .p3 => .AND

/-- State after reuse of the retained first capability. -/
def afterO1 : State
  | .p0 => .A
  | .p1 => .LE
  | .p2 => .B
  | .p3 => .AND

/-- The protected future target. -/
def target : State
  | .p0 => .A
  | .p1 => .LE
  | .p2 => .B
  | .p3 => .OR

/-- Raw one-site constructor formability, before any verifier-guided discovery protocol. -/
def RawFormable (r : Rewrite) : Prop :=
  ∃ p src dst, r = ⟨p, src, dst⟩

end MathGraphPalomarClosure
