#!/usr/bin/env python3
"""Replay the observed two-message discrepancy in published Orekit 13.1.10.

Usage: python3 replay.py /path/to/Orekit/src/test/resources/regular-data
Requires a Java 21 runtime. All downloads are versioned Maven Central artifacts
and must match the recorded SHA-256 values. No live spacecraft data are used.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request

here = Path(__file__).resolve().parent
receipt = json.loads((here / "minimal-receipt.json").read_text())
source = here / "MinimalAemRate.java"
assert hashlib.sha256(source.read_bytes()).hexdigest() == receipt["source_sha256"]
data = Path(sys.argv[1]).resolve()
assert data.is_dir(), data
with tempfile.TemporaryDirectory(prefix="orekit-minimal-") as work:
    root = Path(work)
    deps = []
    for artifact in receipt["artifacts"]:
        content = urllib.request.urlopen(artifact["url"], timeout=60).read()
        assert hashlib.sha256(content).hexdigest() == artifact["sha256"], artifact["name"]
        path = root / artifact["name"]
        path.write_bytes(content)
        if artifact["name"] != "ecj.jar": deps.append(str(path))
    classpath = os.pathsep.join(deps)
    classes = root / "classes"
    classes.mkdir()
    subprocess.run(["java", "-jar", str(root / "ecj.jar"), "-8", "-classpath", classpath,
                    "-d", str(classes), str(source)], check=True)
    output = subprocess.check_output(["java", "-cp", str(classes) + os.pathsep + classpath,
                                      "MinimalAemRate", str(data)], text=True)
    print(output, end="")
    assert output == receipt["stdout"], "Output differs from the recorded binary replay"
    print("REPRODUCED the recorded bounded discrepancy; no broader conclusion asserted.")
