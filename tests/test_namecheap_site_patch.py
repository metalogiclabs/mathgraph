import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "patch_mathgraph_org_epistemic_status.py"

spec = importlib.util.spec_from_file_location("mathgraph_site_patch", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def _fixture() -> str:
    return """<!doctype html>
<html><body>
<h1>MathGraph</h1>
<p>Verifiers decide what is true. MathGraph remembers how truth was proved, refuted, blocked, and reused.</p>
<h3>ARCHITECTURE</h3>
<p>Existing architecture text.</p>
<h3>AI RELIABILITY LAYER</h3>
<p>Existing AI reliability text.</p>
</body></html>
"""


def test_patch_is_surgical_and_idempotent():
    original = _fixture()
    patched = mod.patch_text(original)
    mod.verify_text(patched)

    assert patched.count(mod.SECTION_MARKER + ":BEGIN") == 1
    assert patched.count(mod.SECTION_MARKER + ":END") == 1
    assert "Existing architecture text." in patched
    assert "Existing AI reliability text." in patched
    assert patched.index("EPISTEMIC STATUS") < patched.index("AI RELIABILITY LAYER")
    assert mod.patch_text(patched) == patched


def test_find_live_page_requires_unique_match(tmp_path):
    root = tmp_path / "public_html"
    root.mkdir()
    page = root / "index.html"
    page.write_text(_fixture(), encoding="utf-8")

    assert mod.find_live_page([root]) == page.resolve()

    other = root / "copy.html"
    other.write_text(_fixture(), encoding="utf-8")

    try:
        mod.find_live_page([root])
    except SystemExit as exc:
        assert "exactly one" in str(exc)
    else:
        raise AssertionError("ambiguous live pages must fail closed")


def test_patch_refuses_unknown_page_structure():
    text = "<html><body><p>unrelated site</p></body></html>"
    try:
        mod.patch_text(text)
    except SystemExit as exc:
        assert "insertion boundary" in str(exc)
    else:
        raise AssertionError("unknown page structure must not be modified")


def test_live_section_preserves_authority_language():
    patched = mod.patch_text(_fixture())
    assert "only axis that can carry mathematical truth authority" in patched
    assert "no non-verification axis can promote truth" in patched
    assert "VERIFIED_PROOF" in patched
    assert "UNDIGESTED" in patched
    assert "statement fidelity UNKNOWN" in patched
    assert "generalization UNKNOWN" in patched
