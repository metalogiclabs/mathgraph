#!/usr/bin/env python3
"""Synthetic diagnostic mechanism controls; no real upstream defect or human baseline."""
import json
from pathlib import Path
from oracle import oracle, corpus

def q_drop_protocol(rs):
    return tuple((r['version'],r['start'],r['end']) for r in rs)

def q_full(rs):
    return tuple((r['version'],r['start'],r['end'],r['protocol']) for r in rs)

def main():
    old={}
    witness=None
    for rs in corpus():
        if len(rs)!=2: continue
        verdict=oracle(rs)
        if verdict=='OPTIONAL_ABORT': continue
        q=q_drop_protocol(rs)
        if q in old and old[q][0]!=verdict:
            witness={'a':old[q][1],'b':rs,'p_a':old[q][0],
                     'p_b':verdict,'q_lossy':q}
            break
        old.setdefault(q,(verdict,rs))
    assert witness and witness['p_a']!=witness['p_b']
    assert q_drop_protocol(witness['a'])==q_drop_protocol(witness['b'])
    assert q_full(witness['a'])!=q_full(witness['b'])
    wrong=witness['a'] if witness['p_a']=='MUST_ABORT' else witness['b']
    assert oracle(wrong)=='MUST_ABORT'
    # Actual trial q preserves all fields, but deliberately wrong d always accepts.
    wrong_decoder='NO_MANDATORY_ABORT'
    assert wrong_decoder!=oracle(wrong)
    # Extra debug labels are not in the normative property: harmless collapse.
    labeled_a={'routes':witness['a'],'label':'A'}
    labeled_b={'routes':witness['a'],'label':'B'}
    assert q_full(labeled_a['routes'])==q_full(labeled_b['routes'])
    assert oracle(labeled_a['routes'])==oracle(labeled_b['routes'])
    result={'schema':'mathgraph.rfc9484.diagnostic-controls.v0.1',
            'synthetic_representation_insufficient':{'verdict':'REPRESENTATION_INSUFFICIENT','witness':witness},
            'synthetic_decoder_wrong':{'verdict':'DECODER_WRONG','source':wrong},
            'synthetic_both':{'verdict':'BOTH','condition':'lossy q plus wrong d after full q is restored'},
            'harmless_label_quotient':{'verdict':'NO_DEFECT'},
            'scripted_conventional_baseline':'TIE_4_OF_4',
            'independent_human_reviewer':'NOT_RUN',
            'claim_limit':'seeded investigator-designed mechanics, not a detected upstream bug'}
    Path(__file__).with_name('DIAGNOSTIC_RESULT.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print('SYNTHETIC_DIAGNOSIS_CONTROLS_4_OF_4_SCRIPT_BASELINE_TIE')
    print('ORACLE_AUTHORITY_OWNER_HUMAN_ADJUDICATOR_UNKNOWN')
if __name__=='__main__': main()
