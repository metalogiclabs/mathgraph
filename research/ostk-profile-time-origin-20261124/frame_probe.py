"""Independent body/reference frame oracle; synthetic TT times, no Earth model."""
import os
os.environ['OSTK_PHYSICS_ENVIRONMENT_EPHEMERIS_SPICE_ENGINE_MODE']='Manual'
import csv,json,math
from pathlib import Path
import numpy as np
from ostk.mathematics.geometry.d3.transformation.rotation import Quaternion
from ostk.physics.time import Instant,Duration
from ostk.physics.coordinate import Frame,Transform
from ostk.physics.coordinate.frame.provider import Dynamic
from ostk.astrodynamics.trajectory import State
from ostk.astrodynamics.trajectory.state import CoordinateBroker
from ostk.astrodynamics.trajectory.state.coordinate_subset import AttitudeQuaternion,AngularVelocity

def h(a,b):
    w,x,y,z=a;v,i,j,k=b
    return np.array([w*v-x*i-y*j-z*k,w*i+x*v+y*k-z*j,w*j-x*k+y*v+z*i,w*k+x*j-y*i+z*v])
def conj(q):return q*np.array([1,-1,-1,-1])
def qaxis(v,t):
    n=np.linalg.norm(v)
    return np.r_[math.cos(n*t/2),v*math.sin(n*t/2)/n] if n else np.array([1.,0,0,0])
def qe(a):
    q=np.array([1.,0,0,0])
    for i,t in enumerate(a):
        v=np.eye(3)[i]
        q=h(q,np.r_[math.cos(t/2),v*math.sin(t/2)])
    return q
def matrix(q):
    w,x,y,z=q
    return np.array([[w*w+x*x-y*y-z*z,2*(x*y+z*w),2*(x*z-y*w)],
                     [2*(x*y-z*w),w*w-x*x+y*y-z*z,2*(y*z+x*w)],
                     [2*(x*z+y*w),2*(y*z-x*w),w*w-x*x-y*y+z*z]])
def native(q):return Quaternion(np.r_[q[1:],q[0]],Quaternion.Format.XYZS)
def from_native(q):
    v=np.asarray(q.to_vector(Quaternion.Format.XYZS))
    return np.r_[v[3],v[:3]]
epoch=Instant.J2000();root=Frame.GCRF();att=AttitudeQuaternion.default();spin=AngularVelocity.default();broker=CoordinateBroker([att,spin])
bodyqs=[qe(a) for a in [(0,0,0),(.4,0,0),(0,.7,0),(0,0,-.9),(.3,-.7,.9),(-.8,.5,-.4)]]
frames=[(qe(a),qe(b)) for a,b in [((0,0,0),(0,0,0)),((.2,0,0),(0,.5,0)),((.2,-.3,.4),(-.6,.1,.7)),((-.5,.9,.2),(.8,-.4,.6))]]
rates=[(np.array(a),np.array(b)) for a,b in [((0,0,0),(0,0,0)),((.1,0,0),(0,.2,0)),((.2,-.3,.4),(-.4,.1,.3)),((0,0,0),(.07,-.11,.13))]]
rows=[]
for fi,(a0,b0) in enumerate(frames):
 for wi,(wa,wb) in enumerate(rates):
    def build(q0,w,label):
        def provider(date):
            dt=(date-epoch).in_seconds();q=h(q0,qaxis(w,dt))
            return Transform.passive(date,np.zeros(3),np.zeros(3),native(q),w)
        return Frame.construct(label,False,root,Dynamic(provider))
    fa=build(a0,wa,'MathGraph_A_%s_%s'%(fi,wi));fb=build(b0,wb,'MathGraph_B_%s_%s'%(fi,wi))
    for bi,c0 in enumerate(bodyqs):
     wc=np.array([.17,-.23,.31])
     for dt in [-2.5,0,3.5]:
      for sign in [-1,1]:
        def input_at(t):
            qa=h(a0,qaxis(wa,t));qc=h(c0,qaxis(wc,t));qca=h(conj(qa),qc)*sign
            wca=wc-matrix(qca)@wa
            return np.r_[qca[1:],qca[0],wca]
        date=epoch+Duration.seconds(dt);data=input_at(dt)
        qb=h(b0,qaxis(wb,dt));qc=h(c0,qaxis(wc,dt));qcb=h(conj(qb),qc)
        expected_r=matrix(qcb);expected_w=wc-expected_r@wb
        got_q=att.in_frame(date,data,fa,fb,broker)
        got_r=matrix(np.r_[got_q[3],got_q[:3]])
        got_w=spin.in_frame(date,data,fa,fb,broker)
        state=State(date,data,fa,[att,spin]).in_frame(fb)
        state_r=matrix(from_native(state.get_attitude()));state_w=state.get_angular_velocity()
        step=1e-4;rdot=np.zeros((3,3))
        for k,factor in [(-2,1),(-1,-8),(1,8),(2,-1)]:
            t=dt+k*step;v=att.in_frame(epoch+Duration.seconds(t),input_at(t),fa,fb,broker)
            rdot+=factor*matrix(np.r_[v[3],v[:3]])/(12*step)
        skew=rdot@got_r.T
        numeric=np.array([skew[1,2]-skew[2,1],skew[2,0]-skew[0,2],skew[0,1]-skew[1,0]])/2
        rows.append(dict(frame=fi,rates=wi,body=bi,dt=dt,sign=sign,
          matrix_error=float(np.max(np.abs(got_r-expected_r))),rate_error=float(np.linalg.norm(got_w-expected_w)),
          state_matrix_error=float(np.max(np.abs(state_r-expected_r))),state_rate_error=float(np.linalg.norm(state_w-expected_w)),
          derivative_rate_error=float(np.linalg.norm(numeric-got_w))))
out=Path('ostk-evidence');out.mkdir(exist_ok=True)
with (out/'independent-frame-cases.csv').open('w') as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
limits={'matrix_error':3e-14,'rate_error':3e-13,'state_matrix_error':3e-14,'state_rate_error':3e-13,'derivative_rate_error':2e-8}
summary={'cases':len(rows),'discrepancies':sum(any(r[k]>v for k,v in limits.items()) for r in rows),
         'max_errors':{k:max(r[k] for r in rows) for k in limits},'tolerances':limits}
(out/'independent-frame-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2),flush=True)
