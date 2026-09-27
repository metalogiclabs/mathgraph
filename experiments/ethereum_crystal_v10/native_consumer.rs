use std::alloc::{GlobalAlloc, Layout, System};
use std::fs;
use std::hint::black_box;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::time::Instant;

struct CountingAlloc;
static COUNT: AtomicBool = AtomicBool::new(false);
static ALLOC_BYTES: AtomicUsize = AtomicUsize::new(0);
static ALLOC_CALLS: AtomicUsize = AtomicUsize::new(0);

unsafe impl GlobalAlloc for CountingAlloc {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if COUNT.load(Ordering::Relaxed) {
            ALLOC_BYTES.fetch_add(layout.size(), Ordering::Relaxed);
            ALLOC_CALLS.fetch_add(1, Ordering::Relaxed);
        }
        System.alloc(layout)
    }
    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) { System.dealloc(ptr, layout) }
    unsafe fn realloc(&self, ptr: *mut u8, layout: Layout, new_size: usize) -> *mut u8 {
        if COUNT.load(Ordering::Relaxed) {
            ALLOC_BYTES.fetch_add(new_size, Ordering::Relaxed);
            ALLOC_CALLS.fetch_add(1, Ordering::Relaxed);
        }
        System.realloc(ptr, layout, new_size)
    }
}
#[global_allocator] static A: CountingAlloc = CountingAlloc;

#[derive(Clone, Copy, Default)]
struct Span { list: bool, s: usize, e: usize, next: usize }

fn span_at(b:&[u8], p:usize)->Span {
    let x=b[p];
    if x<=0x7f { return Span{list:false,s:p,e:p+1,next:p+1}; }
    if x<=0xb7 {
        let n=(x-0x80) as usize; let s=p+1;
        return Span{list:false,s,e:s+n,next:s+n};
    }
    if x<=0xbf {
        let q=(x-0xb7) as usize;
        let n=usize::from_be_bytes({
            let mut a=[0u8; std::mem::size_of::<usize>()];
            let src=&b[p+1..p+1+q]; let start=a.len()-q; a[start..].copy_from_slice(src); a
        });
        let s=p+1+q; return Span{list:false,s,e:s+n,next:s+n};
    }
    if x<=0xf7 {
        let n=(x-0xc0) as usize; let s=p+1;
        return Span{list:true,s,e:s+n,next:s+n};
    }
    let q=(x-0xf7) as usize;
    let n=usize::from_be_bytes({
        let mut a=[0u8; std::mem::size_of::<usize>()];
        let src=&b[p+1..p+1+q]; let start=a.len()-q; a[start..].copy_from_slice(src); a
    });
    let s=p+1+q; Span{list:true,s,e:s+n,next:s+n}
}

fn fixed<const N:usize>(b:&[u8], x:Span)->[Span;N] {
    assert!(x.list);
    let mut out=[Span::default();N]; let mut p=x.s; let mut i=0;
    while p<x.e { assert!(i<N); let q=span_at(b,p); out[i]=q; i+=1; p=q.next; }
    assert_eq!(p,x.e); assert_eq!(i,N); out
}
fn bytes(b:&[u8], x:Span)->Vec<u8> { assert!(!x.list); b[x.s..x.e].to_vec() }

type Pair=(Vec<u8>,Vec<u8>);
#[derive(Debug)] struct Storage { slot:Vec<u8>, changes:Vec<Pair> }
#[derive(Debug)] struct FullAccount { addr:Vec<u8>, storage:Vec<Storage>, reads:Vec<Vec<u8>>, balances:Vec<Pair>, nonces:Vec<Pair>, codes:Vec<Pair> }
#[derive(Debug)] struct DepAccount { addr:Vec<u8>, reads:Vec<Vec<u8>>, slots:Vec<Vec<u8>> }
#[derive(Debug)] struct ReconAccount { addr:Vec<u8>, storage:Vec<Storage>, balances:Vec<Pair>, nonces:Vec<Pair>, codes:Vec<Pair> }

fn parse_pairs(b:&[u8], x:Span)->Vec<Pair> {
    assert!(x.list); let mut out=Vec::new(); let mut p=x.s;
    while p<x.e {
        let q=span_at(b,p); let f=fixed::<2>(b,q);
        out.push((bytes(b,f[0]),bytes(b,f[1]))); p=q.next;
    }
    assert_eq!(p,x.e); out
}
fn parse_storage(b:&[u8], x:Span)->Vec<Storage> {
    assert!(x.list); let mut out=Vec::new(); let mut p=x.s;
    while p<x.e {
        let q=span_at(b,p); let f=fixed::<2>(b,q);
        out.push(Storage{slot:bytes(b,f[0]),changes:parse_pairs(b,f[1])}); p=q.next;
    }
    assert_eq!(p,x.e); out
}
fn parse_reads(b:&[u8], x:Span)->Vec<Vec<u8>> {
    assert!(x.list); let mut out=Vec::new(); let mut p=x.s;
    while p<x.e { let q=span_at(b,p); out.push(bytes(b,q)); p=q.next; }
    out
}
fn parse_full(raw:&[u8])->Vec<FullAccount> {
    let root=span_at(raw,0); assert!(root.list); assert_eq!(root.next,raw.len());
    let mut out=Vec::new(); let mut p=root.s;
    while p<root.e {
        let a=span_at(raw,p); let f=fixed::<6>(raw,a);
        out.push(FullAccount{
            addr:bytes(raw,f[0]), storage:parse_storage(raw,f[1]), reads:parse_reads(raw,f[2]),
            balances:parse_pairs(raw,f[3]), nonces:parse_pairs(raw,f[4]), codes:parse_pairs(raw,f[5])
        }); p=a.next;
    }
    out
}
fn parse_dep(raw:&[u8])->Vec<DepAccount> {
    let root=span_at(raw,0); assert!(root.list); let mut out=Vec::new(); let mut p=root.s;
    while p<root.e {
        let a=span_at(raw,p); let f=fixed::<6>(raw,a);
        let mut slots=Vec::new(); let mut q=f[1].s;
        while q<f[1].e {
            let se=span_at(raw,q); let sf=fixed::<2>(raw,se);
            slots.push(bytes(raw,sf[0])); q=se.next;
        }
        out.push(DepAccount{addr:bytes(raw,f[0]),reads:parse_reads(raw,f[2]),slots}); p=a.next;
    }
    out
}
fn parse_recon(raw:&[u8])->Vec<ReconAccount> {
    let root=span_at(raw,0); assert!(root.list); let mut out=Vec::new(); let mut p=root.s;
    while p<root.e {
        let a=span_at(raw,p); let f=fixed::<6>(raw,a);
        out.push(ReconAccount{
            addr:bytes(raw,f[0]), storage:parse_storage(raw,f[1]),
            balances:parse_pairs(raw,f[3]), nonces:parse_pairs(raw,f[4]), codes:parse_pairs(raw,f[5])
        }); p=a.next;
    }
    out
}

fn len_prefix(mut n:usize)->Vec<u8> {
    if n==0 { return vec![0]; }
    let mut tmp=[0u8;8]; let mut i=8;
    while n>0 { i-=1; tmp[i]=(n&255) as u8; n>>=8; }
    tmp[i..].to_vec()
}
fn enc_bytes(x:&[u8])->Vec<u8> {
    if x.len()==1 && x[0]<=0x7f { return vec![x[0]]; }
    let mut out=Vec::new();
    if x.len()<=55 { out.push(0x80+x.len() as u8); }
    else { let q=len_prefix(x.len()); out.push(0xb7+q.len() as u8); out.extend(q); }
    out.extend_from_slice(x); out
}
fn enc_list(items:Vec<Vec<u8>>)->Vec<u8> {
    let n:usize=items.iter().map(|x|x.len()).sum(); let mut out=Vec::new();
    if n<=55 { out.push(0xc0+n as u8); }
    else { let q=len_prefix(n); out.push(0xf7+q.len() as u8); out.extend(q); }
    for x in items { out.extend(x); } out
}
fn enc_pair(p:&Pair)->Vec<u8> { enc_list(vec![enc_bytes(&p.0),enc_bytes(&p.1)]) }
fn reassemble(dep:&[DepAccount], rec:&[ReconAccount])->Vec<u8> {
    assert_eq!(dep.len(),rec.len()); let mut accts=Vec::new();
    for (d,r) in dep.iter().zip(rec.iter()) {
        assert_eq!(d.addr,r.addr); assert_eq!(d.slots.len(),r.storage.len());
        let mut storage=Vec::new();
        for (slot,s) in d.slots.iter().zip(r.storage.iter()) {
            assert_eq!(*slot,s.slot);
            let changes=enc_list(s.changes.iter().map(enc_pair).collect());
            storage.push(enc_list(vec![enc_bytes(slot),changes]));
        }
        let reads=enc_list(d.reads.iter().map(|x|enc_bytes(x)).collect());
        let bals=enc_list(r.balances.iter().map(enc_pair).collect());
        let nonces=enc_list(r.nonces.iter().map(enc_pair).collect());
        let codes=enc_list(r.codes.iter().map(enc_pair).collect());
        accts.push(enc_list(vec![enc_bytes(&d.addr),enc_list(storage),reads,bals,nonces,codes]));
    }
    enc_list(accts)
}

fn read_corpus(path:&str)->Vec<Vec<u8>> {
    let b=fs::read(path).unwrap(); assert_eq!(&b[0..4],b"CV10");
    let mut p=4; let n=u32::from_le_bytes(b[p..p+4].try_into().unwrap()) as usize; p+=4;
    let mut out=Vec::with_capacity(n);
    for _ in 0..n {
        let q=u32::from_le_bytes(b[p..p+4].try_into().unwrap()) as usize; p+=4;
        out.push(b[p..p+q].to_vec()); p+=q;
    }
    assert_eq!(p,b.len()); out
}
fn checksum_full(v:&[FullAccount])->usize {
    v.iter().map(|a| a.addr.len()+a.reads.len()+a.storage.len()+a.balances.len()+a.nonces.len()+a.codes.len()).sum()
}
fn checksum_dep(v:&[DepAccount])->usize { v.iter().map(|a|a.addr.len()+a.reads.len()+a.slots.len()).sum() }
fn checksum_rec(v:&[ReconAccount])->usize { v.iter().map(|a|a.addr.len()+a.storage.len()+a.balances.len()+a.nonces.len()+a.codes.len()).sum() }

fn pass_full(rs:&[Vec<u8>])->usize { rs.iter().map(|r|{let v=parse_full(r); black_box(checksum_full(&v))}).sum() }
fn pass_dep(rs:&[Vec<u8>])->usize { rs.iter().map(|r|{let v=parse_dep(r); black_box(checksum_dep(&v))}).sum() }
fn pass_rec(rs:&[Vec<u8>])->usize { rs.iter().map(|r|{let v=parse_recon(r); black_box(checksum_rec(&v))}).sum() }

fn median(mut x:Vec<f64>)->f64 { x.sort_by(|a,b|a.partial_cmp(b).unwrap()); x[x.len()/2] }
fn timed(rs:&[Vec<u8>], f:fn(&[Vec<u8>])->usize)->f64 {
    COUNT.store(false,Ordering::Relaxed);
    let mut ts=Vec::new();
    for _ in 0..9 {
        let t=Instant::now(); let mut c=0usize;
        for _ in 0..100 { c^=black_box(f(rs)); }
        black_box(c); ts.push(t.elapsed().as_secs_f64());
    }
    median(ts)
}
fn allocated(rs:&[Vec<u8>], f:fn(&[Vec<u8>])->usize)->(usize,usize) {
    ALLOC_BYTES.store(0,Ordering::Relaxed); ALLOC_CALLS.store(0,Ordering::Relaxed);
    COUNT.store(true,Ordering::Relaxed); black_box(f(rs)); COUNT.store(false,Ordering::Relaxed);
    (ALLOC_BYTES.load(Ordering::Relaxed),ALLOC_CALLS.load(Ordering::Relaxed))
}

fn main() {
    let args:Vec<String>=std::env::args().collect(); assert!(args.len()>=2);
    let rs=read_corpus(&args[1]); assert!(!rs.is_empty());

    for r in &rs {
        let d=parse_dep(r); let q=parse_recon(r); let rebuilt=reassemble(&d,&q);
        assert_eq!(&rebuilt,r);
    }

    let ft=timed(&rs,pass_full); let dt=timed(&rs,pass_dep); let rt=timed(&rs,pass_rec);
    let (fb,fc)=allocated(&rs,pass_full); let (db,dc)=allocated(&rs,pass_dep); let (rb,rc)=allocated(&rs,pass_rec);
    let raw:usize=rs.iter().map(|x|x.len()).sum();

    println!("ETHEREUM_CRYSTAL_V10_NATIVE=PASS");
    println!("records={} raw_bal_bytes={}",rs.len(),raw);
    println!("full_median_s={:.6} dependency_median_s={:.6} reconstruction_median_s={:.6}",ft,dt,rt);
    println!("dependency_speedup_vs_full={:.3} reconstruction_speedup_vs_full={:.3}",ft/dt,ft/rt);
    println!("full_alloc_bytes={} dependency_alloc_bytes={} reconstruction_alloc_bytes={}",fb,db,rb);
    println!("dependency_alloc_ratio={:.6} reconstruction_alloc_ratio={:.6}",db as f64/fb as f64,rb as f64/fb as f64);
    println!("full_alloc_calls={} dependency_alloc_calls={} reconstruction_alloc_calls={}",fc,dc,rc);
    println!("native_exact_reassembly_all_heldout=true");

    if args.len()>2 {
        let cert=format!(
            "{{\n  \"protocol\": \"ETHEREUM_CRYSTAL_V10_NATIVE\",\n  \"records\": {},\n  \"raw_bal_bytes\": {},\n  \"full_median_s\": {:.9},\n  \"dependency_median_s\": {:.9},\n  \"reconstruction_median_s\": {:.9},\n  \"dependency_speedup_vs_full\": {:.9},\n  \"reconstruction_speedup_vs_full\": {:.9},\n  \"full_alloc_bytes\": {},\n  \"dependency_alloc_bytes\": {},\n  \"reconstruction_alloc_bytes\": {},\n  \"dependency_alloc_ratio\": {:.9},\n  \"reconstruction_alloc_ratio\": {:.9},\n  \"full_alloc_calls\": {},\n  \"dependency_alloc_calls\": {},\n  \"reconstruction_alloc_calls\": {},\n  \"exact_reassembly_all\": true,\n  \"claim_boundary\": \"optimized dependency-free Rust microbenchmark on pinned held-out EELS BAL RLP corpus\"\n}}\n",
            rs.len(),raw,ft,dt,rt,ft/dt,ft/rt,fb,db,rb,db as f64/fb as f64,rb as f64/fb as f64,fc,dc,rc
        );
        fs::write(&args[2],cert).unwrap();
    }
}
