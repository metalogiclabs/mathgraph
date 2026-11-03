"""Mechanical boundaries for the fixed empty-tail consumer investigation."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent

def sha(data):return hashlib.sha256(data).hexdigest()
def remove_empty_ctors(text):
    for name in ['TCompactSeqTail','TCompactMapTail']:
        exact=f'    | nil (n : Nat) (s : SurfPos) :\n        {name} n s s ([])\n'
        if text.count(exact)!=1:raise ValueError('MUTATION_TARGET_NOT_UNIQUE:'+name)
        text=text.replace(exact,'',1)
    return text

def error_messages(text):
    # Lean's error category is authoritative; a name appearing in an unrelated
    # diagnostic is not evidence that its declaration is unavailable.
    return re.findall(r"(?m)^(?:[^\n]*?:\d+:\d+:\s*)?error(?:\([^\n)]*\)|\[[^\n]*\])?:[ \t]*(.*)$",text)

def admit(receipt,controller):
    def require(test,reason):
        if not test:raise ValueError(reason)
    def observation(o,expected):
        require(isinstance(o,dict) and o.get('complete') is True and o.get('exit')==expected,'EXECUTION_INCOMPLETE_OR_UNEXPECTED')
        require(all(isinstance(o.get(k),str) for k in ['stdout','stderr']),'OUTPUT_MISSING')
        require(len((o['stdout']+o['stderr']).encode())<=1000000,'OUTPUT_LIMIT')
    def proof(o,name,allowed):
        observation(o,0)
        prefix=re.escape("'MathGraphClaim."+name+"'")
        matches=re.findall(prefix+r" (does not depend on any axioms|depends on axioms: \[([^\]]*)\])",o['stdout'])
        require(len(matches)==1,'AXIOM_BOUNDARY_UNQUALIFIED')
        actual=[] if matches[0][0].startswith('does not') else [x.strip() for x in matches[0][1].split(',') if x.strip()]
        require(sorted(actual)==sorted(allowed),'AXIOM_BOUNDARY_UNQUALIFIED')
    try:
        c=json.loads((HERE/'contract.json').read_text());r=receipt
        require(r.get('schema')=='mathgraph.claim-consumer.receipt.v1' and r.get('controller_sha')==controller,'CONTEXT_MISMATCH')
        for k in ['repository','base_sha','head_sha']:require(r.get(k)==c[k],'SOURCE_MISMATCH')
        require(r.get('contract_sha256')==sha((HERE/'contract.json').read_bytes()),'CONTRACT_CHANGED')
        require(r.get('probes_sha256')==c['probes_sha256']=={p.name:sha(p.read_bytes()) for p in sorted((HERE/'probes').glob('*.lean'))},'CONSUMER_CHANGED')
        for k in ['source_preserved','shared_dependencies_identical','surface_identical','generator_outputs_match_checked_in','restoration_identical']:require(r.get(k) is True,k.upper())
        require(set(r.get('arms',{}))==set(c['arms']),'ARMS_INCOMPLETE')
        for arm,expected in c['arms'].items():
            row=r['arms'][arm];require(set(row)==set(expected),'PROBES_INCOMPLETE')
            for name,exitcode in expected.items():observation(row[name],exitcode)
            proof(row['source_witness'],'sourceEmptyTails',c['allowed_axioms']['source_witness']);proof(row['weak_offer'],'offered',c['allowed_axioms']['weak_offer'])
            if expected['strong_consumer']==0:proof(row['strong_consumer'],'consumer',c['allowed_axioms']['strong_consumer'])
            else:
                diagnostic=row['strong_consumer']['stdout']+row['strong_consumer']['stderr']
                messages=error_messages(diagnostic)
                require(len(messages)==2 and all(any(re.search(r'^Unknown constant [^\n]*'+re.escape(x)+r'\.nil(?:[^A-Za-z0-9_]|$)',m) for m in messages) for x in ['TCompactSeqTail','TCompactMapTail']),'UNQUALIFIED_REJECTION')
            diagnostic=row['weak_consumer']['stdout']+row['weak_consumer']['stderr']
            messages=error_messages(diagnostic)
            require(len(messages)==1 and messages[0].startswith('Type mismatch') and 'EmptyTailTrace' in diagnostic,'UNQUALIFIED_WEAKENING_REJECTION')
        proof(r.get('law'),'weakeningDoesNotAuthorize',c['allowed_axioms']['law'])
        require(all(r['arms']['head'][k]==r['arms']['head_restored'][k] for k in c['arms']['head'] if k!='module'),'WITHDRAWAL_NOT_IDENTICAL')
        return {'state':'WARRANTED_BOUNDED','proof_assumptions':c['allowed_axioms'],'axiom_free_claim':'REJECTED','terminal_form':'VERIFIED_PROOF','claim':'Two empty-tail constructor APIs support the universally quantified consumer at head.','base_obstruction':'NAMED_CONSTRUCTOR_API_UNAVAILABLE; NOT_PROOF_OF_NONEXISTENCE','weak_offering':'REJECTED_AS_SUPPORT_FOR_STRONG_OBLIGATION','whole_generator_correctness':'UNKNOWN','fresh_discovery':False,'boundary':c['boundary']}
    except (ValueError,KeyError,TypeError,AttributeError) as e:return {'state':'UNKNOWN','reason':str(e),'whole_generator_correctness':'UNKNOWN'}
