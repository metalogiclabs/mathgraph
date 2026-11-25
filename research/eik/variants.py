import hashlib,re,sys,pathlib
BASE='3d9777afffd5aba80d52bf4926243aa3dbe1c1fa78b12f63ed597d634895e3b4'
ORIG='c858c54e3e0b07b469d4445028a5ddd7c7ce579932bf42d4575cc3044ef61661'
VARIANTS=['row','index','tl','tsr','small-tanh','small-sigmoid','small-exp','hint-tanh','hint-sigmoid','hint-exp']
def replace(s,a,b,n=1):
    assert s.count(a)==n,(a,s.count(a),n)
    return s.replace(a,b)
def base(s):
    assert hashlib.sha256(s.encode()).hexdigest()==ORIG
    s=re.sub(r'^#ifndef EIK_SEL\n.*?^#endif\n','',s,count=1,flags=re.M|re.S)
    s,n=re.subn(r'if \(\(t_w \* (?:t_w|t_m4)\) == (?:5|13|21|29|37|45|53|61)u\)', 'if (0)',s);assert n==9
    for f in ('sigmoid','tanh','exp'):
        s,n=re.subn(r'if \(EIK_SEL\)\s*return eik_'+f+r'_r\(w\);\s*return t_eik_'+f+r'\(w\);','return eik_'+f+'_r(w);',s);assert n==1
    assert hashlib.sha256(s.encode()).hexdigest()==BASE
    return s
def change(s,v):
    if v=='row':
        a=re.search(r'(static const struct \{ uint32_t hi\[1 << 8\]; uint16_t lo\[1 << 8\]; uint32_t row\[)2 \* 17(\]; \} ex8_r = \{\{.*?\}, \{.*?\}, \{)(.*?)(\}\};)',s,re.S);assert a
        nums=re.findall(r'\d+u',a[3]);assert len(nums)==34 and set(nums[1::2])=={'1488522236u'}
        s=s[:a.start()]+a[1]+'17'+a[2]+'\n    '+', '.join(nums[::2])+'\n'+a[4]+s[a.end():]
        s=replace(s,'ex8_r.row + 4u + 2u *','ex8_r.row + 2u +',2)
        s=replace(s,'ex8_r.row + 2u *','ex8_r.row +',2)
        s=replace(s,'b[1]','1488522236u',4)
    elif v=='index':
        for a,b,n in [
          ('*(const uint32_t *)((const uint8_t *)(ex8_r.hi) + 1020u - 2u * o2)','ex8_r.hi[255u-(o2>>1)]',1),
          ('*(const uint16_t *)((const uint8_t *)(ex8_r.lo) + 510u - o2)','ex8_r.lo[255u-(o2>>1)]',1),
          ('*(const uint32_t *)((const uint8_t *)(ex8_r.hi) + 1020u - ((Y >> 14) & 0x3FCu))','ex8_r.hi[255u-((Y>>16)&255u)]',1),
          ('*(const uint32_t *)((const uint8_t *)(ex8_r.hi) + ((Y >> 15) & 0x3FCu))','ex8_r.hi[(Y>>17)&255u]',1),
          ('*(const uint32_t *)((const uint8_t *)(ex8_r.hi) + ((Y >> 14) & 0x3FCu))','ex8_r.hi[(Y>>16)&255u]',1),
          ('*(const uint32_t *)((const uint8_t *)(ex8_r.hi) + 1020u - ((k << 1) & 0x3FCu))','ex8_r.hi[255u-((k>>1)&255u)]',1)]:s=replace(s,a,b,n)
    elif v=='tl':
        m=re.search(r'static const struct rl_r tl_r\[132\] = \{(.*?)\};',s,re.S);assert m
        rows=[x.split(',') for x in re.findall(r'\{([^{}]+)\}',m[1])];assert len(rows)==132
        c0=[r[0].strip() for r in rows];assert all(c0[i]==c0[i+1] for i in range(1,131,2))
        text='struct tl_comp {int32_t c1,c2,c3;};\nstatic const uint32_t tl_base[67]={'+','.join(c0[::2]+[c0[-1]])+'};\nstatic const struct tl_comp tl_r[132]={\n'+',\n'.join('{'+','.join(r[1:])+'}' for r in rows)+'\n};'
        assert all(c0[i]==(c0[::2]+[c0[-1]])[(i+1)//2] for i in range(132))
        s=s[:m.start()]+text+s[m.end():]
        pos=s.index('static inline uint32_t rb_cell_r')
        s=s[:pos]+'''static inline uint32_t tl_cell_r(uint32_t i, int32_t th) {
 const struct tl_comp *r=&tl_r[i];
 int32_t p=r->c2+mulhs_r(r->c3,th); p=r->c1+mulhs_r(p,th);
 return tl_base[(i+1u)>>1]+(uint32_t)mulhs_r(p,th);
}
'''+s[pos:]
        for offset in ('0xF9Cu','0x2F9Cu'):
            s=replace(s,'const struct rl_r *r = &tl_r[(w >> 18) - '+offset+'];\n        uint32_t V = rl_cell_r(r, (int32_t)(w << 13));','uint32_t ix=(w >> 18)-'+offset+';\n        uint32_t V=tl_cell_r(ix,(int32_t)(w<<13));')
        j=s.index('static inline uint32_t eik_sigmoid_r');k=s.index('static const struct { int32_t c0',j)
        sub=s[j:k];sub=replace(sub,'r->c0 - 0x101u','tl_base[(ix+1u)>>1] - 0x101u',3);s=s[:j]+sub+s[k:]
        s=replace(s,'const struct rl_r *q = (const struct rl_r *)((const uint8_t *)tl_r + (qi_ - (0xF7Cu << 4)));\n        c0v_ = q->c0 - 0x101u;','uint32_t ix=(qi_>>4)-0xF7Cu;\n        c0v_=tl_base[(ix+1u)>>1]-0x101u;')
    elif v=='tsr':
        m=re.search(r'static const uint32_t tsr_r\[82\] = \{(.*?)\};',s,re.S);assert m
        a=re.findall(r'0x[0-9a-f]+u',m[1]);assert len(a)==82
        assert len(set(a[:2]))==1 and len(set(a[2:18]))==1
        s=s[:m.start()]+'static const uint32_t tsr_r[64]={'+','.join(a[18:])+'};\nstatic inline uint32_t tsr_value(uint32_t i){return i<18u?(i<2u?0x8d8ec8bau:0x8e000000u):tsr_r[i-18u];}'+s[m.end():]
        s=replace(s,'tsr_r[(t >> 19) - (115u << 5) - 14u]','tsr_value((t >> 19) - (115u << 5) - 14u)')
    elif v=='small-tanh':
        s=replace(s,'uint32_t t = w << 1;\n    if ((int32_t)t < 0)\n        goto hi_;','uint32_t t = w << 1;\n    if (t < 0x73713000u) return w;\n    if ((int32_t)t < 0)\n        goto hi_;')
        s=replace(s,'        if (t < 0x73713000u)\n            return w;\n','')
    elif v=='small-sigmoid':
        a='static inline uint32_t eik_sigmoid_r(uint32_t w)\n{'
        s=replace(s,a,a+'\n    if ((w << 1) < 0x66ffe000u) return 0x3F000000u;')
    elif v=='small-exp':
        a='static inline uint32_t eik_exp_r(uint32_t w)\n{'
        s=replace(s,a,a+'\n    if ((w << 1) <= 0x66000000u) return 0x3F800000u;')
    elif v.startswith('hint-'):
        f=v[5:];j=s.index('static inline uint32_t eik_'+f+'_r(uint32_t w)');k=s.index('\n}',j)+2
        sub=s[j:k]
        sub,n=re.subn(r'if \(((?:Vf|V|v7|v8|z|t|U9|U|x|Z|P_|u) & (?:0x[0-9A-Fa-f]+|[0-9]+)u|\((?:Vf|V|v7|v8|z|t|U9|U|x|Z|P_|u) & (?:0x[0-9A-Fa-f]+|[0-9]+)u\) != 0u)\)',r'if (__builtin_expect(!!(\1), 1))',sub)
        assert n>=2,(f,n)
        s=s[:j]+sub+s[k:]
    else: raise ValueError(v)
    return s
if __name__=='__main__':
    s=base(pathlib.Path(sys.argv[1]).read_text())
    for v in sys.argv[3:]:s=change(s,v)
    pathlib.Path(sys.argv[2]).write_text(s)
