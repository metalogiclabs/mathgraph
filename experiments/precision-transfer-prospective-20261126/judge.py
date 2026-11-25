"""Post-seal evaluation against independently authored published labels."""
import json
import statistics
from pathlib import Path
from contract import digest, reference


def main():
    out = Path("receipts")
    raw = (out / "predictions-sealed.json").read_bytes()
    assert digest(raw) == (out / "predictions-sealed.sha256").read_text().strip()
    prediction = json.loads(raw)
    selection = json.loads((out / "selection.json").read_text())
    labels_raw = (out / "labels-withheld.json").read_bytes()
    assert digest(labels_raw) == selection["labels_sha256"]
    labels = json.loads(labels_raw)
    result = dict(predictions_sha256=digest(raw), labels_sha256=digest(labels_raw), targets=[],
                  boundary="Externally curated source list and externally authored scalar integer labels. No external human blinding; general novelty and total economic advantage UNKNOWN.")
    for target in prediction["targets"]:
        row = dict(package=target["package"], version=target["version"], status=target["status"],
                   installation_seconds=target["installation"]["wall_ns"]/1e9)
        if not target.get("lanes"):
            result["targets"].append(row)
            continue
        row["source_stable"] = target["source_stable"]
        lanes = []
        for lane in target["lanes"]:
            path = out / lane["filename"]
            data = json.loads(path.read_text()) if path.exists() else dict(status="UNKNOWN_PROCESS")
            lanes.append(data)
        row["arms"] = {}
        for arm in ["candidate", "hypothesis"]:
            arms = [v for v in lanes if v.get("arm") == arm]
            row["arms"][arm] = dict(statuses=[v["status"] for v in arms],
                calls=sum(v["native_probe_calls"] for v in arms),
                value_discrepancies=sum(sum(r["status"] == "VALUE_DISCREPANCY" for r in v["observations"]) for v in arms),
                rejections=sum(sum(r["status"] == "REJECTED_INPUT" for r in v["observations"]) for v in arms),
                median_lane_seconds=statistics.median(v["wall_ns"] for v in arms)/1e9 if arms else None,
                median_process_seconds=statistics.median(v["process"]["wall_ns"] for v in target["lanes"] if arm in v["filename"])/1e9)
        controls = []
        for control in target["mutant_controls"]:
            path = out / control["filename"]
            v = json.loads(path.read_text()) if path.exists() else dict(status="UNKNOWN_PROCESS")
            controls.append({k:v.get(k) for k in ["arm", "status", "native_probe_calls", "first_nonagreement_call"]})
        row["injected_precision_controls"] = controls
        external = target["external_predictions"]
        scores = dict(total=0, oracle_label_disagreements=0, false_alarms=0, confirmed_value_discrepancies=0, rejections=0, agreements=0)
        for pred in external.get("rows", []):
            label = labels[pred["id"]]
            raw_case = bytes.fromhex(pred["hex"])
            expected = label.get("decoded", label.get("diagnostic"))
            if isinstance(expected, str) and expected.lstrip("-").isdigit():
                expected = int(expected)
            assert type(expected) is int, "unsupported independent label"
            scores["total"] += 1
            oracle = reference(raw_case)
            scores["oracle_label_disagreements"] += oracle != expected
            if pred["status"] == "REJECTED_INPUT":
                scores["rejections"] += 1
            elif pred.get("actual") == expected:
                scores["agreements"] += 1
                scores["false_alarms"] += pred["status"] != "AGREEMENT"
            else:
                scores["confirmed_value_discrepancies"] += 1
        assert scores["oracle_label_disagreements"] == 0
        row["external_labels"] = scores
        result["targets"].append(row)
    (out / "evaluation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
