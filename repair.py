from pathlib import Path
p=Path("uncertainty/PropertyKindCalculus/Uncertainty/Sensitivity.lean")
s=p.read_text()
a=s.index("    let grads0 : Array")
b=s.index("    ids.mapM",a)
assert "Tape.backwardDenseFrom" in s[a:b]
s=s[:a]+"    let grads ← Tape.backwardDenseAll (t := t) outId (SomeTensor.ofTensor (Tensor.scalar (1 : Float)))\n"+s[b:]
# preserve bounds check; h no longer used, change to anonymous condition
s=s.replace("if h : outId < t.nodes.size then","if outId < t.nodes.size then")
p.write_text(s)
