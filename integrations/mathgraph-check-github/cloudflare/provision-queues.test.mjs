import test from "node:test";
import assert from "node:assert/strict";
import {ensureQueues,QUEUE_NAMES} from "./provision-queues.mjs";

function fixture(initial=[]){
  const names=new Set(initial),calls=[];
  const fetcher=async (raw,opts)=>{
    const u=new URL(raw);
    assert.equal(u.hostname,"api.cloudflare.com");
    assert.equal(opts.headers.Authorization,"Bearer fixture-token-12345");
    calls.push(opts.method);
    if(opts.method==="GET")
      return new Response(JSON.stringify({success:true,
        result:[...names].map(queue_name=>({queue_name})),
        result_info:{total_pages:1}}),{status:200});
    if(opts.method==="POST"){
      const {queue_name}=JSON.parse(opts.body);
      names.add(queue_name);
      return new Response(JSON.stringify({success:true,result:{queue_name}}),{status:200});
    }
    throw Error("OTHER_METHOD");
  };
  const run=()=>ensureQueues({
    accountId:"a".repeat(32),apiToken:"fixture-token-12345",fetcher
  });
  return {names,calls,run};
}
test("creates both queues and verifies them by independent list",async()=>{
  const f=fixture();
  const r=await f.run();
  assert.deepEqual(r.created,QUEUE_NAMES);
  assert.deepEqual([...f.names].sort(),[...QUEUE_NAMES].sort());
});
test("repeated provisioning doesn't create a duplicate queue",async()=>{
  const f=fixture(QUEUE_NAMES);
  const r=await f.run();
  assert.deepEqual(r.created,[]);
  assert.deepEqual(f.calls,["GET","GET"]);
});
test("rejects missing credentials before network access",async()=>{
  await assert.rejects(ensureQueues({accountId:"",apiToken:""}),
    /CLOUDFLARE_DEPLOY_CREDENTIALS_MISSING/);
});
