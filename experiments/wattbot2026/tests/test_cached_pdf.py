import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cached_pdf import self_test, cached_download


def test_exact_version_cache_reuse_and_poison_refusal():
    with tempfile.TemporaryDirectory() as folder:
        self_test(Path(folder))
