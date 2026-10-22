#!/usr/bin/env python3
"""Deterministic multi-turn one-column visual compass; synthetic ONLY.

Observe one 64-row column at each instant from a world-fixed textured
cylindrical panorama. The true angle is never passed to estimator. The
gyro has fixed bias and noise. A causal grid-search landmark likelihood
compares each sample against a frozen 1-turn reference map. A conventional
matched-filter estimate is the explicit comparator; no novelty claim.
"""
import argparse,json,time
import numpy as np
p=argparse.ArgumentParser()
p.add_argument("--output",default="multiturn.json")
p.add_argument("--seed",type=int,default=27)
p.add_argument("--turns",type=int,default=12)
p.add_argument("--dropout-start",type=int,default=2600)
p.add_argument("--dropout-end",type=int,default=3400)
a=p.parse_args()
t0=time.perf_counter();rng=np.random.default_rng(a.seed)
bins=256;rows=64;per_turn=360
# Synthetic textured scene, with periodic confuser introduced deliberately.
base=rng.normal(0,1,(bins,rows))
for _ in range(3):base=(np.roll(base,1,axis=0)+2*base+np.roll(base,-1,axis=0))/4
base=base/np.linalg.norm(base,axis=1)[:,None]
# 12 revolutions, variable speed, and a slowly changing scene.
n=a.turns*per_turn;dt=.01
speed=2*np.pi/(per_turn*dt)*(1+.15*np.sin(np.arange(n)*.004))
true=np.cumsum(speed*dt);true-=true[0]
measure=true/(2*np.pi)*bins
# Each output is precisely one detector column per timestamp.
sample=lambda angle: base[np.mod(np.rint(angle/(2*np.pi)*bins).astype(int),bins)]
observations=sample(true)+rng.normal(0,.08,(n,rows))
gyro_delta=np.diff(true,prepend=true[0])+.014*dt+rng.normal(0,.002*dt,n)
est=np.cumsum(gyro_delta)
# Construct a frozen map ONLY from samples observed in the first
# gyro-estimated revolution. No hidden scene values, true orientations,
# or future observations enter the reference. Unobserved bins stay empty.
map_sum=np.zeros((bins,rows));map_count=np.zeros(bins,dtype=int)
training_end=next((i for i,x in enumerate(est) if x>=2*np.pi),n)
if training_end>=n:raise ValueError("No completed initial gyro revolution")
for i in range(training_end):
 b=int(round(est[i]/(2*np.pi)*bins))%bins
 map_sum[b]+=observations[i]
 map_count[b]+=1
reference=np.zeros_like(map_sum)
occupied=map_count>0
reference[occupied]=map_sum[occupied]/map_count[occupied,None]
reference[occupied]-=reference[occupied].mean(axis=1,keepdims=True)
reference[occupied]/=np.maximum(np.linalg.norm(reference[occupied],axis=1,keepdims=True),1e-12)
def run(use_vision):
 heading=0.;accepted=0;wrong=0;errs=[];reacq=None
 for i in range(n):
  heading+=gyro_delta[i]
  if use_vision and i>=training_end and not(a.dropout_start<=i<a.dropout_end):
   z=observations[i];pred=int(round(heading/(2*np.pi)*bins))
   idx=(np.arange(pred-10,pred+11)%bins).astype(int)
   idx=idx[occupied[idx]]
   if len(idx)<2:
    errs.append(heading-true[i]);continue
   quality=reference[idx]@z
   order=np.argsort(quality)
   top=order[-1];second=order[-2]
   if quality[top]>=.63 and quality[top]-quality[second]>=.005:
    innovation=((idx[top]-pred+bins//2)%bins-bins//2)*2*np.pi/bins
    heading+=.30*innovation
    accepted+=1
    if abs(((heading-true[i]+np.pi)%(2*np.pi))-np.pi)>np.deg2rad(10):wrong+=1
    if i>=a.dropout_end and reacq is None:reacq=i
  errs.append(heading-true[i])
 e=np.array(errs)
 return {"rmse_deg":float(np.rad2deg(np.sqrt(np.mean(e**2)))),"end_error_deg":float(np.rad2deg(e[-1])),"max_error_deg":float(np.max(np.abs(np.rad2deg(e)))),"accepted":accepted,"unsafe_gt_gt10deg_after_correction":wrong,"first_post_blackout_accepted":reacq}
fixed=run(False);visual=run(True)
result=dict(kind="SYNTHETIC_FIRST_REVOLUTION_LEARNED_MAP",seed=a.seed,turns=a.turns,training_end_index=training_end,observed_map_bins=int(occupied.sum()),map_coverage=float(occupied.mean()),
  samples=n,samples_per_turn=per_turn,pixels_per_observation=rows,panorama_bins=bins,
  dropout=[a.dropout_start,a.dropout_end],gyro_only=fixed,visual_learned_map=visual,
  processing_seconds=time.perf_counter()-t0,
  limitation="Reference learned causally from one-column observations over first gyro-estimated revolution; scene synthesis still idealized. No real camera motion distortion or independent physical measurement; ordinary matched-filter baseline, not a novel MathGraph advantage.")
open(a.output,"w").write(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
