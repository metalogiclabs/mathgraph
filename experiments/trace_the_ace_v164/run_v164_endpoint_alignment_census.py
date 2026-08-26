#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd

QUESTION_RE=re.compile(r"\?|\b(?:what|which|how|why|can you|could you|tell me|work out|calculate|solve|find)\b",re.I)
AGREE_RE=re.compile(r"^(?:yeah|yes|yep|okay|ok|mm+|mhm|uh huh|right|sure)[.! ]*$",re.I)
DIGIT_RE=re.compile(r"\d+")

def headers(p): return list(pd.read_csv(p,nrows=0).columns)
def digits(x):
    m=DIGIT_RE.findall(str(x)); return int(m[-1]) if m else None

def main(a):
    fh,lh=headers(a.features),headers(a.labels)
    print('FEATURE_HEADERS',fh,flush=True); print('LABEL_HEADERS',lh,flush=True)
    req={'response_id','session_id','learning_objective_id','learning_objective'}
    if not req.issubset(fh): raise ValueError(f'missing feature cols {sorted(req-set(fh))}')
    f=pd.read_csv(a.features,dtype=str); y=pd.read_csv(a.labels,dtype=str)
    if f.response_id.duplicated().any(): raise ValueError('response_id not unique')
    sess_counts=f.groupby('session_id').size().to_dict()
    session_rows=[]; missing=[]; transcript_headers=Counter(); id_prefix_matches=0; id_digit_rows=0
    for sid,g in f.groupby('session_id',sort=False):
        p=a.transcripts/f'{sid}.csv'
        if not p.exists(): missing.append(str(sid)); continue
        th=headers(p); transcript_headers[tuple(th)]+=1
        d=pd.read_csv(p,dtype=str).fillna('')
        roles=d['role'].astype(str).str.lower() if 'role' in d else pd.Series([],dtype=str)
        cont=d['content'].astype(str) if 'content' in d else pd.Series([],dtype=str)
        n_all=len(d); n_student=int((roles=='student').sum()); n_tutor=int((roles=='tutor').sum())
        n_sub=int(sum((r=='student') and bool(c.strip()) and not bool(AGREE_RE.match(c.strip())) for r,c in zip(roles,cont)))
        n_questions=int(sum((r=='tutor') and bool(QUESTION_RE.search(c)) for r,c in zip(roles,cont)))
        # Greedy tutor-question -> next student answer episode count, independent of labels.
        eps=0
        for i,(r,c) in enumerate(zip(roles,cont)):
            if r!='tutor' or not QUESTION_RE.search(c): continue
            for j in range(i+1,min(len(d),i+5)):
                if roles.iloc[j]=='student' and cont.iloc[j].strip(): eps+=1; break
                if roles.iloc[j]=='tutor' and QUESTION_RE.search(cont.iloc[j]) and j>i+1: break
        nr=len(g); rid=[str(x) for x in g.response_id]
        id_prefix_matches += sum(str(sid) in x for x in rid)
        dg=[digits(x) for x in rid]; id_digit_rows += sum(v is not None for v in dg)
        dg2=[v for v in dg if v is not None]
        session_rows.append({'session_id':str(sid),'feature_rows':nr,'utterances':n_all,'student_turns':n_student,'substantive_student_turns':n_sub,'tutor_questions':n_questions,'episodes':eps,
                             'eq_student':nr==n_student,'eq_substantive':nr==n_sub,'eq_questions':nr==n_questions,'eq_episodes':nr==eps,
                             'response_digits_unique':len(dg2)==len(set(dg2)) if dg2 else False,
                             'response_digits_contiguous':bool(dg2) and sorted(dg2)==list(range(min(dg2),max(dg2)+1))})
    s=pd.DataFrame(session_rows)
    n_sessions=len(s); total_rows=len(f)
    weighted=lambda col: float(s.loc[s[col],'feature_rows'].sum()/total_rows) if n_sessions else 0.0
    exact={k:{'sessions':int(s[k].sum()),'session_fraction':float(s[k].mean()),'row_fraction':weighted(k)} for k in ['eq_student','eq_substantive','eq_questions','eq_episodes']}
    # If counts identify a single natural transcript object in almost all rows, ordinal alignment is structurally available; otherwise not.
    best_name=max(exact,key=lambda k: exact[k]['row_fraction'])
    best=exact[best_name]
    objective_mult=f.groupby(['session_id','learning_objective_id']).size()
    per_session_obj=f.groupby('session_id').learning_objective_id.nunique()
    summary={
      'protocol':'V164_ENDPOINT_ALIGNMENT_CENSUS', 'rows':total_rows,'sessions':int(f.session_id.nunique()),'objectives':int(f.learning_objective_id.nunique()),
      'missing_transcript_sessions':len(missing),'transcript_header_variants':[{ 'columns':list(k),'sessions':v} for k,v in transcript_headers.items()],
      'response_id':{'contains_session_id_fraction':id_prefix_matches/total_rows,'has_numeric_component_fraction':id_digit_rows/total_rows},
      'session_count_correspondence':exact,'best_count_correspondence':{'candidate':best_name,**best},
      'within_session':{'median_feature_rows':float(np.median(list(sess_counts.values()))),'median_objectives':float(per_session_obj.median()),'median_rows_per_session_objective':float(objective_mult.median()),'max_rows_per_session_objective':int(objective_mult.max())},
      'digit_structure':{'sessions_unique_numeric_ids':int(s.response_digits_unique.sum()),'sessions_contiguous_numeric_ids':int(s.response_digits_contiguous.sum())},
    }
    if best['row_fraction']>=.95:
        decision='ORDINAL_ALIGNMENT_STRUCTURALLY_AVAILABLE'
        residual='A natural transcript event family has >=95% row-count correspondence; next test must validate ordinal direction/offset without labels.'
    elif best['row_fraction']>=.75:
        decision='PARTIAL_ORDINAL_PORTAL'
        residual='Strong but incomplete count correspondence; characterize exceptional sessions before any endpoint model.'
    else:
        decision='NO_LAWFUL_ENDPOINT_ALIGNMENT_FROM_AVAILABLE_COLUMNS'
        residual='response_id/session/objective plus transcript utterance metadata do not expose a defensible row-to-event alignment; endpoint-local state is unavailable without another observable.'
    summary['decision']=decision; summary['residual']=residual
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(summary,indent=2)); print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--features',type=Path,required=True); p.add_argument('--labels',type=Path,required=True); p.add_argument('--transcripts',type=Path,required=True); p.add_argument('--out',type=Path,required=True); main(p.parse_args())
