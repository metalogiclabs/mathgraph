import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, readFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
const mod=await import('./mention-agent-v1.mjs').catch(()=>({}));
const sha='a'.repeat(40), other='b'.repeat(40);
const snapshot={repository:'metalogiclabs/demo',number:1,sha,files:[{filename:'Control.lean',patch:'+theorem t : True := by trivial'}],runs:[],files_visibility:'COMPLETE',ci_visibility:'COMPLETE'};
const event={action:'created',repository:{full_name:snapshot.repository},sender:{id:7,type:'User'},issue:{number:1,pull_request:{}},comment:{id:12,body:'@MathGraph -check',user:{id:7,type:'User'}}};
const policy={repositories:[snapshot.repository],userIds:[7],handle:'MathGraph',model:'test-model',inputCentsPerMillion:1000,outputCentsPerMillion:3000,maxOutputTokens:500,maxInputBytes:10000,jobCapCents:500,totalCapCents:5000};
const proposal={summary:'Proof replay required',findings:[{title:'Inspect the assumptions',detail:'The diff alone does not establish intent.'}],next_step:'Run the pinned proof checker.'};
async function setup(fn){const dir=await mkdtemp(join(tmpdir(),'mg-mention-'));try{await fn(dir)}finally{await rm(dir,{recursive:true,force:true})}}
function dependencies(dir, overrides={}){
 const published=[],counts={model:0};
 return {published,counts,deps:{stateDir:dir,policy,
  github:{snapshot:async()=>snapshot,head:async()=>sha,publish:async(body,id)=>{published.push({body,id});return id??91;}},
  model:async()=>{counts.model++;return proposal;},...overrides}};
}
test('module exports a mention runner',()=>assert.equal(typeof mod.runMention,'function'));
test('only standalone commands trigger',()=>{
 for(const body of ['@MathGraph -check','@mathgraph -fix','@MathGraph[bot] -check']) assert.ok(mod.parseCommand(body,'MathGraph'));
 for(const body of ['> @MathGraph -check','hello @MathGraph -check','@MathGraph -checker','@MathGraph -check and merge','````\n@MathGraph -check\n````','@Other -check']) assert.equal(mod.parseCommand(body,'MathGraph'),null);
});
test('authorized source-pinned check updates one comment and stays advisory',()=>setup(async dir=>{
 const {deps,published,counts}=dependencies(dir);const result=await mod.runMention(event,deps);
 assert.equal(result.state,'COMPLETED');assert.equal(counts.model,1);
 assert.equal(published.length,2);assert.equal(published[1].id,91);
 assert.match(published[1].body,/Proof replay required/);assert.match(published[1].body,/advisory/i);assert.match(published[1].body,/Meaning.*unverified/i);
 assert.match(published[1].body,new RegExp(sha.slice(0,12)));
}));
test('unauthorized users, forged sender and bots never cause IO',()=>setup(async dir=>{
 for(const e of [{...event,sender:{id:8,type:'User'}},{...event,comment:{...event.comment,user:{id:8,type:'User'}}},{...event,sender:{id:7,type:'Bot'}},{...event,repository:{full_name:'outsider/repo'}}]){
 const {deps,counts,published}=dependencies(dir);assert.equal((await mod.runMention(e,deps)).state,'IGNORED');assert.equal(counts.model,0);assert.equal(published.length,0);
 }
}));
test('concurrent redeliveries reserve and call model once, including after restart',()=>setup(async dir=>{
 const {deps,counts}=dependencies(dir);const results=await Promise.all([mod.runMention(event,deps),mod.runMention(event,deps)]);
 assert.equal(counts.model,1);assert.equal(results.filter(x=>x.state==='DUPLICATE').length,1);
 assert.equal((await mod.runMention(event,deps)).state,'DUPLICATE');
}));
test('budget exhausted across distinct comments before model call',()=>setup(async dir=>{
 const {deps,counts}=dependencies(dir);deps.policy={...policy,jobCapCents:1,totalCapCents:1};
 const r=await mod.runMention(event,deps);assert.equal(r.state,'BUDGET_EXHAUSTED');assert.equal(counts.model,0);
}));
test('concurrent distinct jobs cannot overspend shared total',()=>setup(async dir=>{
 const {deps,counts}=dependencies(dir);const cost=mod.reservationCents(policy);deps.policy={...policy,jobCapCents:cost,totalCapCents:cost};
 const out=await Promise.all([mod.runMention(event,deps),mod.runMention({...event,comment:{...event.comment,id:13}},deps)]);
 assert.equal(counts.model,1);assert.equal(out.filter(x=>x.state==='BUDGET_EXHAUSTED').length,1);
}));
test('head changes during inference withdraw findings',()=>setup(async dir=>{
 const {deps,published}=dependencies(dir);deps.github.head=async()=>other;
 const r=await mod.runMention(event,deps);assert.equal(r.state,'STALE');assert.doesNotMatch(published.at(-1).body,/Inspect the assumptions/);assert.match(published.at(-1).body,/changed/i);
}));
test('model errors remain unknown, retain spend and do not leak errors',()=>setup(async dir=>{
 const {deps,published}=dependencies(dir);deps.model=async()=>{throw Error('secret sk-example');};
 const r=await mod.runMention(event,deps);assert.equal(r.state,'UNKNOWN');assert.doesNotMatch(published.at(-1).body,/sk-example/);
 const files=await import('node:fs/promises').then(fs=>fs.readdir(join(dir,'spend')));assert.equal(files.length,mod.reservationCents(policy));
}));
test('fix command does not call model or pretend a repair was verified',()=>setup(async dir=>{
 const {deps,counts,published}=dependencies(dir);const e={...event,comment:{...event.comment,body:'@MathGraph -fix'}};
 assert.equal((await mod.runMention(e,deps)).state,'REPAIR_NOT_CONFIGURED');assert.equal(counts.model,0);assert.match(published[0].body,/repair.*not.*connected/i);
}));
test('proposal parser rejects verdicts and markdown is escaped',()=>{
 assert.throws(()=>mod.validateProposal({...proposal,verdict:'VERIFIED'}));
 assert.throws(()=>mod.validateProposal({...proposal,findings:[{title:'x',detail:'y',command:'curl evil'}]}));
 const body=mod.renderResult({state:'COMPLETED',sha,proposal:{summary:'<script>@everyone',findings:[],next_step:'[click](https://evil.test)'}});
 assert.doesNotMatch(body,/<script>|@everyone|\[click\]\(https/);assert.match(body,/Meaning.*unverified/i);
});
test('OpenAI adapter sends bounded structured request and checks returned usage',async()=>{
 let request;const adapter=mod.openAIModel({apiKey:'test-key',policy,fetcher:async(url,opts)=>{request={url,opts};return new Response(JSON.stringify({status:'completed',usage:{input_tokens:100,output_tokens:200},output:[{type:'message',content:[{type:'output_text',text:JSON.stringify(proposal)}]}]}));}});
 const actual=await adapter({snapshot});assert.deepEqual(actual,proposal);const body=JSON.parse(request.opts.body);
 assert.equal(request.url,'https://api.openai.com/v1/responses');assert.equal(body.store,false);assert.equal(body.service_tier,'default');assert.equal(body.max_output_tokens,500);assert.equal(body.model,'test-model');assert.equal(body.text.format.type,'json_schema');
});
test('missing API key fails before any network request',()=>assert.throws(()=>mod.openAIModel({policy,fetcher:()=>{throw Error('network');}}),/API_KEY/));
test('input over cap and non-finite rates fail before paid work',()=>setup(async dir=>{
 const {deps,counts}=dependencies(dir);deps.policy={...policy,inputCentsPerMillion:NaN};await assert.rejects(mod.runMention(event,deps),/POLICY/);assert.equal(counts.model,0);
}));

test('failed publication recovers persisted result without another model call',()=>setup(async dir=>{
 const {deps,counts,published}=dependencies(dir);const original=deps.github.publish;
 deps.github.publish=async(body,id)=>{if(id)throw Error('network');return original(body,id);};
 await assert.rejects(mod.runMention(event,deps));assert.equal(counts.model,1);
 deps.github.resumePublish=original;
 const result=await mod.runMention(event,{...deps,recover:true});assert.equal(result.state,'COMPLETED');assert.equal(counts.model,1);assert.match(published.at(-1).body,/Proof replay required/);
}));
test('interrupted claimed job ends unknown without retrying paid inference',()=>setup(async dir=>{
 const {deps,counts,published}=dependencies(dir);const original=deps.github.publish;deps.github.publish=async()=>{throw Error('network');};
 await assert.rejects(mod.runMention(event,deps));deps.github.publish=original;
 const result=await mod.runMention(event,{...deps,recover:true});assert.equal(result.state,'UNKNOWN');assert.equal(counts.model,0);assert.match(published.at(-1).body,/could not finish/);
}));
test('a prior unlocked budget file does not disable new reservations',()=>setup(async dir=>{
 const fs=await import('node:fs/promises');await fs.writeFile(join(dir,'budget.lock'),'old process');
 const {deps,counts}=dependencies(dir);assert.equal((await mod.runMention(event,deps)).state,'COMPLETED');assert.equal(counts.model,1);
}));
test('native observation is separate from model assessment and survives model failure',()=>setup(async dir=>{
 const {deps,published}=dependencies(dir);deps.observeProof=async()=>({status:'NATIVE_REPLAY_OBSERVED',theorem:'Artin_exercise_2_2_9',meaning:'UNVERIFIED',run_url:'https://github.com/metalogiclabs/demo/actions/runs/100'});deps.model=async()=>{throw Error('model unavailable');};
 const r=await mod.runMention(event,deps);assert.equal(r.state,'UNKNOWN');assert.equal(r.proof.status,'NATIVE_REPLAY_OBSERVED');assert.match(published.at(-1).body,/native replay observed/);assert.match(published.at(-1).body,/Meaning.*unverified/i);
}));
test('native observation is withdrawn on changed head, including saved-result recovery',()=>setup(async dir=>{
 const {deps,published}=dependencies(dir);deps.observeProof=async()=>({status:'NATIVE_REPLAY_OBSERVED',theorem:'Artin_exercise_2_2_9',meaning:'UNVERIFIED'});const original=deps.github.publish;
 deps.github.publish=async(body,id)=>{if(id)throw Error('publication failed');return original(body,id);};
 await assert.rejects(mod.runMention(event,deps));deps.github.resumePublish=original;deps.github.head=async()=>other;
 const r=await mod.runMention(event,{...deps,recover:true});assert.equal(r.state,'STALE');assert.equal(r.proof,undefined);assert.doesNotMatch(published.at(-1).body,/native replay observed/);
}));
test('reservation subprocess receives no API credential environment',()=>setup(async dir=>{
 const fs=await import('node:fs/promises');const oldPath=process.env.PATH,oldKey=process.env.OPENAI_API_KEY;
 await fs.writeFile(join(dir,'flock'),'#!/bin/sh\nif [ -n "$OPENAI_API_KEY" ]; then exit 99; fi\nexec /usr/bin/flock "$@"\n',{mode:0o700});
 process.env.PATH=dir+':'+oldPath;process.env.OPENAI_API_KEY='fixture-key-must-not-reach-lock-child';
 try{const {deps}=dependencies(dir);assert.equal((await mod.runMention(event,deps)).state,'COMPLETED');}
 finally{process.env.PATH=oldPath;if(oldKey===undefined)delete process.env.OPENAI_API_KEY;else process.env.OPENAI_API_KEY=oldKey;}
}));
