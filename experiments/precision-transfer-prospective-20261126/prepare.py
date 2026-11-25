"""Freeze external registry/versions/labels before any target execution."""
import hashlib
import json
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

VECTOR_REVISION = "aba89b653e484bc8573c22f3ff35641d79dfd8c1"
PACKAGES = ("cbor2", "flynn", "flunn")


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "MathGraph-prospective-contract-trial"}), timeout=60) as r:
        return r.read()


class Registry(HTMLParser):
    def __init__(self):
        super().__init__()
        self.heading = None
        self.collect = False
        self.parts = []
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == "h2":
            self.heading = []
            self.collect = False
        if tag == "a" and self.collect:
            self.links.extend(v for k, v in attrs if k == "href")
    def handle_data(self, text):
        if self.heading is not None:
            self.heading.append(text)
        if self.collect:
            self.parts.append(text)
    def handle_endtag(self, tag):
        if tag == "h2" and self.heading is not None:
            self.collect = "".join(self.heading).strip().lower() == "python"
            self.heading = None


def main():
    started = time.monotonic()
    out = Path("receipts")
    out.mkdir(exist_ok=True)
    registry = get("https://cbor.io/impls.html")
    (out / "registry.html").write_bytes(registry)
    parser = Registry()
    parser.feed(registry.decode())
    text = " ".join(parser.parts).lower()
    assert all(name in text for name in PACKAGES) and len(parser.links) == 3, "Registry selection changed; no substitution permitted"
    # All three named Python implementations in this externally curated section.
    selection = dict(schema="mathgraph.external-source-transfer.v1", selection="all three named Python registry entries; no outcome-based substitution",
                     registry_url="https://cbor.io/impls.html", registry_sha256=hashlib.sha256(registry).hexdigest(),
                     python_registry_text=text, python_registry_links=parser.links, targets=[])
    for package in PACKAGES + ("hypothesis",):
        raw = get(f"https://pypi.org/pypi/{package}/json")
        (out / (package + "-pypi.json")).write_bytes(raw)
        meta = json.loads(raw)
        selection["targets"].append(dict(distribution=package, module=package, version=meta["info"]["version"],
                                          metadata_sha256=hashlib.sha256(raw).hexdigest(),
                                          release_files=[dict(filename=f["filename"], url=f["url"], sha256=f["digests"]["sha256"]) for f in meta["urls"]]))
    labels = get(f"https://raw.githubusercontent.com/cbor/test-vectors/{VECTOR_REVISION}/appendix_a.json")
    (out / "labels-withheld.json").write_bytes(labels)
    # Export only inputs. Expected values are not passed to the frozen probes.
    inputs = [dict(id=i, hex=v["hex"]) for i, v in enumerate(json.loads(labels))
              if v.get("hex") and bytes.fromhex(v["hex"])[0] >> 5 in (0, 1)]
    assert inputs, "empty external integer-vector cohort"
    (out / "heldout-inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    selection.update(labels_revision=VECTOR_REVISION, labels_sha256=hashlib.sha256(labels).hexdigest(),
                     created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), preparation_seconds=time.monotonic()-started,
                     source_inspection_before_freeze="none of the selected implementation bodies read in this trial",
                     blindness="PROSPECTIVE_TRANSFER; externally published labels; no independent human blinding or model-training exclusion established")
    (out / "selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    print(json.dumps({"selection_sha256": hashlib.sha256((out / "selection.json").read_bytes()).hexdigest(),
                      "targets": [{k: t[k] for k in ["distribution", "version"]} for t in selection["targets"]],
                      "labels_sha256": selection["labels_sha256"]}))


if __name__ == "__main__":
    main()
