# Observation acquisition V1 — bounded behavioral source search

Status: LOCAL_CANDIDATE; CI NOT YET QUALIFIED. Inherits but does not modify the verified decision-sufficient compiler at commit 48eb475b40a475a697db5d385d2bb0c2b5e21bbd.

Pinned interface reference: python/cpython v3.13.7, Lib/zipfile/__init__.py (blob 05f387a950ba0a6a3c57f8ae8bc8ef437b401927).
Local interpreter: Python 3.13.5, **not identical to pinned CPython version**.

Target: decide whether the ZIP_STORED payload agrees with its recorded CRC32 when filename listing alone cannot decide.

Frozen restricted enumeration: inspect zero-required-argument public ZipFile methods, skip a fixed denylist of potentially effectful APIs, run each on eight paired intact/corrupted archive examples; choose lexicographically first method separating every pair. Candidate methods were infolist, namelist, testzip. Scores 0, 0, 8. The method selected was testzip.

Initial decoder memorized the filename on the first discovery pair and FAILED at holdout seed 100. Repaired to use the observation's None-vs-non-None type class (learned on discovery). Held-out seeds 100–139: 40/40 pairs and 80/80 classifications matched an independently written raw-ZIP-header/CRC32 checker. Permission withdrawal returned named obstruction.

Result: CANDIDATE for generic observation API selection under a restricted source grammar. **Not an independently checked GitHub CI result**, not an unanticipated physical observation primitive, not a demonstrated planner advantage, not a proof of method side-effect freedom. This source and task were chosen by the designer; the selector saw paired interventions and their pair membership. Fully informed conventional enumerator picks the same method.

Next decisive test: source-derive safety/permissions separately, avoid designer-provided restricted grammar, freeze protocol before revealing a genuinely untouched source, charge all source inspection, candidate testing, adapter creation and verification costs.
