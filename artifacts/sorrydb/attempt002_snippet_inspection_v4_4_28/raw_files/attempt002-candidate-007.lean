/- Author: E.W.Ayers © 2019 -/
import ..equate

open robot

constant k : Type
constant V : Type
constant k_f : field k
noncomputable instance : field k := k_f
constant V_ac : add_comm_group V
noncomputable instance : add_comm_group V := V_ac

constant p : k → V → V
infixr ` • `: 100 := p
constant is_linear : (V → V) → Prop
constant adj : (V → V) → (V → V)
variables {μ ν : k} {u v w x y z : V} {A : V → V}
postfix `†`:200 := adj
@[equate] axiom L1 {A : V → V} : is_linear A → A (x + y) = A x + A y
@[equate] axiom L2 {A : V → V}: is_linear A → μ • A x = A (μ • x)
@[equate] axiom SS : μ • ν • x = (μ * ν) • x
@[equate] axiom LL : μ • (x + y) = μ • x + μ • y
constant ip : V → V → k
notation `⟪` x `,` y `⟫`  := ip x y
@[equate] axiom ipL : ⟪x + y,z⟫ = ⟪x,z⟫ + ⟪y,z⟫
@[equate] axiom ipR : ⟪x, y + z⟫ = ⟪x,y⟫ + ⟪x,z⟫
@[equate] axiom ipSL : ⟪μ • x,z⟫ = μ * ⟪x,z⟫
@[equate] axiom ipSR : ⟪x,μ • z⟫ = μ * ⟪x,z⟫
@[equate] axiom ADJ : is_linear A → ⟪A† x, y ⟫ = ⟪x, A y⟫
@[equate] lemma COMP_DEF {α β γ} {f : β → γ} {g : α → β} {x : α} : (f ∘ g) x = f (g x) := rfl

open tactic

example (il : is_linear A) :
    μ • A (x) + ν • A (y) = A (μ • x + ν • y)  :=
by equate 

example (il : is_linear A) : 
    ⟪A† (x + y) + w, z⟫ = ⟪A† x + A† y + w ,z⟫ := 
by equate 
example (il : is_linear A) : 
    ⟪A† (x + y) + (w + v), z⟫ = ⟪A† x + v + A† y + w,z⟫ := 
by equate -- [FIXME]
example (il : is_linear A) :
    ⟪ A† ( u + v ) + w , x ⟫ = ⟪ A† u + w + A† v , x ⟫
:= by equate

example (il : is_linear A) : 
    ⟪A† x + A† y ,z⟫ = ⟪A† (x + y), z⟫ := 
by equate 
example (il : is_linear A) : 
    ⟪(x + y),  A z⟫ = ⟪A† x + A† y ,z⟫ := 
by equate 

@[equate] lemma adj_linear (il : is_linear A) : 
    ⟪A† (x + y), z⟫ = ⟪A† x + A† y ,z⟫ := 
by equate 
-- try the same two problems again but this time with the adjoint lemma.
example (il : is_linear A) : 
    ⟪A† (x + y) + w, z⟫ = ⟪A† x + A† y + w ,z⟫ := 
by equate 
example (il : is_linear A) :
    ⟪ A† ( u + v ) + w , x ⟫ = ⟪ A† u + w + A† v , x ⟫
:= by equate

/- Can it find a better solution to the problem if we add in the proof that A† is linear? -/
@[equate] lemma adj_linear_2 (il : is_linear A) : A†(x + y) = A†x + A†y := sorry

example (il : is_linear A) :
    ⟪ A† ( u + v ) + w , x ⟫ = ⟪ A† u + w + A† v , x ⟫
:= by equate