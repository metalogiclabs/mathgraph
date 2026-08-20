#!/usr/bin/env python3
"""Run the complete Developmental Capability Growth V1 experiment."""

from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent

for script in ("run.py", "audit_all_boolean_refinements.py"):
    print(f"\n=== {script} ===", flush=True)
    subprocess.run([sys.executable, str(HERE / script)], check=True)

print("\n=== COMPLETE ===")
print("PASS_BOUNDED_DEVELOPMENTAL_EVENT")
print("PASS_GLOBAL_REFINEMENT_CLASS_AUDIT")
