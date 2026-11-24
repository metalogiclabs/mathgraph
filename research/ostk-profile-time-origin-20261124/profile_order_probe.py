"""Permutation invariance and analytic affine-state contract for Tabulated profiles."""
import os
os.environ['OSTK_PHYSICS_ENVIRONMENT_EPHEMERIS_SPICE_ENGINE_MODE']='Manual'
import itertools,json,csv,math
from pathlib import Path
import numpy as np
from ostk.physics.time import Instant,Duration
from ostk.physics.coordinate import Frame,Position,Velocity
from ostk.mathematics.geometry.d3.transformation.rotation import Quaternion
from ostk.mathematics.curve_fitting import Interpolator
from ostk.astrodynamics.trajectory import State
from ostk.astrodynamics.trajectory.state.coordinate_subset import CartesianPosition,CartesianVelocity,AngularVelocity
from ostk.astrodynamics.flight.profile.model import Tabulated

def h(a,b):
 w,x,y,z=a;v,i,j,k=b
 return np.array([w*v-x*i-y*j-z*k,w*i+x*v+y*k-z*j,w*j-x*k+y*v+z*i,w*k+x*j-y*i+z*v])
def q_at(t):
 w=np.array([.001,.002,-.003]);n=np.linalg.norm(w)
 return h(np.array([math.sqrt(.86),.2,.3,-.1]),np.r_[math.cos(n*t/2),w*math.sin(n*t/2)/n])
def matrix(q):
 w,x,y,z=q
 return np.array([[w*w+x*x-y*y-z*z,2*(x*y+z*w),2*(x*z-y*w)],
 [2*(x*y-z*w),w*w-x*x+y*y-z*z,2*(y*z+x*w)],
 [2*(x*z+y*w),2*(y*z-x*w),w*w-x*x-y*y+z*z]])
root=Frame.GCRF();epoch=Instant.J2000();p0=np.array([100.,-200.,300.]);v=np.array([7.,-11.,13.]);w=np.array([.001,.002,-.003])
times=[0,10,20,30];states=[]
for t in times:
 q=q_at(t)
 states.append(State(epoch+Duration.seconds(t),Position.meters(p0+t*v,root),Velocity.meters_per_second(v,root),
                     Quaternion(np.r_[q[1:],q[0]],Quaternion.Format.XYZS),w,root))
rows=[];types=[Interpolator.Type.Linear,Interpolator.Type.BarycentricRational]
for order in itertools.permutations(range(4)):
 for mode in ['uniform','per-subset','default']:
  for interp in (types if mode!='default' else [Interpolator.Type.BarycentricRational]):
   ordered=[states[i] for i in order]
   if os.environ.get('OSTK_CANONICALIZE_INPUT')=='1':ordered=sorted(ordered,key=lambda s:s.get_instant())
   if mode=='uniform':model=Tabulated(ordered,interp)
   elif mode=='default':model=Tabulated.default(ordered)
   else:model=Tabulated(ordered,{CartesianPosition.default():interp,CartesianVelocity.default():interp,AngularVelocity.default():interp})
   for t in [0,5,10,15,20,25,30]:
    s=model.calculate_state_at(epoch+Duration.seconds(t));p=np.array(s.get_position().get_coordinates())
    qq=s.get_attitude().to_vector(Quaternion.Format.XYZS);qm=matrix(np.r_[qq[3],qq[:3]])
    rows.append(dict(order='-'.join(map(str,order)),first=order[0],mode=mode,interpolator=str(interp),query=t,
       expected_x=float((p0+t*v)[0]),actual_x=float(p[0]),position_error=float(np.linalg.norm(p-(p0+t*v))),
       velocity_error=float(np.linalg.norm(s.get_velocity().get_coordinates()-v)),
       rate_error=float(np.linalg.norm(s.get_angular_velocity()-w)),
       attitude_matrix_error=float(np.max(np.abs(qm-matrix(q_at(t))))),
       timestamp_error=float((s.get_instant()-(epoch+Duration.seconds(t))).in_seconds())))
out=Path('ostk-evidence');out.mkdir(exist_ok=True);name='profile-order-canonicalized' if os.environ.get('OSTK_CANONICALIZE_INPUT')=='1' else 'profile-order-wheel'
with (out/(name+'.csv')).open('w') as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
summary={'cases':len(rows),'position_discrepancies':sum(r['position_error']>1e-7 for r in rows),
 'per_first':{i:{'cases':sum(r['first']==i for r in rows),'position_discrepancies':sum(r['first']==i and r['position_error']>1e-7 for r in rows)} for i in range(4)},
 'max_errors':{k:max(r[k] for r in rows) for k in ['position_error','velocity_error','rate_error','attitude_matrix_error','timestamp_error']}}
(out/(name+'.json')).write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)
