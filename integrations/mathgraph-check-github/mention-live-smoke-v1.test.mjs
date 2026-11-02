import test from 'node:test';
import assert from 'node:assert/strict';
const mod=await import('./mention-live-smoke-v1.mjs').catch(()=>({}));
test('smoke script exposes dependency-injected live check',()=>assert.equal(typeof mod.liveSmoke,'function'));
test('missing key fails before requests and never prints it',async()=>{
 let calls=0;await assert.rejects(mod.liveSmoke({env:{},fetcher:async()=>{calls++;}}),/OPENAI_API_KEY_REQUIRED/);assert.equal(calls,0);
});
test('live smoke uses real adapter and returns only safe accounting fields',async()=>{
 const proposal={summary:'Assumption contains the conclusion',findings:[{title:'Circular assumption',detail:'The claimed universal statement is not established by assuming it.'}],next_step:'Attempt the original claim without that assumption.'};let request;
 const result=await mod.liveSmoke({env:{OPENAI_API_KEY:'fixture-private-key'},fetcher:async(url,options)=>{request={url,options};return new Response(JSON.stringify({id:'resp_fixture',model:'gpt-6.1-sol',status:'completed',usage:{input_tokens:500,output_tokens:350},output:[{type:'message',content:[{type:'output_text',text:JSON.stringify(proposal)}]}]}));}});
 assert.equal(result.status,'LIVE_MODEL_RESPONSE_VALIDATED');assert.equal(result.proof,'NOT_REPLAYED');assert.equal(result.meaning,'UNVERIFIED');assert.equal(result.api_calls,1);assert.equal(result.usage.input_tokens,500);assert.ok(result.reserved_cents<=25);assert.doesNotMatch(JSON.stringify(result),/fixture-private-key/);assert.equal(JSON.parse(request.options.body).max_output_tokens,4096);
});
test('provider errors are sanitized, single attempt only',async()=>{
 let calls=0;await assert.rejects(mod.liveSmoke({env:{OPENAI_API_KEY:'fixture-private-key'},fetcher:async()=>{calls++;return new Response(JSON.stringify({error:{message:'private-key'}}),{status:401});}}),/MODEL_HTTP_401/);assert.equal(calls,1);
});
