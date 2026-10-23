"""Read-only, bounded acquisition. No order submission or trading methods."""
from __future__ import annotations
import argparse, collections, datetime, hashlib, json, time, urllib.request, urllib.error
from pathlib import Path

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def classify(receipt):
    if receipt.get('error'):
        return {'kind':'TRANSPORT_ERROR'}
    status=receipt.get('status')
    if status==429:
        return {'kind':'THROTTLED'}
    if status!=200:
        return {'kind':'HTTP_ERROR'}
    try:
        obj=json.loads(receipt['body'])
    except (ValueError, KeyError):
        return {'kind':'INVALID_JSON'}
    orders=obj.get('orders') if isinstance(obj,dict) else None
    if not isinstance(orders,list) or any(not isinstance(o,dict) for o in orders):
        return {'kind':'UNKNOWN_SCHEMA'}
    return {'kind':'SUCCESS','orders':orders}

def unique_orders(receipts):
    seen={}
    for r in receipts:
        for o in classify(r).get('orders',[]):
            key=o.get('orderHash')
            if not isinstance(key,str) or not key:
                continue
            if key not in seen:
                seen[key]={'order':o,'first_seen_utc':r.get('finished_utc'),'observations':0}
            seen[key]['observations']+=1
            seen[key]['last_seen_utc']=r.get('finished_utc')
    return list(seen.values())

def request(url, payload=None):
    if payload is not None and payload.get('method') not in {'eth_chainId','eth_getBlockByNumber','eth_blockNumber'}:
        raise ValueError('RPC_METHOD_NOT_ALLOWED')
    r={'url':url,'started_utc':utc(),'request':payload}
    start=time.monotonic()
    try:
        req=urllib.request.Request(url, data=None if payload is None else json.dumps(payload).encode(),
             headers={'User-Agent':'MathGraph-read-only-research/1.0','Content-Type':'application/json','Accept':'application/json'})
        with urllib.request.urlopen(req,timeout=10) as res:
            r.update(status=res.status,headers=dict(res.headers),body=res.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        r.update(status=e.code,headers=dict(e.headers),body=e.read().decode('utf-8',errors='replace'))
    except Exception as e:
        r['error']=type(e).__name__+': '+str(e)
    r.update(finished_utc=utc(),elapsed_seconds=time.monotonic()-start)
    if 'body' in r:r['body_sha256']=hashlib.sha256(r['body'].encode()).hexdigest()
    return r

def run(directory, polls):
    root=Path(directory);root.mkdir(parents=True,exist_ok=True)
    def save(name,r):
        (root/(name+'.json')).write_text(json.dumps(r,indent=2))
        return r
    start=utc(); base='https://api.uniswap.org/v2/'
    save('schema',request(base+'uniswapx/docs.json'))
    for i,method in enumerate(('eth_chainId','eth_getBlockByNumber')):
        r=save('rpc_'+str(i),request('https://mainnet.base.org',{'jsonrpc':'2.0','id':i+1,'method':method,'params':[] if method=='eth_chainId' else ['latest',False]}))
        print('RPC',method,json.dumps(r)[:1800],flush=True)
    before=save('recent_before',request(base+'orders?chainId=8453&orderType=Dutch_V3&limit=50'))
    print('RECENT_BEFORE',json.dumps(before)[:14000],flush=True)
    if before.get('status')==429: polls=0
    receipts=[]
    for i in range(polls):
        t=time.monotonic()
        r=save(f'open_{i:03d}',request(base+'orders?orderStatus=open&chainId=8453&orderType=Dutch_V3&limit=50'))
        receipts.append(r);c=classify(r)
        if i in {0,14,29,59,89}:
            print('POLL',i,c.get('kind'),'count',len(c.get('orders',[])),flush=True)
            if i==0:print('FIRST_OPEN',json.dumps(r)[:18000],flush=True)
        if r.get('status')==429:break
        time.sleep(max(0,2-(time.monotonic()-t)))
    throttle=any(r.get('status')==429 for r in [before]+receipts)
    if not throttle:
        after=save('recent_after',request(base+'orders?chainId=8453&orderType=Dutch_V3&limit=50'))
        if after.get('status')!=429:
            save('filled',request(base+'orders?orderStatus=filled&chainId=8453&orderType=Dutch_V3&limit=50'))
    unique=unique_orders(receipts)
    (root/'unique_open_orders.json').write_text(json.dumps(unique,indent=2))
    counts=collections.Counter(classify(r)['kind'] for r in receipts)
    summary={'started_utc':start,'finished_utc':utc(),'planned_polls':90,'attempted_polls':len(receipts),'response_kinds':dict(counts),
      'unique_order_hashes':len(unique),'returned_observations':sum(len(classify(r).get('orders',[])) for r in receipts),
      'throttled':throttle,'status':'ACQUISITION_ONLY_NO_FILLABILITY_OR_PROFIT_CLAIM','trades_submitted':0}
    (root/'summary.json').write_text(json.dumps(summary,indent=2));print('SUMMARY',json.dumps(summary),flush=True)
    manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob('*.json'))}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2))
    return summary

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='out/orderfill');ap.add_argument('--polls',type=int,default=90)
    a=ap.parse_args();assert 1<=a.polls<=90;run(a.out,a.polls)
