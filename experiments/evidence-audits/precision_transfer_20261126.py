"""Independent raw-byte arithmetic audit and fresh actual-package replay.

This intentionally does not import the frozen constructor, reader or judge.
"""
import argparse
import ast
import hashlib
import importlib
import json
import os
import statistics
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "evidence" / "precision-transfer-native-evidence"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    def item(index):
        first, index = raw[index], index + 1
        major, argument = divmod(first, 32)
        if argument >= 24:
            width = {24: 1, 25: 2, 26: 4, 27: 8}[argument]
            argument = int.from_bytes(raw[index:index+width], "big")
            index += width
        if major < 2:
            return (argument if major == 0 else -argument-1), index
        if major == 4:
            result = []
            for _ in range(argument):
                value, index = item(index)
                result.append(value)
            return result, index
        if major == 5:
            result = {}
            for _ in range(argument):
                key, index = item(index)
                value, index = item(index)
                result[key] = value
            return result, index
        raise ValueError("outside admitted grammar")
    value, end = item(0)
    assert end == len(raw)
    return value


def native(target):
    sys.path.insert(0, str(DATA / "installed-source" / target))
    module = importlib.import_module(target)
    assert (DATA / "installed-source" / target).resolve() in Path(module.__file__).resolve().parents
    name = next(n for n in ("loads", "decode") if callable(getattr(module, n, None)))
    function = getattr(module, name)
    count = 0
    for path in sorted(DATA.glob(target + "-[0-9]-*.json")):
        lane = json.loads(path.read_text())
        for row in lane["observations"]:
            raw = bytes.fromhex(row["hex"])
            expected = decode(raw)
            assert function(raw) == expected
            count += 1
    for row in json.loads((DATA / "heldout-inputs.json").read_text()):
        raw = bytes.fromhex(row["hex"])
        assert function(raw) == decode(raw)
        count += 1
    print(json.dumps(dict(package=target, native_replayed=count, entrypoint=name,
                          module_sha256=sha(Path(module.__file__).read_bytes()), status="PASS")))


def audit():
    selection = json.loads((DATA / "selection.json").read_text())
    raw = (DATA / "predictions-sealed.json").read_bytes()
    assert sha(raw) == (DATA / "predictions-sealed.sha256").read_text().strip()
    prediction = json.loads(raw)
    manifest = json.loads((DATA / "manifest.json").read_text())
    for name, expected in manifest.items():
        assert sha((DATA / name).read_bytes()) == expected, name
    for line in (DATA / "method.sha256").read_text().splitlines():
        expected, name = line.split(None, 1)
        assert sha((ROOT / Path(name).name).read_bytes()) == expected
    labels_raw = (DATA / "labels-withheld.json").read_bytes()
    assert sha(labels_raw) == selection["labels_sha256"]
    labels = json.loads(labels_raw)
    result = dict(manifest_entries=len(manifest), original_probe_observations=0,
                  injected_observations=0, external_labels=0, targets=[])
    for target in prediction["targets"]:
        package = target["package"]
        expected = next(t for t in selection["targets"] if t["distribution"] == package)
        install = json.loads((DATA / (package + "-install.json")).read_text())
        selected = next(i for i in install["install"] if i["metadata"]["name"].lower() == package)
        assert selected["metadata"]["version"] == expected["version"]
        archive_sha = selected["download_info"]["archive_info"]["hashes"]["sha256"]
        assert archive_sha in {f["sha256"] for f in expected["release_files"]}
        assert sha((DATA / "installed-archives" / archive_sha).read_bytes()) == archive_sha
        assert target["source_stable"]
        for name, expected_hash in target["source_before"].items():
            assert sha((DATA / "installed-source" / package / name).read_bytes()) == expected_hash
        for lane in target["lanes"] + target["mutant_controls"]:
            assert lane["process"]["exit"] == 0
            data = json.loads((DATA / lane["filename"]).read_text())
            assert data["native_probe_calls"] == len(data["observations"])
            assert len(data["admission"]) == 7
            assert all(r["status"] == "AGREEMENT" for r in data["admission"])
            for row in data["observations"]:
                expected_value = decode(bytes.fromhex(row["hex"]))
                actual = ast.literal_eval(row["observed"])
                agreement = actual == expected_value
                assert agreement == row["exact"]
                assert ast.literal_eval(row["expected"]) == expected_value
                if data["injected_mutant"]:
                    assert not agreement and data["first_nonagreement_call"] == 1
                    result["injected_observations"] += 1
                else:
                    assert agreement and data["status"] == "BOUNDED_AGREEMENT"
                    result["original_probe_observations"] += 1
            if not data["injected_mutant"]:
                assert data["native_probe_calls"] == 1000
        for row in target["external_predictions"]["rows"]:
            label = labels[row["id"]]
            value = label.get("decoded", label.get("diagnostic"))
            if type(value) is str:
                value = int(value)
            assert type(value) is int
            assert decode(bytes.fromhex(row["hex"])) == value == int(row["oracle"])
            assert row["actual"] == value and row["status"] == "AGREEMENT"
            result["external_labels"] += 1
        proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--root", str(ROOT), "--native", package],
                              capture_output=True, text=True, timeout=120,
                              env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        assert proc.returncode == 0, proc.stderr
        result["targets"].append(json.loads(proc.stdout))
    assert result["original_probe_observations"] == 30000
    assert result["injected_observations"] == 6
    assert result["external_labels"] == 48
    (ROOT / "independent-audit.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--native")
    p.add_argument("--root", default=str(ROOT))
    args = p.parse_args()
    ROOT = Path(args.root).resolve()
    DATA = ROOT / "evidence" / "precision-transfer-native-evidence"
    native(args.native) if args.native else audit()
