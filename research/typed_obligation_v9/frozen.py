"""Frozen typed normative clause extractor, before choosing V9 source.
Conservative syntactic proposals; NOT an authoritative semantic interpreter.
"""
import re
MODAL=re.compile(r"\b(MUST NOT|SHALL NOT|MUST|SHALL|REQUIRED)\b",re.I)
def extract(source):
    result=[]
    for line_no,line in enumerate(source.splitlines(),1):
        s=" ".join(line.split())
        if not s or not MODAL.search(s):continue
        match=MODAL.search(s);modal=match.group().upper()
        tail=s[match.end():].strip()
        if modal in ("MUST NOT","SHALL NOT"):kind="prohibition"
        elif re.search(r"\b(?:encoded|encoding|alphabet|character|characters|format|syntax)\b",tail,re.I):kind="lexical_format"
        elif re.search(r"\b(?:same|equal|identical|match|consistent)\b",tail,re.I):kind="equality"
        elif re.search(r"\b(?:present|included|provided|contain|contains)\b",tail,re.I):kind="presence"
        else:kind="unresolved_normative"
        result.append(dict(line=line_no,modal=modal,kind=kind,clause=s[:500]))
    return result
def decision(obligations,source_authorized,evidence):
    if not source_authorized:return "UNKNOWN_SOURCE_WITHDRAWN"
    if not obligations:return "UNKNOWN_NO_EXTRACTED_OBLIGATION"
    if any(o["kind"]=="unresolved_normative" for o in obligations):return "UNKNOWN_UNRESOLVED_CLAUSE"
    if not evidence:return "UNKNOWN_MISSING_EVIDENCE"
    return "WARRANTED_BOUNDED" if all(evidence.get(str(i)) is True for i in range(len(obligations))) else "UNKNOWN_MISSING_EVIDENCE"
def self_test():
    examples=["X MUST NOT contain Z.","The value MUST be encoded using UTF-8.","A marker MUST be present.","The result MUST match the input.","The value MUST be valid."]
    found=extract("\n".join(examples))
    assert [x["kind"] for x in found]==["prohibition","lexical_format","presence","equality","unresolved_normative"]
    assert decision(found,False,{})=="UNKNOWN_SOURCE_WITHDRAWN"
    assert decision(found,True,{})=="UNKNOWN_UNRESOLVED_CLAUSE"
    print("FROZEN_TYPED_GRAMMAR_SELF_TEST_PASS")
if __name__=="__main__":self_test()
