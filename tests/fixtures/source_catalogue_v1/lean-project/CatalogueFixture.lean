import Lean

namespace CatalogueFixture

inductive Token where
  | mk : Token

axiom typeOnly : Token
theorem proofOnly : True := True.intro
theorem usesProof : True := proofOnly
-- CatalogueFixture.proofOnly and CatalogueFixture.typeOnly are text.
def text : String := "CatalogueFixture.proofOnly"
noncomputable def α : Token := typeOnly
def «name.with.dot» : Nat := 1
opaque hidden : Nat := 1

def recur : Nat → Nat
  | 0 => 0
  | n + 1 => recur n

private def secret : Nat := 0
def _user : Nat := 0

open Lean Elab Command in
run_cmd do
  liftCoreM <| addDecl (.axiomDecl { name := `CatalogueFixture.noRange, levelParams := [], type := mkConst ``Nat, isUnsafe := false })

end CatalogueFixture
