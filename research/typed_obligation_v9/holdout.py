"""Prospective RFC 4648 holdout selected after frozen grammar commit 66dbd589."""
import hashlib,json,urllib.request
from frozen import extract,decision
URL="https://www.rfc-editor.org/rfc/rfc4648.txt"
def main():
    with urllib.request.urlopen(URL,timeout=30) as f:raw=f.read()
    clauses=extract(raw.decode("utf-8"))
    counts={k:sum(x["kind"]==k for x in clauses) for k in sorted({x["kind"] for x in clauses})}
    print("SOURCE_SHA256",hashlib.sha256(raw).hexdigest())
    print("TYPED_EXTRACTION",json.dumps(counts,sort_keys=True),"TOTAL",len(clauses))
    print("SAMPLE",json.dumps(clauses[:5]))
    assert len(clauses)>0
    assert decision(clauses,False,{})=="UNKNOWN_SOURCE_WITHDRAWN"
    assert decision(clauses,True,{}) in ("UNKNOWN_MISSING_EVIDENCE","UNKNOWN_UNRESOLVED_CLAUSE")
    print("AUTHORITY_WITHDRAWAL_PASS")
    print("RESULT CANDIDATE_CLAUSES_NOT_SEMANTICALLY_VERIFIED")
if __name__=="__main__":main()
