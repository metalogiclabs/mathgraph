import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/sorrydb/sorrydb_v4_2_3_hydrate_one_repo.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sorrydb_v423_hydrate", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_safe_url_accepts_github_https():
    mod = load_module()
    assert mod.safe_url("https://github.com/siddhartha-gadgil/MetaExamples")


def test_safe_url_rejects_shell_metacharacters():
    mod = load_module()
    assert not mod.safe_url("https://github.com/a/b; rm -rf /")
    assert not mod.safe_url("git@github.com:a/b")
    assert not mod.safe_url("https://example.com/a/b")


def test_free_gb_returns_float_for_tmp_path(tmp_path):
    mod = load_module()
    value = mod.free_gb(tmp_path / "missing" / "nested")
    assert isinstance(value, float)
    assert value >= 0
