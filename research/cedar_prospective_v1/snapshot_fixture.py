"""Deterministic preregistered first author integration fixture, no outcome selection."""
from __future__ import annotations
import hashlib, json, pathlib, sys
root=pathlib.Path(sys.argv[1]).resolve()
ev=pathlib.Path(sys.argv[2]).resolve()
candidates=sorted((x for x in (root/"tests").rglob("*.json") if x.is_file()),
                  key=lambda p:p.relative_to(root).as_posix())
if not candidates:
    raise SystemExit("UNKNOWN_NO_NATIVE_AUTHOR_FIXTURES")
p=candidates[0]
relative=p.relative_to(root).as_posix()
if relative != "tests/decimal/1.json":
    raise SystemExit("UNKNOWN_FIRST_FIXTURE_CHANGED_"+relative)
b=p.read_bytes()
j=json.loads(b)
requests=j.get("requests")
if not isinstance(requests,list) or len(requests)!=2:
    raise SystemExit("UNKNOWN_PRESELECTED_FIXTURE_NO_TWO_AUTHOR_REQUESTS")
decisions=[str(x.get("decision","")).lower() for x in requests]
if decisions!=["allow","deny"]:
    raise SystemExit("UNKNOWN_PRESELECTED_FIXTURE_EXPECTED_DECISION_CHANGED")
for key in ("policies","entities","schema"):
    filename=root/j[key]
    if not filename.exists():
        raise SystemExit("UNKNOWN_AUTHOR_DEPENDENCY_ABSENT_"+key)
    (ev/(key+"_sha256.txt")).write_text(hashlib.sha256(filename.read_bytes()).hexdigest()+"  "+j[key]+"\n")
h=hashlib.sha256(b).hexdigest()
(ev/"fixture.sha256").write_text(h+"  "+relative+"\n")
out={"relative_path":relative,"fixture_sha256":h,
     "expected_decisions":decisions,"count":len(requests),
     "author_contract_source":"cedar-integration-tests README + tests/decimal/1.json",
     "source_files":{k:j[k] for k in ("policies","entities","schema")},
     "selected_without_outcome_scanning":True}
(ev/"first_fixture.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
print(json.dumps(out,sort_keys=True))
