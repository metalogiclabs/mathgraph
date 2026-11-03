"""Project caller-admitted native facts into the existing BoundaryWarrant.

Only producer-transport.mjs supplies these facts after authenticated artifact,
native and target-identity checks. This projection is not an authenticator.
"""
from dataclasses import asdict
from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from mathgraph_check.boundary_warrant import (Subject,Obligation,Relation,Verification,
    Conclusion,Dependency,BoundaryWarrant,required_dependencies,scope_identity,
    admitted_route,resolve_boundaries)
from mathgraph_check.warrant_resolution import Receipt


def digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def project(facts,current=None):
    subject=Subject(facts['subject']['repository'],facts['subject']['head_sha'],facts['subject']['sha256'])
    evidence=Dependency('evidence','producer-artifact:'+facts['artifact_sha256'],facts['artifact_sha256'])
    pairs=[]
    for name in ['observation','selection']:
        obligation=Obligation('ledger-'+name,
            'Exact producer candidate passed the reviewed finite guards' if name=='observation' else 'These same reviewed finite guards may be selected for this exact current request',
            'OPERATOR_ADOPTED_FINITE',facts['requirement_sha256'])
        relation=Relation('finite-native-'+name,'Exact reviewed guard bytes at source-bound candidate',
            (('plan_sha256',facts['plan_sha256']),('producer_gate_subject',facts['producer_parent'])))
        verification=Verification('native',('producer:' if name=='observation' else 'admission:')+
            facts['producer_controller' if name=='observation' else 'consumer_controller'],
            facts['policy_sha256'],tuple(facts['assumptions']),'receipt:'+name+':'+facts['artifact_sha256'])
        deps=required_dependencies(subject,obligation,relation,verification)+(evidence,)
        if name=='selection':deps+=(Dependency('evidence','consumer-request',digest(facts['request'])),)
        warrant=BoundaryWarrant(subject,obligation,relation,verification,
            Conclusion('SUPPORTED',tuple(facts.get('limits',('Only two operator-adopted finite obligations; not a formal theorem',
                'Selection does not substitute for fresh target native replay')))),deps)
        receipt=Receipt(verification.receipt_id,'native',scope_identity(warrant));pairs.append((warrant,receipt))
    expected={}
    for w,_ in pairs:
        for d in w.dependencies:
            if d.key in expected and expected[d.key]!=d.sha256:raise ValueError('DEPENDENCY_NAMESPACE_COLLISION')
            expected[d.key]=d.sha256
    resolution=resolve_boundaries(pairs,expected if current is None else current)
    ids=[admitted_route(w,r)[0].id for w,r in pairs]
    return {'status':resolution.states[ids[1]],'native_status':resolution.states[ids[0]],
            'claims':{'observation':ids[0],'selection':ids[1]},'states':dict(resolution.states),
            'warrants':[asdict(w) for w,_ in pairs],'current_dependencies':expected}


if __name__=='__main__':
    try:
        data=json.load(sys.stdin);print(json.dumps(project(data['facts'],data.get('current_dependencies'))))
    except Exception:
        print(json.dumps({'status':'UNKNOWN','reason':'PRODUCER_WARRANT_INCOMPLETE'}));sys.exit(1)
