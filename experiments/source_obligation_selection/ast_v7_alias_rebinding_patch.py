#!/usr/bin/env python3
"""Minimal, checksum-gated v6->v7 alias-rebinding correction. No bug oracle."""
from hashlib import sha256
from pathlib import Path

source = Path("mathgraph_ast_obligations_v6.js")
before = source.read_bytes()
assert sha256(before).hexdigest() == "a21b1309c144d774c107bc60625ca48742fe5a7706e5a7d0cb21a43efcea9807"
old = "if(ts.isBinaryExpression(p)&&p.left===top&&p.operatorToken.kind===SK.EqualsToken)evidence.push(event('SHARED_EFFECT',n,src,'cache entry field assigned'));"
new = """if(ts.isBinaryExpression(p)&&p.left===top&&p.operatorToken.kind===SK.EqualsToken){
    const fieldMutation=ts.isPropertyAccessExpression(top)||ts.isElementAccessExpression(top);
    evidence.push(event(fieldMutation?'SHARED_EFFECT':'LOCAL_REASSIGNMENT',n,src,fieldMutation?'cache entry field assigned':'local variable rebound'));
  }"""
text = before.decode()
assert text.count(old) == 1
assert text.count("MathGraph-AST-Obligations-v6") == 1
text = text.replace(old, new).replace("MathGraph-AST-Obligations-v6", "MathGraph-AST-Obligations-v7")
result = text.encode()
assert sha256(result).hexdigest() == "dff93dd97a6c75b58e13fd176e2de18cd0c03a3ac5bd3104104e10c6a0805011"
Path("mathgraph_ast_obligations_v7.js").write_bytes(result)
print("V7_ALIAS_PROVENANCE_PATCH_EXACT")
