"""Prospective target RFC 8259 selected after frozen.py commit 08f9ad8."""
import urllib.request,hashlib,json
from frozen import extract
url="https://www.rfc-editor.org/rfc/rfc8259.txt"
with urllib.request.urlopen(url,timeout=20) as f: raw=f.read()
text=raw.decode("utf-8")
items=extract(text)
print("SOURCE",url,"SHA256",hashlib.sha256(raw).hexdigest())
print("EXTRACTED_COUNT",len(items))
print("EXTRACTED_EXAMPLES",json.dumps(items[:8]))
targets=["MUST be encoded using UTF-8","MUST NOT add a byte order mark","MUST be lowercase"]
print("TARGETS_PRESENT",[t in text for t in targets])
assert all(t in text for t in targets)
# The frozen restricted presence grammar cannot express encoding and prohibitions.
assert not any("UTF-8" in x["statement"] or "byte order mark" in x["statement"] for x in items)
print("RESULT UNKNOWN_MISSING_GRAMMAR_FOR_SOURCE_OBLIGATIONS")
