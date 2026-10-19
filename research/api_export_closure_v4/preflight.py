#!/usr/bin/env python3
"""No-future self-tests, including physical export mutation and static UNKNOWN gates."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory


def load(path):
    spec = importlib.util.spec_from_file_location("v4_static_exports", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load(Path(__file__).with_name("resolve.py"))
with TemporaryDirectory() as d:
    root = Path(d)
    pkg = root / "demo"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(
        "from .special import *\nfrom .core import *\n"
        "from .version import __version__\n"
    )
    core = pkg / "core.py"
    original_core = (
        "from typing import Literal\n"
        "__all__ = ['slugify', 'truncate']\n"
        "def slugify(text):\n    return text.lower().replace(' ', '-')\n"
        "def truncate(text):\n    return text[:5]\n"
    )
    core.write_text(original_core)
    (pkg / "special.py").write_text("def utility(x):\n    return x\n")
    (pkg / "version.py").write_text("__version__ = '0.0.0'\n")
    baseline = m.scan(root)
    assert baseline["status"] == "STATIC_EXPORT_CLOSURE_BOUNDED", baseline
    assert "slugify" in baseline["exports"] and "truncate" in baseline["exports"]
    assert "*" not in baseline["exports"]
    assert len(baseline["api_manifest"]["files"]) == 3
    assert len(baseline["api_manifest"]["edges"]) == 2
    core.write_text(original_core.replace("['slugify', 'truncate']", "['truncate']"))
    changed = m.scan(root)
    assert "slugify" not in changed["exports"] and "truncate" in changed["exports"]
    assert changed["api_sha256"] != baseline["api_sha256"]
    core.write_text(original_core)
    restored = m.scan(root)
    assert restored["api_sha256"] == baseline["api_sha256"]
    assert restored["exports"] == baseline["exports"]
    core.write_text("__all__ = helper()\ndef helper(): return ['slugify']\n")
    unsupported = m.scan(root)
    assert unsupported["status"].startswith("UNKNOWN_STATIC_EXPORT:DYNAMIC_ALL"), unsupported
    core.write_text("from .cycle import *\n")
    (pkg / "cycle.py").write_text("from .core import *\n")
    assert "CYCLIC_STAR_IMPORT" in m.scan(root)["status"]
    (pkg / "__init__.py").write_text("from .unavailable import *\n")
    assert "MISSING_OR_AMBIGUOUS_LOCAL_MODULE" in m.scan(root)["status"]
    (pkg / "__init__.py").write_text("def dump(x): return x\n")
    no_relation = m.scan(root)
    assert no_relation["status"] == "STATIC_EXPORT_CLOSURE_BOUNDED"
    assert no_relation["exports"] == ["dump"]

print("STATIC_EXPORT_CLOSURE_SYNTHETIC_GREEN_WITH_MUTATION_AND_RESTORATION")
