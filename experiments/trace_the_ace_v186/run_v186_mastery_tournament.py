#!/usr/bin/env python3
import json, sys
from itertools import combinations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.cluster import KMeans

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'trace_the_ace_v183'))
import run_v183_mastery_geometry as v183

OUT=Path('/workspace/trace-ace-results/v186'); OUT.mkdir(parents=True,exist_ok=True)
EPS=1e-6; NTRAIN=9000; NDEV=600; NCHAMP=1000; TAGS=['V186_DEV_A','V186_DEV_B','V186_DEV_C']

def metric(y,p):
    p=np.clip(p,EPS,1-EPS)
    return {'logloss':float(log_loss(y,p)),'auc':float(roc_auc_score(y,p))}

def take(df,n,tag,forbidden):
    z=df[~df.session_id.isin(forbidden)]; s=v183.session_sample(z,n,tag); return set(s)

def session_proxy(frame,ptext,pprior):
    r=v183.logit(ptext)-v183.logit(pprior); mean=np.zeros(len(frame)); med=np.zeros(len(frame)); n=np.zeros(len(frame))
    groups={}
    for i,s in enumerate(frame.session_id.astype(str)): groups.setdefault(s,[]).append(i)
    for inds in groups.values():
        for i in inds:
            vals=[r[j] for j in inds if j!=i]
            if vals: mean[i]=float(np.mean(vals)); med[i]=float(np.median(vals)); n[i]=len(vals)
    return mean,med,n

def graph_variants(frame,ptext,pprior,oi,W):
    directed,sup=v183.propagated_signal(frame,ptext,oi,W)
    sym=(W+W.T)/2.0
    symmetric,ssup=v183.propagated_signal(frame,ptext,oi,sym)
    W2=W@W; W2=np.clip(W2,-1.5,1.5)
    second,sup2=v183.propagated_signal(frame,ptext,oi,W2)
    pos=np.maximum(W,0); neg=np.minimum(W,0)
    ps,psup=v183.propagated_signal(frame,ptext,oi,pos); ns,nsup=v183.propagated_signal(frame,ptext,oi,neg)
    # Low-rank objective geometry: reconstruct W with rank <= 8, then propagate.
    try:
        U,S,Vt=np.linalg.svd(W,full_matrices=False); k=min(8,len(S)); low=(U[:,:k]*S[:k])@Vt[:k,:]
    except Exception: low=W
    low=np.clip(low,-1.5,1.5); lows,lowsup=v183.propagated_signal(frame,ptext,oi,low)
    return directed,sup,symmetric,ssup,second,sup2,ps,psup,ns,nsup,lows,lowsup

def make_modules(frame,ptext,pprior,pcnt,oi,W):
    d,ds,sy,sys,s2,s2s,po,pos,ne,nes,lo,los=graph_variants(frame,ptext,pprior,oi,W)
    sm,smed,sn=session_proxy(frame,ptext,pprior)
    lsup=np.log1p(pcnt); inv_unc=1/np.sqrt(pcnt+2.0)
    mods={
      'directed':np.column_stack([d,np.tanh(d),np.log1p(ds),d*np.log1p(ds)]),
      'symmetric':np.column_stack([sy,np.tanh(sy),np.log1p(sys)]),
      'lowrank':np.column_stack([lo,np.tanh(lo),np.log1p(los)]),
      'second_order':np.column_stack([s2,np.tanh(s2),np.log1p(s2s)]),
      'signed':np.column_stack([po,ne,np.log1p(pos),np.log1p(nes)]),
      'session_ability':np.column_stack([sm,smed,np.log1p(sn)]),
      'uncertainty':np.column_stack([inv_unc,lsup,inv_unc*(v183.logit(ptext)-v183.logit(pprior))]),
      'support_gate':np.column_stack([d/(1+inv_unc),d*lsup,sm*lsup]),
      'factor_interact':np.column_stack([lo*sm,lo*v183.logit(ptext),lo*v183.logit(pprior)]),
      'graph_ability':np.column_stack([d*sm,sy*sm,s2*sm,d*smed])
    }
    return mods

def base_features(ptext,pprior,pcnt):
    lt=v183.logit(ptext); lp=v183.logit(pprior); s=np.log1p(pcnt)
    return np.column_stack([lt,lp,s,lt*s,lp*s])

def eval_candidate(cols_train,cols_eval,ytr,yeval,C=.1):
    m=LogisticRegression(C=C,solver='liblinear',max_iter=240).fit(cols_train,ytr)
    p=m.predict_proba(cols_eval)[:,1]
    return p,metric(yeval,p)

def main():
    X=pd.read_csv(v183.FEAT); Y=pd.read_csv(v183.LAB)
    print('FEATURE_HEADERS',list(X.columns)); print('LABEL_HEADERS',list(Y.columns))
    target='is_correct' if 'is_correct' in Y.columns else 'correct'; Y=Y.rename(columns={target:'is_correct'})
    df=X.merge(Y,on='response_id',validate='one_to_one')
    used=set(); devs=[]
    for tag in TAGS:
        s=take(df,NDEV,tag,used); used|=s; devs.append(df[df.session_id.isin(s)].copy().reset_index(drop=True))
    cs=take(df,NCHAMP,'V186_CHAMP',used); used|=cs; champ=df[df.session_id.isin(cs)].copy().reset_index(drop=True)
    pool=df[~df.session_id.isin(used)].copy(); ts=take(pool,NTRAIN,'V186_TRAIN',set()); train=pool[pool.session_id.isin(ts)].copy().reset_index(drop=True)
    print('TRAIN_ROWS',len(train),'DEV_ROWS',[len(x) for x in devs],'CHAMP_ROWS',len(champ))
    eval_all=pd.concat(devs+[champ],ignore_index=True); work=pd.concat([train,eval_all],ignore_index=True); ntr=len(train)
    cache={}; texts=[]; scal=[]
    for k,r in enumerate(work.itertuples(index=False)):
        t,s=v183.build_row(str(r.session_id),str(r.learning_objective),cache); texts.append(t); scal.append(s)
        if (k+1)%1000==0: print('FEATURE_ROWS',k+1)
    scal=np.vstack(scal); mu=scal[:ntr].mean(0); sd=scal[:ntr].std(0); sd[sd<1e-8]=1; scal=(scal-mu)/sd
    vec=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.995,sublinear_tf=True,max_features=35000,strip_accents='unicode')
    Xt=vec.fit_transform(texts[:ntr]); Xe=vec.transform(texts[ntr:]); Ftr=hstack([Xt,csr_matrix(scal[:ntr])],format='csr'); Fe=hstack([Xe,csr_matrix(scal[ntr:])],format='csr')
    y=train.is_correct.to_numpy(int); groups=train.session_id.astype(str).to_numpy(); gkf=GroupKFold(n_splits=4)
    oof=np.zeros(ntr); op=np.zeros(ntr); oc=np.zeros(ntr); mod_oof={k:None for k in ['directed','symmetric','lowrank','second_order','signed','session_ability','uncertainty','support_gate','factor_interact','graph_ability']}
    chunks={k:[] for k in mod_oof}
    for f,(a,b) in enumerate(gkf.split(np.zeros(ntr),y,groups)):
        m=LogisticRegression(C=.35,max_iter=180,solver='liblinear',random_state=20260827).fit(Ftr[a],y[a]); oof[b]=m.predict_proba(Ftr[b])[:,1]
        pa,_,_=v183.objective_prior(train.iloc[a],train.iloc[a],2.0); pb,cb,_=v183.objective_prior(train.iloc[a],train.iloc[b],2.0); op[b]=pb; oc[b]=cb
        objs,oi,W,cnt=v183.fit_graph(train.iloc[a].reset_index(drop=True),pa)
        mods=make_modules(train.iloc[b].reset_index(drop=True),oof[b],pb,cb,oi,W)
        for k,v in mods.items(): chunks[k].append((b,v))
        print('FOLD',f,'ROWS',len(b),'EDGES',int((cnt>0).sum()))
    for k,arr in chunks.items():
        width=arr[0][1].shape[1]; M=np.zeros((ntr,width))
        for idx,v in arr: M[idx]=v
        mod_oof[k]=M
    # Final base and graph for dev/champ.
    fm=LogisticRegression(C=.35,max_iter=180,solver='liblinear',random_state=20260827).fit(Ftr,y); pe=fm.predict_proba(Fe)[:,1]
    pp,cc,_=v183.objective_prior(train,eval_all,2.0); ptrain,_,_=v183.objective_prior(train,train,2.0); objs,oi,W,cnt=v183.fit_graph(train,ptrain)
    mod_eval=make_modules(eval_all,pe,pp,cc,oi,W)
    A=base_features(oof,op,oc); B=base_features(pe,pp,cc)
    names=list(mod_oof)
    # Frozen dev slices; championship is never touched during candidate selection.
    offs=[]; q=0
    for d in devs: offs.append((q,q+len(d))); q+=len(d)
    champ_start=q
    ydev=np.concatenate([d.is_correct.to_numpy(int) for d in devs]); ychamp=champ.is_correct.to_numpy(int)
    Bdev=B[:champ_start]; Bchamp=B[champ_start:];
    base_model=LogisticRegression(C=.25,solver='liblinear',max_iter=200).fit(A,y); pbase=base_model.predict_proba(Bdev)[:,1]; base_m=metric(ydev,pbase)

    def score_combo(combo,include_champ=False):
        Tr=np.column_stack([A]+[mod_oof[k] for k in combo]); Ev=np.column_stack([Bdev]+[mod_eval[k][:champ_start] for k in combo])
        p,m=eval_candidate(Tr,Ev,y,ydev,.1)
        split=[]; pos=0
        for d in devs:
            n=len(d); mm=metric(d.is_correct.to_numpy(int),p[pos:pos+n]); bm=metric(d.is_correct.to_numpy(int),pbase[pos:pos+n]); split.append(mm['logloss']-bm['logloss']); pos+=n
        worst=max(split); rank=m['logloss']+0.25*max(0,worst)
        return {'combo':list(combo),'logloss':m['logloss'],'auc':m['auc'],'delta':m['logloss']-base_m['logloss'],'split_deltas':split,'rank_score':rank}

    # Round 1: all singletons and pairs.
    r1=[score_combo(c) for z in [1,2] for c in combinations(names,z)]; r1.sort(key=lambda r:r['rank_score']); beam=[tuple(r['combo']) for r in r1[:8]]
    rounds=[{'round':1,'tested':len(r1),'top':r1[:12]}]
    seen={tuple(sorted(r['combo'])) for r in r1}
    # Beam expansion up to size 6, keep 8 each round.
    for rr in range(2,6):
        cand=set()
        for c in beam:
            for n in names:
                z=tuple(sorted(set(c+(n,))))
                if len(z)==len(c)+1 and z not in seen: cand.add(z)
        if not cand: break
        vals=[score_combo(c) for c in cand]; vals.sort(key=lambda r:r['rank_score']); beam=[tuple(r['combo']) for r in vals[:8]]; seen|=cand
        rounds.append({'round':rr,'tested':len(vals),'top':vals[:12]})
    finalists=sorted([score_combo(c) for c in beam],key=lambda r:r['rank_score'])[:3]
    # Untouched championship judge: only finalists.
    champs=[]
    for r in finalists:
        c=tuple(r['combo']); Tr=np.column_stack([A]+[mod_oof[k] for k in c]); Ec=np.column_stack([Bchamp]+[mod_eval[k][champ_start:] for k in c])
        p,m=eval_candidate(Tr,Ec,y,ychamp,.1); pb=base_model.predict_proba(Bchamp)[:,1]; bm=metric(ychamp,pb)
        champs.append({'combo':list(c),'metric':m,'base':bm,'delta_logloss':m['logloss']-bm['logloss'],'delta_auc':m['auc']-bm['auc']})
    champs.sort(key=lambda r:r['metric']['logloss']); winner=champs[0]
    decision='TOURNAMENT_WINNER__PROMOTE' if winner['delta_logloss']<=-0.002 else ('SMALL_WIN__USE_V184' if winner['delta_logloss']<0 else 'NO_WIN__V184_REMAINS')
    result={'protocol':'V186_FAST_MASTERY_MODULE_TOURNAMENT','train_rows':len(train),'dev_rows':len(ydev),'champ_rows':len(ychamp),'modules':names,'dev_base':base_m,'rounds':rounds,'finalists':finalists,'championship':champs,'winner':winner,'decision':decision}
    (OUT/'v186_results.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))

if __name__=='__main__': main()
