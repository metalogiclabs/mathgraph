"""V8 frozen grammar before choosing heldout standard. This is intentionally narrow."""
import re
def extract(text):
    lines=re.split(r'(?<=[.!?])\s+',text)
    out=[]
    for sentence in lines:
        if not re.search(r'\b(MUST|SHALL|REQUIRED)\b',sentence):continue
        # generic required-presence schema, no protocol-specific checksum words
        m=re.search(r'\b(?:MUST|SHALL)\s+(?:always\s+)?(?:be\s+)?(?:present|included|provided)\b',sentence,re.I)
        if m:out.append({"kind":"presence","statement":sentence.strip()[:500]})
    return out
