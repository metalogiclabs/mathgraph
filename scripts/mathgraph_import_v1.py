#!/usr/bin/env python3
"""Run the standalone, local-only supported-import consumer."""
from pathlib import Path
import runpy


if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "conformance/import_v1/consumer.py"),
        run_name="__main__",
    )
