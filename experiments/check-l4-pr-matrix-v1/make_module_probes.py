"""Finite parity candidates from frozen prior implementations; not intent proofs."""
from pathlib import Path
import hashlib,itertools,json,re,runpy,sys

def quoted(x): return json.dumps(x, ensure_ascii=False)
def lean_list(xs, array=False): return ('#[' if array else '[')+', '.join(quoted(x) if isinstance(x,str) else str(x) for x in xs)+']'
def digest(x): return hashlib.sha256(x.encode()).hexdigest()

def generate(evidence, destination):
    evidence=Path(evidence); entries=json.loads((evidence/'module-inputs.json').read_text()); out=[]
    for item in entries:
        n=item['n']; probes=[]; ns=item['path'][:-5].replace('/','.')
        def add(expr,expected,inputs): probes.append({'expression':expr,'expected':expected,'inputs':inputs})
        oracle=None
        if n!=208:oracle=runpy.run_path(str(evidence/'oracles'/f'{n}.py'),run_name='frozen_reference')
        if n==208:
            atoms=['a','b','.','[ab]','[^a]','(?:a|b)','(?:a?)','(?:ab|a)','(?:a*)']
            for atom,q,anchor in itertools.product(atoms,['','?','*','+','{0,2}','{2}','{1,}'],[False,True]):
                pattern=('^' if anchor else '')+atom+q+'b'+('$' if anchor else '')
                for text in ['','a','b','ab','aab','abb','ba','bbb','cab']:
                    add('test '+quoted(pattern)+' '+quoted(text),str(bool(re.search(pattern,text))).lower(),[pattern,text])
        elif n==211:
            for left,right,slashes,spaces in itertools.product(['','a','a|b'],['','b','b|c'],range(6),['',' ']):
                s='|'+spaces+left+'\\'*slashes+'|'+right+spaces+'|'
                add('splitRow '+quoted(s),lean_list(oracle['split_row'](s),array=True),[s])
        elif n==204:
            for prefix,num,suffix in itertools.product(['Reflection ','Reflections ','x','_',''],['001','123','999','1234'],['','x','_a',' (456)',', 124']):
                s=prefix+num+suffix
                add('labelNumbers '+quoted(s),lean_list(oracle['label_numbers'](s)),[s])
        elif n==212:
            for term,ws in itertools.product(['A x','GOpt (A x)','GSeq (A x) (B y)','A ⟨x, ⟨y, z⟩⟩','(A (B x))','A s₁ s₂'],[' ','  ','\t','\n']):
                s=term.replace(' ',ws)
                add('tokenize '+quoted(s),lean_list(oracle['tokenize'](s)),[s])
            # Actual grammar input, parsed by the previous Python implementation.
            text=(evidence/'SurfaceNode.lean').read_text(); g=oracle['Gen'](text)
            ct=lambda c:'⟨'+quoted(c[0])+', '+quoted(c[1])+', '+lean_list(c[2],True)+', '+quoted(c[3])+'⟩'
            ind=lambda i:'⟨'+quoted(i[0])+', '+quoted(i[1])+', #['+', '.join(ct(c) for c in i[2])+']⟩'
            data='#['+', '.join(ind(i) for i in g.inds)+']'
            add('render ('+data+' : Array Ind)',quoted(g.emit()),['ACTUAL_SURFACE_NODE_PARSED_BY_BASE_PYTHON'])
            item['grammar_input_sha256']=digest(text)
        row={k:v for k,v in item.items() if k!='source'}
        row.update({'module':ns,'source_sha256':digest(item['source']),'oracle_sha256':digest((evidence/'oracles'/f'{n}.py').read_text()) if oracle else None,'oracle_authority':'BASE_PYTHON_PARITY_CANDIDATE' if oracle else 'PYTHON_RE_ASCII_SUBSET_CANDIDATE','probes':probes})
        out.append(row)
    Path(destination).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print([(r['n'],len(r['probes'])) for r in out])

if __name__=='__main__':generate(sys.argv[1],sys.argv[2])
