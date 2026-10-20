"""Bind source-generated Lean files to preregistered closed-value theorem probes.

The probes are compiled by the pinned Lean toolchain. Never infer success solely
from the presence of expected text in a generated file.
"""
from __future__ import annotations
import pathlib
import sys

evidence = pathlib.Path(sys.argv[1]).resolve()
for role, symbol, output in (
    ("drop", "fn0", "DropVerified.lean"),
    ("control", "control", "ControlVerified.lean"),
):
    folder = evidence / f"generated_{role}"
    files = sorted(folder.rglob("*.lean"))
    if len(files) != 1:
        raise SystemExit(f"FAIL_CLOSED_{role.upper()}_LEAN_FILE_COUNT={len(files)}: {[str(f) for f in files]}")
    content = files[0].read_text()
    # The target definition must actually have been generated; templates do not count.
    import re
    if re.search(r"(?m)^\s*(?:private\s+)?def\s+" + symbol + r"\b", content) is None:
        raise SystemExit(f"FAIL_CLOSED_NO_GENERATED_SYMBOL: {role}:{symbol}")
    target = evidence / "verified" / output
    target.write_text(
        content
        + "\n-- MathGraph preregistered, exact generated function reduction check.\n"
        + f"theorem mathgraph_{role}_result : one_guard.{symbol} = ok 0#i32 := by rfl\n"
        + f"#print axioms mathgraph_{role}_result\n"
        + f'#eval "MATHGRAPH_{role.upper()}_LEAN_THEOREM_PASSED"\n'
    )
    (evidence / f"{role}_files.txt").write_text(str(files[0]) + "\n")
    print("PREPARED", role, symbol, files[0], "->", target)
