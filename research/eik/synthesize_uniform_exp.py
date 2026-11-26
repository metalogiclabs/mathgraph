"""Coupled residue synthesis for a complete, packed negative-exp cell family.

One word carries both the constant polynomial term and a signed cubic
coefficient. Fit proposals have no authority until exact integer replay over
every word of the cell establishes the guarded output relation.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import numpy as np
from hot_path_hints import BASE
from uniform_negative_exp import replace_family,LO,HI


def signed_residue(value):
    return (value+128)%256-128


def pack_interval(lower, upper, cubic, p_min, p_max):
    """Propose a constant and guard from an exhaustively established interval.

    `lower` and `upper` bound -256*Y-p and 255-256*Y-p respectively.
    They are assumptions supplied by cell enumeration, not fit estimates.
    """
    if not -(1 << 23) <= cubic < (1 << 23):
        return None
    difference = lower + (cubic-lower) % 256
    threshold = max(0, difference-upper-1)
    if threshold >= 255:
        return None
    packed = (threshold << 24) | (cubic & 0xffffff)
    base = (packed-difference) // 256
    if not (0 <= base < 2**32 and 0 <= packed+p_min <= packed+p_max < 2**32):
        return None
    return packed, base, threshold


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline',type=Path,required=True)
    ap.add_argument('--oracle',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--bits',type=int,default=17)
    ap.add_argument('--grid',choices=['uniform','mixed'],default='uniform')
    ap.add_argument('--proposal',choices=['rounded','analytic'],default='analytic')
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    source=a.baseline.read_text()
    if hashlib.sha256(source.encode()).hexdigest()!=BASE:raise ValueError('baseline')
    lib=C.CDLL(str(a.oracle.resolve()));oracle=lib.direct_exp_outputs
    oracle.argtypes=[C.c_uint32,C.c_uint32,C.POINTER(C.c_uint32)]
    groups=[(LO,HI,a.bits)] if a.grid=='uniform' else [(LO,0xbf800000,18),(0xbf800000,0xc0800000,17),(0xc0800000,HI,16)]
    cells=[]
    for low,high,k in groups:
        if low%(1<<k) or high%(1<<k):raise ValueError('complete cells')
        cells.extend((lo,k) for lo in range(low,high,1<<k))
    nodes=np.cos(np.pi*(np.arange(64)+.5)/64)
    nodes_u=(nodes+1)/2
    records=[];digest=hashlib.sha256()
    for cell,(lo,k) in enumerate(cells):
        n=1<<k
        u=np.arange(n,dtype=np.int64)<<(32-k)
        x=np.arange(n,dtype=np.float64)/n
        sample=np.unique(np.linspace(0,n-1,4097).astype(np.int64))
        y32=np.empty(n,dtype=np.uint32)
        oracle(lo,n,y32.ctypes.data_as(C.POINTER(C.c_uint32)))
        digest.update(y32.tobytes());y=y32.astype(np.int64)
        if a.proposal=='rounded':
            proposal=np.polynomial.polynomial.polyfit(x[sample],int(y[0])-y[sample],3)
        else:
            endpoints=np.array([lo,lo+n],dtype=np.uint32).view(np.float32).astype(np.float64)
            values=np.exp(endpoints[0]-(endpoints[0]-endpoints[1])*nodes_u)
            fraction,exponent=np.frexp(values)
            continuous=(exponent+125)*(1<<23)+fraction*(1<<24)
            cheb=np.polynomial.chebyshev.chebfit(nodes,int(y[0])-continuous,3)
            proposal=np.polynomial.Chebyshev(cheb,domain=[0,1]).convert(kind=np.polynomial.Polynomial).coef
        c1,c2,c3=np.rint(proposal[1:]*256).astype(np.int64).tolist()
        best=None;delta=0;seen=set()
        # The cubic's minimax compensation is lower degree; its residue map
        # is close to a contraction. Search is heuristic; replay is exact.
        for iteration in range(10):
            if delta in seen:break
            seen.add(delta)
            d3=c3+delta;d2=c2+int(np.rint(-1.5*delta));d1=c1+int(np.rint(9*delta/16))
            bounds=[d2+min(0,d3),d2+max(0,d3)]
            bounds += [d1+min(0,bounds[0]),d1+max(0,bounds[1])]
            if not (-(1<<23)<=d3<(1<<23)) or not all(-(1<<31)<=z<(1<<31) for z in [d1,d2,*bounds]):break
            p=(d3*u)>>32;p=((d2+p)*u)>>32;p=((d1+p)*u)>>32
            lower=int((-y*256-p).max())
            upper=int(((1-y)*256-1-p).min())
            result=pack_interval(lower,upper,d3,int(p.min()),int(p.max()))
            if result is not None:
                packed,base,threshold=result
                q=packed+p
                settled=((q.astype(np.uint64)<<24)&0xffffffff)>packed
                got=base-(q>>8)
                assert np.all(got[settled]==y[settled])
                r={'lo':lo,'hi':lo+n,'bits':k,'threshold':threshold,
                   'row':[packed,base,d1,d2], 'cubic':d3,
                   'p_min':int(p.min()),'p_max':int(p.max()),
                   'words_enumerated':n,'settled':int(settled.sum()),
                   'mismatches':0,'intermediate_bounds':bounds,'delta':delta}
                if best is None or (threshold,-r['settled'])<(best['threshold'],-best['settled']):best=r
            delta=signed_residue(lower-c3)
        records.append(best or {'lo':lo,'hi':lo+n,'bits':k,'threshold':999,'reason':'no admitted integer cell'})
        if (cell+1)%32==0:print('cells',cell+1,'admitted',sum(r['threshold']<32 for r in records),flush=True)
    journal={'baseline_sha256':BASE,'domain':[LO,HI],'groups':groups,'proposal':a.proposal,
             'oracle_output_sha256':digest.hexdigest(),'words_enumerated':HI-LO,
             'oracle_library_sha256':hashlib.sha256(a.oracle.read_bytes()).hexdigest(),
             'boundary':'Source-relative complete-cell synthesis; no all-input independent reference qualification',
             'cells':records}
    (a.out/'synthesis.json').write_text(json.dumps(journal,indent=2)+'\n')
    for cap in (8,16,32,64):
        active=[r for r in records if r['threshold']<=cap]
        narrow=all(-32768<=r['cubic']<32768 for r in active)
        table='union ue_word {uint32_t word;int16_t half[2];};\nstruct ue_row {union ue_word packed;uint32_t base;int32_t c1,c2;};\n'
        table+='static const struct ue_row ue_rows['+str(len(records))+']={\n'
        vals=[]
        for r in records:
            row=r['row'] if r['threshold']<=cap else [0xffffffff,0,0,0]
            if r['threshold']<=cap and narrow:
                packed=(r['threshold']<<24)|(r['cubic']&65535)
                base=row[1]+(packed-row[0])//256
                if not (0<=packed+r['p_min'] and packed+r['p_max']<2**32 and 0<=base<2**32):raise ValueError('narrow packed range')
                row=[packed,base,*row[2:]]
            vals.append('{{'+str(row[0])+'u},'+str(row[1])+'u,'+str(row[2])+','+str(row[3])+'}')
        table+=',\n'.join(vals)+'\n};\n'
        dispatch=''
        offset=0
        for gi,(low,high,k) in enumerate(groups):
            if len(groups)==1:
                dispatch='uint32_t ui=(r_w>>'+str(k)+')-'+str(low>>k)+'u,uu=r_w<<'+str(32-k)+';\n'
            else:
                prefix=('if' if gi==0 else 'else if')+'(r_w<'+hex(high)+'u)' if gi<len(groups)-1 else 'else'
                dispatch+=prefix+' {ui='+str(offset)+'u+(r_w>>'+str(k)+')-'+str(low>>k)+'u;uu=r_w<<'+str(32-k)+';}\n'
            offset+=(high-low)>>k
        if len(groups)>1:dispatch='uint32_t ui,uu;\n'+dispatch
        coefficient='ur->packed.half[0]' if narrow else '(int32_t)(uc<<8)>>8'
        replacement='''        if (r_w < 0xC1000000u) {
            '''+dispatch+'''
            const struct ue_row *ur=&ue_rows[ui];
            uint32_t uc=ur->packed.word;
            int32_t us=ur->c2+r_mulhsx_r('''+coefficient+''',uu);
            us=ur->c1+r_mulhsx_r(us,uu);
            uint32_t uq=uc+(uint32_t)r_mulhsx_r(us,uu);
            if((uq<<24)>uc) return ur->base-(uq>>8);
            /* Cell replay warrants only the guarded return. The old residual
             * correction also assumes its original approximation phase;
             * every uncertain case uses the complete range reducer. */
            r_cB=&r_exp8_r;
            goto r_negmain_;
        }
'''
        candidate=replace_family(source,replacement)
        anchor='static inline uint32_t r_eik_exp_r('
        if candidate.count(anchor)!=1:raise ValueError('table anchor')
        candidate=candidate.replace(anchor,table+anchor)
        if len(candidate.encode())>262144:raise ValueError('source limit')
        name='cap'+str(cap);(a.out/(name+'.c')).write_text(candidate)
        receipt={'cap':cap,'active_cells':len(active),'total_cells':len(records),
                 'source_sha256':hashlib.sha256(candidate.encode()).hexdigest(),
                 'source_bytes':len(candidate.encode()),'groups':groups,'signed_cubic_bits':16 if narrow else 24}
        (a.out/(name+'-certificate.json')).write_text(json.dumps(receipt,indent=2)+'\n')
        print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()
