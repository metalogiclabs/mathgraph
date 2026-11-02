import test from 'node:test';import assert from 'node:assert/strict';
const m=await import('./mention-actions-demo-v1.mjs').catch(()=>({}));
const event={action:'created',repository:{full_name:'metalogiclabs/mathgraph'},sender:{id:32909488,type:'User'},issue:{number:1,pull_request:{}},comment:{id:10,body:'@MathGraph -check',user:{id:32909488,type:'User'}}};
test('actions controller exposes authenticated demo event gate',()=>assert.equal(typeof m.demoCommand,'function'));
test('only original approved comment is eligible',()=>{
 assert.equal(m.demoCommand(event,{attempt:1}),'check');
 for(const e of [{...event,sender:{id:1,type:'User'}},{...event,action:'edited'},{...event,repository:{full_name:'outsider/repo'}},{...event,comment:{...event.comment,body:'> @MathGraph -check'}},{...event,comment:{...event.comment,user:{id:1,type:'User'}}}])assert.equal(m.demoCommand(e,{attempt:1}),null);
 assert.equal(m.demoCommand(event,{attempt:2}),null);
});
test('demo rendering distinguishes accepted proof from rejected intended consumer',()=>{
 const body=m.demoComment({command:'check',sha:'a'.repeat(40),native:{status:'CLAIM_NOT_ESTABLISHED',source_compiles:true},runURL:'https://github.com/metalogiclabs/mathgraph/actions/runs/1'});
 assert.match(body,/Proof compiles/);assert.match(body,/original claim is not established/);assert.match(body,/@MathGraph -fix/);assert.match(body,/Controlled demo/);
});
test('repair is only labelled verified after native original-target check',()=>{
 assert.doesNotMatch(m.demoComment({command:'fix',sha:'a'.repeat(40),native:{status:'UNKNOWN'}}),/Repair verified/);
 assert.match(m.demoComment({command:'fix',sha:'a'.repeat(40),native:{status:'ORIGINAL_TARGET_VERIFIED',axioms:[]},repairURL:'https://github.com/metalogiclabs/mathgraph/pull/2'}),/Repair verified/);
});
test('repair publishing checks head after file write and withdraws a stale opened PR',async()=>{
 const pr={head:{ref:'demo'}},sha='a'.repeat(40),args={root:'/repos/metalogiclabs/mathgraph',pr,sha,sourceFile:{sha:'blob'},repaired:'proof',event:{issue:{number:1},comment:{id:2}},runURL:'https://github.com/metalogiclabs/mathgraph/actions/runs/3'};
 for(const moveAt of [2,3]){
  let reads=0,opened=0,closed=0;
  const api=async(path,options={})=>{
   if(path.endsWith('/pulls/1')){reads++;return {state:'open',head:{sha:reads>=moveAt?'b'.repeat(40):sha}};}
   if(path.endsWith('/pulls')&&options.method==='POST'){opened++;return {number:4,html_url:'https://github.com/metalogiclabs/mathgraph/pull/4'};}
   if(path.endsWith('/pulls/4')&&options.method==='PATCH'){closed++;return {state:'closed'};}
   return {};
  };
  await assert.rejects(m.createVerifiedRepair({...args,api}),/SOURCE_MOVED/);
  assert.equal(opened,moveAt===2?0:1);assert.equal(closed,moveAt===3?1:0);
 }
});
test('source updates withdraw only this pilot bot results without model calls',async()=>{
 const old='a'.repeat(40),head='b'.repeat(40),patched=[];
 const comment={id:5,user:{login:'github-actions[bot]'},body:'<!-- mathgraph-actions-demo-v1:1 -->\n### MathGraph Check\nRevision: `'+old+'`\nOld evidence'};
 const api=async(path,options={})=>{
  if(path.endsWith('/pulls/1'))return {head:{sha:head,repo:{full_name:'metalogiclabs/mathgraph'}}};
  if(path.includes('/comments?'))return [comment,{...comment,id:6,user:{login:'someone'}},{...comment,id:7,body:'unrelated'}];
  if(options.method==='PATCH'){patched.push(options.body.body);return {id:5};}
  throw Error('unexpected');
 };
 const n=await m.withdrawDemoComments({api,root:'/repos/metalogiclabs/mathgraph',number:1});assert.equal(n,1);assert.match(patched[0],/Source changed/);assert.match(patched[0],/Old evidence/);
});
