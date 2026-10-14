import test from 'node:test';
import assert from 'node:assert/strict';
import {createHmac,generateKeyPairSync} from 'node:crypto';
import {once} from 'node:events';
import {start} from './webhook.mjs';

const SHA='a04aa77aaebd81d11274560e8d24d90c6f417589';
const REPO='metalogiclabs/go-ethereum';
const SECRET='only-a-local-test-secret';
const json=x=>new Response(JSON.stringify(x),{status:200});

async function deliver(send,id,payload,secret=SECRET){
  const body=Buffer.from(JSON.stringify(payload));
  const signature='sha256='+createHmac('sha256',secret).update(body).digest('hex');
  return send('/github/webhook',{method:'POST',headers:{
    'content-type':'application/json','x-hub-signature-256':signature,
    'x-github-delivery':id,'x-github-event':'pull_request'
  },body});
}
async function waitForChecks(checks,count){
  for(let i=0;i<100 && checks.length<count;i++)
    await new Promise(r=>setTimeout(r,10));
  assert.equal(checks.length,count);
}

test('signed actual HTTP delivery gives one neutral exact-head Check Run',async()=>{
  const realFetch=globalThis.fetch;
  const keys=generateKeyPairSync('rsa',{modulusLength:2048});
  const checks=[];
  let liveHead=SHA;
  globalThis.fetch=async(input,opts={})=>{
    const url=new URL(input);
    assert.equal(url.origin,'https://api.github.com');
    if(url.pathname==='/app/installations/42/access_tokens'){
      assert.equal(opts.method,'POST');
      assert.match(opts.headers.Authorization,/^Bearer /);
      return json({token:'test-install-token'});
    }
    assert.equal(opts.headers.Authorization,'Bearer test-install-token');
    if(url.pathname==='/repos/'+REPO+'/pulls/19')
      return json({head:{sha:liveHead}});
    if(url.pathname==='/repos/'+REPO+'/pulls/19/files')
      return json([{filename:'.github/workflows/bal-test.yml',
        patch:'+echo remote_conflicting_fcu=UNKNOWN'}]);
    if(url.pathname==='/repos/'+REPO+'/actions/runs')
      return json({total_count:1,workflow_runs:[{id:1001,name:'BAL qualifier',
        head_sha:SHA,status:'completed',conclusion:'success'}]});
    if(url.pathname==='/repos/'+REPO+'/check-runs' && opts.method==='POST'){
      checks.push(JSON.parse(opts.body));
      return json({id:1002});
    }
    throw Error('UNEXPECTED_GITHUB_API_REQUEST: '+url.pathname);
  };
  let server;
  try{
    server=start({PORT:'0',GITHUB_APP_ID:'123',
      GITHUB_APP_PRIVATE_KEY:keys.privateKey.export({type:'pkcs8',format:'pem'}),
      GITHUB_WEBHOOK_SECRET:SECRET,MATHGRAPH_ALLOWED_REPOS:REPO});
    if(!server.listening) await once(server,'listening');
    const root='http://127.0.0.1:'+server.address().port;
    const send=(path,opts)=>realFetch(root+path,opts);
    const payload={action:'opened',repository:{full_name:REPO},
      installation:{id:42},pull_request:{number:19,head:{sha:SHA}}};
    assert.equal((await deliver(send,'delivery-1',payload)).status,202);
    await waitForChecks(checks,1);
    assert.equal(checks[0].head_sha,SHA);
    assert.equal(checks[0].conclusion,'neutral');
    assert.equal(checks[0].name,'MathGraph Check / evidence scope');
    assert.match(checks[0].output.summary,/remote_conflicting_fcu=UNKNOWN/);
    assert.equal((await deliver(send,'delivery-1',payload)).status,202);
    assert.equal((await deliver(send,'bad-signature',payload,'wrong-secret')).status,401);
    assert.equal((await deliver(send,'other-repository',
      {...payload,repository:{full_name:'ethereum/go-ethereum'}})).status,202);
    await new Promise(r=>setTimeout(r,70));
    assert.equal(checks.length,1);
    liveHead='f'.repeat(40);
    assert.equal((await deliver(send,'stale-head',payload)).status,202);
    await new Promise(r=>setTimeout(r,70));
    assert.equal(checks.length,1,'stale PR head must not receive a check');
  }finally{
    globalThis.fetch=realFetch;
    if(server) await new Promise(resolve=>server.close(resolve));
  }
});
