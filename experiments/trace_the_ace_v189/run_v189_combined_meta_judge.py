#!/usr/bin/env python3
"""Combine the disjoint V187 and V188 predictions into one session-clustered judge."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, roc_auc_score

OUT=Path('/workspace/trace-ace-results/v189'); OUT.mkdir(parents=True,exist_ok=True)
P187=Path('/workspace/trace-ace-results/v187/v187_predictions.csv')
P188=Path('/workspace/trace-ace-results/v188/v188_predictions.csv')
FEAT=Path('/workspace/trace_the_ace/train_features_TMQTWsB.csv')
EPS=1e-6

def metrics(y,p):
 p=np.clip(np.asarray(p,float),EPS,1-EPS)
 return {'logloss':float(log_loss(y,p)),'auc':float(roc_auc_score(y,p))}

def main():
 a=pd.read_csv(P187); b=pd.read_csv(P188); f=pd.read_csv(FEAT,usecols=['response_id','session_id'])
 print('V187_HEADERS',list(a.columns)); print('V188_HEADERS',list(b.columns)); print('FEATURE_HEADERS',list(f.columns))
 a=a.merge(f,on='response_id',how='left',validate='one_to_one')
 a=a[['response_id','session_id','y','v184_directed','minimal_session_ability']].rename(
  columns={'v184_directed':'pbase','minimal_session_ability':'pcand'})
 b=b[['response_id','session_id','y','p_v184','p_v184_session_ability']].rename(
  columns={'p_v184':'pbase','p_v184_session_ability':'pcand'})
 a['source']='V187'; b['source']='V188'; z=pd.concat([a,b],ignore_index=True)
 if z.session_id.isna().any(): raise RuntimeError('missing session join')
 if z.response_id.duplicated().any(): raise RuntimeError('holdouts are not disjoint')
 y=z.y.to_numpy(int); pb=z.pbase.to_numpy(float); pc=z.pcand.to_numpy(float)
 groups={}
 for i,s in enumerate(z.session_id.astype(str)): groups.setdefault(s,[]).append(i)
 keys=list(groups); rng=np.random.default_rng(20260827); ds=[]
 for _ in range(5000):
  chosen=rng.choice(keys,size=len(keys),replace=True)
  idx=np.concatenate([groups[s] for s in chosen])
  ds.append(log_loss(y[idx],np.clip(pc[idx],EPS,1-EPS))-log_loss(y[idx],np.clip(pb[idx],EPS,1-EPS)))
 ds=np.asarray(ds)
 sources={}
 for name,g in z.groupby('source'):
  yy=g.y.to_numpy(int); p0=g.pbase.to_numpy(float); p1=g.pcand.to_numpy(float)
  sources[name]={'rows':len(g),'baseline':metrics(yy,p0),'candidate':metrics(yy,p1),
   'delta_logloss':metrics(yy,p1)['logloss']-metrics(yy,p0)['logloss']}
 bm=metrics(y,pb); cm=metrics(y,pc)
 result={'protocol':'V189_COMBINED_DISJOINT_INCREMENTAL_META_JUDGE','rows':len(z),'sessions':len(keys),
  'sources':sources,'baseline':bm,'candidate':cm,'delta_logloss':cm['logloss']-bm['logloss'],
  'delta_auc':cm['auc']-bm['auc'],'clustered_bootstrap':{'repetitions':5000,'mean':float(ds.mean()),
  'lower_95':float(np.quantile(ds,.025)),'upper_95':float(np.quantile(ds,.975)),
  'probability_better':float(np.mean(ds<0))}}
 result['decision']='INTEGRATE_SESSION_ABILITY' if result['delta_logloss']<=-.001 and result['clustered_bootstrap']['probability_better']>=.8 else 'KEEP_V184'
 (OUT/'v189_results.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))

if __name__=='__main__': main()
