namespace CrystalFreyPackageView

def freyCurveInt (P : CrystalFreyPackageView) : WeierstrassCurve ℤ where
  a₁ := 1
  a₂ := (P.b ^ P.p - 1 - P.a ^ P.p) / 4
  a₃ := 0
  a₄ := -(P.a ^ P.p) * (P.b ^ P.p) / 16
  a₆ := 0

def freyCurve (P : CrystalFreyPackageView) : WeierstrassCurve ℚ where
  a₁ := 1
  a₂ := (P.b ^ P.p - 1 - P.a ^ P.p) / 4
  a₃ := 0
  a₄ := -(P.a ^ P.p) * (P.b ^ P.p) / 16
  a₆ := 0

end CrystalFreyPackageView

theorem freyCurveInt_commutes (P : FreyPackage) :
    CrystalFreyPackageView.freyCurveInt (freyPackageToCrystal P) =
      FreyPackage.freyCurveInt P := by
  rfl

theorem freyCurve_commutes (P : FreyPackage) :
    CrystalFreyPackageView.freyCurve (freyPackageToCrystal P) =
      FreyPackage.freyCurve P := by
  rfl
