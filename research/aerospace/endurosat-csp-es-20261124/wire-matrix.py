"""Golden bytes from field-width concatenation, not implementation shifts/masks."""
from pathlib import Path
import hashlib
import itertools
import json
import random
import subprocess
import sys

OUT = Path(__file__).resolve().parent
rng = random.Random(20261124)
requests, expected = [], []
case_id = 0
for version, fixup in itertools.product((1, 2), (0, 1)):
    widths = [2, 5 if version == 1 else 14, 5 if version == 1 else 14, 6, 6, 8 if version == 1 else 6]
    maxima = [(1 << w) - 1 for w in widths]
    baseline = [2, 17, 9, 13, 51, 9]
    vectors = set(itertools.product(*[(0, m) for m in maxima]))
    for axis, width in enumerate(widths):
        values = {0, 1, maxima[axis], maxima[axis] - 1}
        for exponent in range(width):
            values.update(v for v in (2**exponent - 1, 2**exponent, 2**exponent + 1) if 0 <= v <= maxima[axis])
        for value in values:
            vector = baseline.copy()
            vector[axis] = value
            vectors.add(tuple(vector))
    for _ in range(64):
        vectors.add(tuple(rng.randrange(m + 1) for m in maxima))
    for vector in sorted(vectors):
        length = (0, 1, 17, 256)[case_id % 4]
        # Layout authority: pinned source's header diagrams. Domain is explicitly valid widths.
        order = (0, 1, 2, 3, 4, 5) if version == 1 else (0, 2, 1, 3, 4, 5)
        bits = "".join(format(vector[i], f"0{widths[i]}b") for i in order)
        wire = int(bits, 2).to_bytes(len(bits) // 8, "big")
        if version == 1 and fixup:
            wire = wire[::-1]
        common = f"{version} {fixup} {length} " + " ".join(map(str, vector))
        for operation in ("E", "D"):
            requests.append(f"{case_id} {operation} {common} {wire.hex()}")
            expected.append({"id": case_id, "op": operation, "version": version, "fixup": fixup,
                             "length": length, "fields": vector, "wire": wire.hex()})
            case_id += 1
    # Native malformed-frame controls: incomplete headers must fail without changing ID/length.
    header = 4 if version == 1 else 6
    for short_length in range(header):
        wire = bytes([0xA5] * short_length).hex() or "-"
        requests.append(f"{case_id} D {version} {fixup} 0 " + " ".join(map(str, baseline)) + " " + wire)
        expected.append({"id": case_id, "op": "D", "version": version, "fixup": fixup, "length": 0,
                         "fields": baseline, "short": True, "wire": wire})
        case_id += 1
input_bytes = ("\n".join(requests) + "\n").encode()
run = subprocess.run([sys.argv[1]], input=input_bytes, capture_output=True, check=True)
label = sys.argv[2]
(OUT / "wire.input").write_bytes(input_bytes)
(OUT / f"wire-{label}.stdout").write_bytes(run.stdout)
(OUT / f"wire-{label}.stderr").write_bytes(run.stderr)
lines = run.stdout.decode().splitlines()
assert len(lines) == len(expected)
failures = []
roundtrips, encodes, decodes, short_controls = 0, 0, 0, 0
for item, line in zip(expected, lines):
    tokens = line.split()
    assert int(tokens[0]) == item["id"] and tokens[1] == item["op"]
    header = 4 if item["version"] == 1 else 6
    if item["op"] == "E":
        encodes += 1
        roundtrips += int(tokens[7])
        good = tokens[2] == item["wire"] and int(tokens[3]) == item["length"] + header and tokens[5:7] == ["1", "1"]
    else:
        values = list(map(int, tokens[2:]))
        rc, length = values[:2]
        fields, payload = values[2:8], values[8]
        if item.get("short"):
            short_controls += 1
            good = rc == -1 and length == 0x1234 and fields == list(item["fields"]) and payload == 1
        else:
            decodes += 1
            good = rc == 0 and length == item["length"] and fields == list(item["fields"]) and payload == 1
    if not good:
        failures.append({"expected": item, "actual": line})
summary = {"requests": len(expected), "encodes": encodes, "independent_decodes": decodes,
           "short_header_controls": short_controls, "native_roundtrips_passed": roundtrips,
           "golden_discrepancies": len(failures), "input_sha256": hashlib.sha256(input_bytes).hexdigest(),
           "output_sha256": hashlib.sha256(run.stdout).hexdigest()}
(OUT / f"wire-{label}.json").write_text(json.dumps({"summary": summary, "failures": failures[:12], "all_failure_ids": [x["expected"]["id"] for x in failures], "detail_boundary": "First 12 details; complete actual stdout and deterministic input retained."}, indent=2) + "\n")
print(json.dumps(summary))
if label == "mutant":
    assert len(failures) > 0 and roundtrips == encodes, "common-mode mutation control failed"
else:
    assert not failures and roundtrips == encodes
