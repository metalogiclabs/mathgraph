import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_v2

_original = run_v2.v1.infer_recolor

def safe_infer_recolor(pairs, pre=lambda x: x):
    for inp, _ in pairs:
        try:
            x = pre(inp)
        except Exception:
            return None
        if x is None:
            return None
    return _original(pairs, pre=pre)

run_v2.v1.infer_recolor = safe_infer_recolor

if __name__ == "__main__":
    run_v2.main()
