from pathlib import Path
def rows(p):
    lines=[s for s in Path(p).read_text().splitlines() if s.startswith("CASE ")]
    assert len(lines)==132, (p,len(lines))
    return lines
a,b=rows("before.txt"),rows("after.txt")
for x,y in zip(a,b):
    assert x.split(" gradient=")[0].split(" ERROR")[0]==y.split(" gradient=")[0].split(" ERROR")[0],(x,y)
assert any("pass=false" in x for x in a), "original discrepancy absent"
assert all("pass=true" in x for x in b), [x for x in b if "pass=true" not in x]
assert all("pass=true" in x for x in a if "op=none " in x)
print("before failures:",sum("pass=true" not in x for x in a),"after failures: 0 / 132")
