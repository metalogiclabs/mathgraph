set_option autoImplicit false

/-- Canonical, consequence-neutral waist for the shared FLT Frey-package schema. -/
structure CrystalFreyPackageView where
  a : ℤ
  b : ℤ
  c : ℤ
  ha0 : a ≠ 0
  hb0 : b ≠ 0
  hc0 : c ≠ 0
  p : ℕ
  pp : Nat.Prime p
  hp5 : 5 ≤ p
  hFLT : a ^ p + b ^ p = c ^ p
  hgcdab : gcd a b = 1
  ha4 : (a : ZMod 4) = 3
  hb2 : (b : ZMod 2) = 0

def freyPackageToCrystal (P : FreyPackage) : CrystalFreyPackageView where
  a := P.a
  b := P.b
  c := P.c
  ha0 := P.ha0
  hb0 := P.hb0
  hc0 := P.hc0
  p := P.p
  pp := P.pp
  hp5 := P.hp5
  hFLT := P.hFLT
  hgcdab := P.hgcdab
  ha4 := P.ha4
  hb2 := P.hb2

def crystalToFreyPackage (P : CrystalFreyPackageView) : FreyPackage where
  a := P.a
  b := P.b
  c := P.c
  ha0 := P.ha0
  hb0 := P.hb0
  hc0 := P.hc0
  p := P.p
  pp := P.pp
  hp5 := P.hp5
  hFLT := P.hFLT
  hgcdab := P.hgcdab
  ha4 := P.ha4
  hb2 := P.hb2

theorem crystalToFreyPackage_toCrystal (P : FreyPackage) :
    crystalToFreyPackage (freyPackageToCrystal P) = P := by
  cases P
  rfl

theorem freyPackageToCrystal_fromCrystal (P : CrystalFreyPackageView) :
    freyPackageToCrystal (crystalToFreyPackage P) = P := by
  cases P
  rfl

def crystalFreyPackageEquiv : FreyPackage ≃ CrystalFreyPackageView where
  toFun := freyPackageToCrystal
  invFun := crystalToFreyPackage
  left_inv := crystalToFreyPackage_toCrystal
  right_inv := freyPackageToCrystal_fromCrystal

theorem freyPackage_nonempty_iff :
    Nonempty FreyPackage ↔ Nonempty CrystalFreyPackageView := by
  constructor
  · rintro ⟨P⟩
    exact ⟨freyPackageToCrystal P⟩
  · rintro ⟨P⟩
    exact ⟨crystalToFreyPackage P⟩


/-- The FLT proof-spine obstruction (no Frey package) is preserved by the same view. -/
theorem freyPackage_isEmpty_iff :
    IsEmpty FreyPackage ↔ IsEmpty CrystalFreyPackageView := by
  constructor
  · intro h
    exact ⟨fun P => h.false (crystalToFreyPackage P)⟩
  · intro h
    exact ⟨fun P => h.false (freyPackageToCrystal P)⟩
