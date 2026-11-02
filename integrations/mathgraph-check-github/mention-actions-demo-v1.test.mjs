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
