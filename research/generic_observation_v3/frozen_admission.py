"""Frozen V3 admission policy. Designed before third-party target reveal.
NOT a proof of safety; conservative lexical and signature checks only.
"""
import inspect,re
EFFECT_TERMS = re.compile(r"\b(write|modify|delete|remove|update|set|create|execute|send|post|put|patch|commit|save|clear|close|open|extract|load|run|pop|insert|append|add)\b",re.I)
READ_TERMS = re.compile(r"\b(return|returns|read|reads|retrieve|retrieves|list|lists|check|checks|inspect|inspects|get|gets|query|queries|calculate|calculates|compute|computes|report|reports)\b",re.I)
def admit(name,fn):
    if name.startswith("_"):return False
    try:
        sig=inspect.signature(fn)
        params=list(sig.parameters.values())
    except (ValueError,TypeError):return False
    mandatory=[p for p in params if p.default is inspect.Parameter.empty and p.kind not in (p.VAR_POSITIONAL,p.VAR_KEYWORD)]
    if mandatory:return False
    text=(name.replace("_"," ")+" "+(inspect.getdoc(fn) or "").split("\n")[0]).lower()
    return bool(READ_TERMS.search(text)) and not EFFECT_TERMS.search(text)
def scan(obj):
    return sorted(n for n in dir(obj) if callable(getattr(obj,n,None)) and admit(n,getattr(obj,n)))
