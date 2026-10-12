#!/usr/bin/env python3
"""Local extract entrypoint; project imports follow isolated producer verification.

Both CLIs require --checkout, --source-policy, and --extractor-identity.
Publication uses --output-dir and optional --check; extraction uses
--environment and --output. Acquisition is outside this workflow.
"""
import os
import sys

if __name__ == "__main__":
    bootstrap = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalogue_bootstrap_v1.py")
    os.execv(sys.executable, [sys.executable, "-I", "-S", "-B", bootstrap, "--mode", "extract", *sys.argv[1:]])
