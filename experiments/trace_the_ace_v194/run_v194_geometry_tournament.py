#!/usr/bin/env python3
import json,pickle,sys,warnings
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss,roc_auc_score
warnings.filterwarnings('ignore')
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments'/'trace_the_ace_v193'))
import run_v193_strict_public_proxy as p
v=p.v
WS=Path('/workspace'); FEAT=WS/'trace_the_ace/train_features_TMQTWsB.csv'; LAB=WS/'trace_the_ace/train_labels_44ujmj2.csv'; CACHE=WS/'trace-ace-work/v185/feature_cache.pkl'; OUT=WS/'trace-ace-results/v194'

def M(y,q): return {'logloss':float(log_loss(y,q)),'auc':float(roc_auc_score(y,q))}
def add_geom(A,objs,vocab,channels,family):
    mp={o:j for j,o in enumerate(vocab)}; n=len(objs); k=len(vocab)
    oh=np.zeros((n,k),np.float32)
    for i,o in enumerate(objs):
        j=mp.get(str(o))
        if j is not None: oh[i,j]=1.
    feats=[A,oh]
    for name in family:
        z=p.L(channels[name]).astype(np.float32)
        feats.append(oh*z[:,None])
    return np.column_stack(feats)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    X=pd.read_csv(FEAT); Y=pd.read_csv(LAB); target='is_correct' if 'is_correct' in Y.columns else 'correct'; Y=Y.rename(columns={target:'is_correct'})
    df=X.merge(Y,on='response_id',validate='one_to_one').reset_index(drop=True); y=df.is_correct.to_numpy(int); groups=df.session_id.astype(str).to_numpy()
    co=pickle.loads(CACHE.read_bytes()); texts=[co['texts'][str(r)] for r in df.response_id]; scal=np.vstack([co['scalars'][str(r)] for r in df.response_id]).astype(float)
    tc={}; sess=df.session_id.astype(str).drop_duplicates().tolist(); frames={s:v.transcript_frame(s,tc) for s in sess}
    alltxt=[v.role_text(frames[s]) for s in groups]; stutxt=[v.role_text(frames[s],'student') for s in groups]; tutt=[v.role_text(frames[s],'tutor') for s in groups]
    osv=np.vstack([v.outcome_scalars(frames[str(r.session_id)],str(r.learning_objective)) for r in df.itertuples(index=False)])
    uniq=np.array(sorted(set(groups)))
    families={
      'sess':('session',),
      'sess_target':('session','target'),
      'sess_student':('session','student'),
      'sess_tutor':('session','tutor'),
      'sess_prior':('session','prior'),
      'sess_target_student':('session','target','student'),
      'sess_student_tutor':('session','student','tutor'),
      'sess_target_student_tutor':('session','target','student','tutor'),
      'sess_target_prior':('session','target','prior'),
      'sess_all':('session','target','student','tutor','prior'),
    }
    Cs=[.003,.005,.008,.01,.015,.02,.03,.05,.08,.1,.15]
    rows=[]
    for seed in [19201,19202,19203]:
        rng=np.random.default_rng(seed); u=uniq.copy(); rng.shuffle(u); nb=int(.60*len(u)); nc=int(.20*len(u)); sb=set(u[:nb]); sc=set(u[nb:nb+nc]); st=set(u[nb+nc:])
        b=np.array([i for i,g in enumerate(groups) if g in sb]); c=np.array([i for i,g in enumerate(groups) if g in sc]); t=np.array([i for i,g in enumerate(groups) if g in st])
        ptc,ptt=p.fit_text(texts,scal,y,b,c,t,.35,35000); psc,pst=p.fit_plain(alltxt,y,b,c,t,.20,26000); puc,put=p.fit_plain(stutxt,y,b,c,t,.15,22000); pvc,pvt=p.fit_plain(tutt,y,b,c,t,.10,18000)
        ppc,ccc,_=v.objective_prior(df.iloc[b],df.iloc[c],2.0); ppt,cct,_=v.objective_prior(df.iloc[b],df.iloc[t],2.0)
        om=osv[b].mean(0); od=osv[b].std(0); od[od<1e-8]=1; osc=(osv[c]-om)/od; ost=(osv[t]-om)/od
        Ac=p.full(ptc,psc,puc,pvc,ppc,ccc,osc); At=p.full(ptt,pst,put,pvt,ppt,cct,ost)
        vocab=sorted(set(df.iloc[b].learning_objective.astype(str)))
        objc=df.iloc[c].learning_objective.astype(str).tolist(); objt=df.iloc[t].learning_objective.astype(str).tolist()
        ccx={'session':psc,'target':ptc,'student':puc,'tutor':pvc,'prior':ppc}; ttx={'session':pst,'target':ptt,'student':put,'tutor':pvt,'prior':ppt}
        candidates=[]
        for fname,fam in families.items():
            Gc=add_geom(Ac,objc,vocab,ccx,fam); Gt=add_geom(At,objt,vocab,ttx,fam)
            for C in Cs:
                mod=LogisticRegression(C=C,solver='liblinear',max_iter=400).fit(Gc,y[c])
                qc=mod.predict_proba(Gc)[:,1]; qt=mod.predict_proba(Gt)[:,1]
                candidates.append({'family':fname,'C':C,'cal':M(y[c],qc),'test':M(y[t],qt)})
        candidates.sort(key=lambda r:r['cal']['logloss'])
        best=candidates[0]
        # fixed V193 reference = session-only, C=.1
        Gc=add_geom(Ac,objc,vocab,ccx,('session',)); Gt=add_geom(At,objt,vocab,ttx,('session',))
        q193=LogisticRegression(C=.1,solver='liblinear',max_iter=400).fit(Gc,y[c]).predict_proba(Gt)[:,1]; m193=M(y[t],q193)
        rows.append({'seed':seed,'v193':m193,'winner_family':best['family'],'winner_C':best['C'],'winner_cal':best['cal'],'winner_test':best['test'],'delta_vs_v193':best['test']['logloss']-m193['logloss'],'top_cal':[{'family':r['family'],'C':r['C'],'cal_logloss':r['cal']['logloss'],'test_logloss':r['test']['logloss']} for r in candidates[:8]]})
        print(json.dumps(rows[-1]))
    mean=float(np.mean([r['delta_vs_v193'] for r in rows])); wins=sum(r['delta_vs_v193']<0 for r in rows)
    # Also identify fixed family/C by average untouched test performance, to avoid per-seed selection optimism.
    fixed=[]
    # recover from top-level rerun results is expensive; record selected-family evidence and conservative decision only.
    res={'protocol':'V194_STRICT_OBJECTIVE_GEOMETRY_TOURNAMENT','rows':rows,'mean_delta_vs_v193':mean,'wins_vs_v193':wins,'decision':'V194_PROMOTE' if wins==3 and mean<=-.0004 else 'KEEP_V193'}
    (OUT/'v194_results.json').write_text(json.dumps(res,indent=2)); print(json.dumps(res,indent=2))
if __name__=='__main__': main()
