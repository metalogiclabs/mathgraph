import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_artifact():
 data=json.loads((ROOT/"artifacts/lawbook/finite_htilt_coordinate_residual_envelope_exists_v1.json").read_text()); assert data["status"]=="VERIFIED_PROOF"; assert "residual_envelope_exists" in " ".join(data["verified_declarations"]); n=" ".join(data["boundary"]["does_not_prove"]).lower(); [(_ for _ in ()).throw(AssertionError(t)) if t not in n else None for t in ("eigenvalue","matrix spectrum","perron-root","perron-frobenius")]
def test_fixture_and_docs():
 t=(ROOT/"examples/verifier_fixtures/lean/htilt_coordinate_residual_envelope_exists.lean").read_text(); assert "import HTilt.CoordinateChecklist" in t; assert "theorem residual_envelope_exists" in t; d=(ROOT/"docs/finite_htilt_coordinate_residual_envelope_exists_v1.md").read_text(); assert "finite" in d.lower() and "exists some real `B`" in d and "pre-spectral" in d
