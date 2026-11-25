"""Execute frozen lanes; seal predictions before external-label adjudication."""
import hashlib
import importlib
import importlib.metadata
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from contract import SEEDS, digest, reference, equal


ROOT = Path(__file__).resolve().parent
OUT = Path("receipts").resolve()


def command(args, name, timeout=600):
    started = time.perf_counter_ns()
    try:
        r = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        raw, rc = r.stdout, r.returncode
    except subprocess.TimeoutExpired as exc:
        raw, rc = (exc.stdout or b"") + b"\nTIMEOUT\n", None
    (OUT / (name + ".log")).write_bytes(raw)
    return dict(exit=rc, wall_ns=time.perf_counter_ns()-started, log_sha256=digest(raw))


def snapshot(distribution):
    dist = importlib.metadata.distribution(distribution)
    hashes = {}
    target = OUT / "installed-source" / distribution
    for f in dist.files or []:
        if str(f).endswith((".py", ".so", ".pyd")):
            p = Path(dist.locate_file(f))
            if p.is_file():
                raw = p.read_bytes()
                hashes[str(f)] = digest(raw)
                copy = target / str(f)
                copy.parent.mkdir(parents=True, exist_ok=True)
                copy.write_bytes(raw)
    assert hashes
    return hashes


def preserve_downloads(report):
    directory = OUT / "installed-archives"
    directory.mkdir(exist_ok=True)
    for row in json.loads(report.read_text())["install"]:
        info = row.get("download_info", {})
        sha = info.get("archive_info", {}).get("hashes", {}).get("sha256")
        if sha and info.get("url", "").startswith("https://"):
            path = directory / sha
            if not path.exists():
                with urllib.request.urlopen(info["url"], timeout=60) as r:
                    raw = r.read()
                assert digest(raw) == sha
                path.write_bytes(raw)


def external_inputs(module_name):
    """Prediction stage consumes encoded inputs and our frozen reader, not labels."""
    module = importlib.import_module(module_name)
    name = next((n for n in ["loads", "decode"] if callable(getattr(module, n, None))), None)
    if not name:
        return dict(status="UNKNOWN_ENTRYPOINT", rows=[])
    decoder = getattr(module, name)
    rows = []
    for case in json.loads((OUT / "heldout-inputs.json").read_text()):
        raw = bytes.fromhex(case["hex"])
        expected = reference(raw)
        row = dict(id=case["id"], hex=case["hex"], oracle=str(expected))
        try:
            value = decoder(raw)
            row.update(status="AGREEMENT" if equal(value, expected) else "VALUE_DISCREPANCY",
                       actual=value if type(value) in (int, float) else None,
                       actual_repr=repr(value), native_type=type(value).__name__)
        except Exception as exc:
            row.update(status="REJECTED_INPUT", error=type(exc).__name__, message=str(exc)[:400])
        rows.append(row)
    return dict(status="EXECUTED", rows=rows)


def main():
    started = time.monotonic()
    selection = json.loads((OUT / "selection.json").read_text())
    hypothesis = next(t for t in selection["targets"] if t["distribution"] == "hypothesis")
    common = command([sys.executable, "-m", "pip", "install", "--report", str(OUT / "hypothesis-install.json"),
                      "hypothesis==" + hypothesis["version"]], "hypothesis-install")
    assert common["exit"] == 0, "Hypothesis unavailable: comparison UNKNOWN"
    preserve_downloads(OUT / "hypothesis-install.json")
    targets = []
    for target in selection["targets"]:
        package = target["distribution"]
        if package == "hypothesis":
            continue
        record = dict(package=package, version=target["version"], lanes=[])
        report = OUT / (package + "-install.json")
        install = command([sys.executable, "-m", "pip", "install", "--report", str(report),
                           package + "==" + target["version"]], package + "-install")
        record["installation"] = install
        if install["exit"] != 0:
            record["status"] = "UNKNOWN_INSTALLATION"
            targets.append(record)
            continue
        preserve_downloads(report)
        source_before = snapshot(package)
        record["source_before"] = source_before
        for repetition, seed in enumerate(SEEDS):
            arms = ["candidate", "hypothesis"] if repetition % 2 == 0 else ["hypothesis", "candidate"]
            for arm in arms:
                filename = f"{package}-{repetition}-{arm}.json"
                args = [sys.executable, str(ROOT / "lane.py"), "--module", target["module"],
                        "--arm", arm, "--seed", str(seed), "--out", str(OUT / filename)]
                process = command(args, filename, timeout=120)
                record["lanes"].append(dict(filename=filename, process=process))
        for arm in ["candidate", "hypothesis"]:
            filename = f"{package}-mutant-{arm}.json"
            process = command([sys.executable, str(ROOT / "lane.py"), "--module", target["module"],
                               "--arm", arm, "--seed", str(SEEDS[0]), "--out", str(OUT / filename), "--mutant"], filename, timeout=120)
            record.setdefault("mutant_controls", []).append(dict(filename=filename, process=process))
        try:
            record["external_predictions"] = external_inputs(target["module"])
        except Exception as exc:
            record["external_predictions"] = dict(status="UNKNOWN_API", error=type(exc).__name__, reason=str(exc))
        source_after = snapshot(package)
        record["source_stable"] = source_after == source_before
        lane_states = [json.loads((OUT / x["filename"]).read_text()).get("status", "UNKNOWN")
                       for x in record["lanes"] if (OUT / x["filename"]).exists()]
        record["status"] = ("UNKNOWN_SOURCE_CHANGED" if not record["source_stable"]
                            else "UNKNOWN_API_OR_LANE" if len(lane_states) != len(record["lanes"]) or any(s.startswith("UNKNOWN") for s in lane_states)
                            else "EXECUTED")
        targets.append(record)
    receipt = dict(schema="mathgraph.precision-prospective-predictions.v1", targets=targets,
                   common_install=common, execution_seconds=time.monotonic()-started,
                   labels_consumed_by_detector=False, blindness="PROSPECTIVE_NOT_EXTERNAL_HUMAN_BLIND")
    raw = (json.dumps(receipt, indent=2, allow_nan=False) + "\n").encode()
    (OUT / "predictions-sealed.json").write_bytes(raw)
    (OUT / "predictions-sealed.sha256").write_text(digest(raw) + "\n")
    print(json.dumps({"predictions_sha256": digest(raw), "targets": [{k:t[k] for k in ["package", "status"]} for t in targets]}))


if __name__ == "__main__":
    main()
