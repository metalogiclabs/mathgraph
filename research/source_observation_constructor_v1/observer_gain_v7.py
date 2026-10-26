#!/usr/bin/env python3
"""MathGraph F1 V7: finite, decision-relative observer gain calculus.

This is a finite deterministic *declared-model* gate. It does not invent physical
couplings, authenticate instrument readings, or infer real author intentions.

Candidate solver: exhaustive pair-witness hitting sets + cost minimization.
Oracle must be independently implemented using fibers/partitions.
"""
from __future__ import annotations
import itertools
import json
import hashlib
import zipfile
from dataclasses import dataclass
from pathlib import Path

V5_SHA = '5972b81991a5a75b4813c20bec35802a0f1090af6daee90ddbd49d78487c7418'
V5_SOURCE='a3716b5e0aeba16b6e85965b2e5019d174328f36'

@dataclass(frozen=True)
class Sensor:
    name: str
    readings: tuple[str, ...]
    cost: int
    support: tuple[str, ...] = ()

@dataclass(frozen=True)
class Model:
    worlds: tuple[str, ...]
    decisions: tuple[str, ...]
    old: tuple[Sensor, ...]
    new: tuple[Sensor, ...]


def validate(model):
    assert len(model.worlds)>0 and len(model.worlds)==len(model.decisions)
    assert len(set(model.worlds))==len(model.worlds)
    assert len(set(s.name for s in model.old+model.new))==len(model.old+model.new)
    for s in model.old+model.new:
        assert len(s.readings)==len(model.worlds)
        assert isinstance(s.cost,int) and s.cost>0


def blockers(model, sensors):
    """World pairs requiring different decisions but sharing ALL listed signals."""
    return [(i,j) for i in range(len(model.worlds)) for j in range(i+1,len(model.worlds))
            if model.decisions[i]!=model.decisions[j]
            and all(s.readings[i]==s.readings[j] for s in sensors)]


def minimum_cost(model, sensors):
    """Constructive exact solver: each consequential pair requires a separator."""
    validate(model)
    pairs=[(i,j) for i in range(len(model.worlds)) for j in range(i+1,len(model.worlds))
           if model.decisions[i]!=model.decisions[j]]
    separating={s.name:{pair for pair in pairs if s.readings[pair[0]]!=s.readings[pair[1]]}
                for s in sensors}
    candidates=[]
    for bits in itertools.product((False,True),repeat=len(sensors)):
        choice=[s for flag,s in zip(bits,sensors) if flag]
        if all(any(pair in separating[s.name] for s in choice) for pair in pairs):
            candidates.append((sum(s.cost for s in choice),len(choice),tuple(sorted(s.name for s in choice))))
    return min(candidates) if candidates else None


def selected_sensors(model, names):
    return tuple(s for s in model.old+model.new if s.name in names)


def evaluate(model, live=None):
    validate(model)
    if live is None:live={t for s in model.old+model.new for t in s.support}
    old=tuple(s for s in model.old if set(s.support)<=set(live))
    extension=old+tuple(s for s in model.new if set(s.support)<=set(live))
    old_basis=minimum_cost(model,old)
    extended_basis=minimum_cost(model,extension)
    obstruction=blockers(model,old)
    if old_basis is None and extended_basis is not None:
        classification='NEW_DECLARED_DECISION_DISTINCTION'
    elif old_basis is not None and extended_basis is not None:
        if extended_basis[0]<old_basis[0]: classification='CHEAPER_EXISTING_DECISION_INFORMATION'
        else:classification='NO_NEW_DECISION_INFORMATION'
    elif old_basis is None and extended_basis is None:
        classification='OBSTRUCTED_WITHIN_DECLARED_GRAMMAR'
    else:raise AssertionError('adding sensors cannot make a feasible problem infeasible')
    return {'classification':classification,
            'old_basis':old_basis,'extended_basis':extended_basis,
            'old_obstruction_world_pairs':[[model.worlds[i],model.worlds[j]] for i,j in obstruction],
            'decisive_old_language_exhausted':old_basis is None,
            'new_decision_identifiable':extended_basis is not None,
            'certification_boundary':'finite supplied deterministic observation tables; not empirically source-attested'}


def independent_partition_oracle(model,sensors):
    """Independent verifier: group by the complete observation word."""
    candidates=[]
    for n in range(len(sensors)+1):
        for choice in itertools.combinations(sensors,n):
            cells={}
            for i in range(len(model.worlds)):
                key=tuple(s.readings[i] for s in choice)
                cells.setdefault(key,set()).add(model.decisions[i])
            if all(len(ds)==1 for ds in cells.values()):
                candidates.append((sum(s.cost for s in choice),len(choice),tuple(sorted(s.name for s in choice))))
    return min(candidates) if candidates else None


def native_receipt_v5_as_model(path):
    """Ground exactly TWO worlds: clean and predefined induced fault.

    Because generic pytest clean passes and mutant fails, conventional
    sensing *already* distinguishes the protected decision. No other real
    states are represented in this source observation experiment.
    """
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=V5_SHA:raise ValueError('V5_ARCHIVE_DIGEST_CHANGED')
    with zipfile.ZipFile(path) as z:
        manifest=json.loads(z.read('result.json'))
        if manifest['pinned_source']!=V5_SOURCE:raise ValueError('V5_SOURCE_MISMATCH')
        if manifest['target_original_case']!='markdown2/tm/emphasis':raise ValueError('V5_TARGET_MISMATCH')
        if not all(manifest['checks'][k] for k in ('original_passes_target',
                 'mutant_fails_protected_target','equal_information_comparator_tie',
                 'conventional_clean_passes_and_fault_fails')):
            raise ValueError('V5_NOT_CONSEQUENTIALLY_QUALIFIED')
        if manifest['generic_original']['exit']!=0 or manifest['fixed_generic']['exit']!=1:
            raise ValueError('V5_CONVENTIONAL_NOT_SEPARATING')
        if manifest['original']['exit']!=0 or manifest['candidate']['exit']==0:
            raise ValueError('V5_AUTHOR_NATIVE_NOT_SEPARATING')
    return Model(('clean','injected-fault'),('allow','deny'),
        (Sensor('generic_pytest',('pass','fail'),1,('authenticated_v5',)),),
        (Sensor('documented_author_native',('pass','fail'),2,('authenticated_v5','author_document')),))


def fixtures():
    return {
      'new_coupling':Model(('A','B','C','D'),('0','0','1','1'),
           (Sensor('visible',('0','1','0','1'),1,('source',)),),
           (Sensor('coupling',('0','0','1','1'),3,('source','coupling_permission')),)),
      'mere_relabel':Model(('A','B','C','D'),('0','0','1','1'),
           (Sensor('visible',('0','1','0','1'),1),),
           (Sensor('relabeled',('blue','red','blue','red'),2),)),
      'combined_senses':Model(('A','B','C','D'),('0','1','1','0'),
           (Sensor('visual',('0','0','1','1'),2),),
           (Sensor('acoustic',('0','1','0','1'),1),)),
      'efficiency_not_novelty':Model(('A','B','C','D'),('0','1','1','0'),
           (Sensor('old_a',('0','0','1','1'),3),Sensor('old_b',('0','1','0','1'),2)),
           (Sensor('cheap_combined',('0','1','1','0'),1),)),
      'duplicate_sensor':Model(('A','B'),('0','1'),
           (Sensor('existing',('a','b'),1),),
           (Sensor('copied',('a','b'),3),)),
      'raw_information_not_decision':Model(('A','B','C','D'),('0','0','1','1'),
           (Sensor('decision',('0','0','1','1'),2),),
           (Sensor('extra_signal',('0','1','0','1'),1),)),
    }

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--v5',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    result={key:evaluate(model) for key,model in fixtures().items()}
    result['authentic_exposed_v5']=evaluate(native_receipt_v5_as_model(a.v5))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps({key:value['classification'] for key,value in result.items()},sort_keys=True))
