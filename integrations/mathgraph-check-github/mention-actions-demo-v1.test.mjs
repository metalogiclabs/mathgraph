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
 assert.match(m.demoComment({command:'fix',sha:'a'.repeat(40),repairPerformed:true,native:{status:'ORIGINAL_TARGET_VERIFIED',axioms:[]},repairURL:'https://github.com/metalogiclabs/mathgraph/pull/2'}),/Repair verified/);
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

test('progress uses one branded source-bound card and only its owning run can resume',()=>{
 const args={command:'fix',sha:'a'.repeat(40),runId:12,stage:'prepare',runURL:'https://github.com/metalogiclabs/mathgraph/actions/runs/12'};
 const body=m.demoProgress(args);
 assert.match(body,/mathgraph-progress:12/);assert.match(body,/Preparing/);assert.match(body,/mathgraph-mark-black.png/);
 const c={user:{login:'github-actions[bot]'},body};
 assert.equal(m.ownsDemoProgress(c,args),true);
 assert.equal(m.ownsDemoProgress(c,{...args,runId:13}),false);
 assert.equal(m.ownsDemoProgress(c,{...args,sha:'b'.repeat(40)}),false);
 assert.equal(m.ownsDemoProgress({...c,user:{login:'someone'}},args),false);
 assert.equal(m.ownsDemoProgress({...c,body:m.demoComment({command:'fix',sha:args.sha,native:{status:'UNKNOWN'}})},args),false);
});
test('repair result shows before and after without calling a missing PR ready',()=>{
 const args={command:'fix',repairPerformed:true,sha:'a'.repeat(40),native:{status:'ORIGINAL_TARGET_VERIFIED',axioms:['propext']}};
 const b=m.demoComment(args);assert.match(b,/Conclusion assumed/);assert.match(b,/Conclusion proved/);assert.match(b,/Opening a repair PR was not confirmed/);
 const ready=m.demoComment({...args,repairURL:'https://github.com/metalogiclabs/mathgraph/pull/2'});
 assert.match(ready,/Review the repair/);assert.match(ready,/Controlled demo/);assert.match(ready,/propext/);
});

test('early acknowledgement resumes once and failure cleanup never overwrites a result',async()=>{
 const root='/repos/metalogiclabs/mathgraph',marker='<!-- mathgraph-actions-demo-v1:10 -->',args={command:'fix',sha:'a'.repeat(40),runId:12,runURL:'https://github.com/metalogiclabs/mathgraph/actions/runs/12'};
 let comments=[],posts=0,patches=0;
 const api=async(path,{method='GET',body}={})=>{
  if(method==='GET')return comments;
  if(method==='POST'){posts++;const c={id:15,user:{login:'github-actions[bot]'},body:body.body};comments.push(c);return c;}
  patches++;comments[0].body=body.body;return comments[0];
 };
 const common={api,root,number:1,marker,progressArgs:args};
 assert.equal(await m.startDemoComment({...common,phase:'prepare'}),null);assert.equal(posts,1);
 assert.equal((await m.startDemoComment({...common,phase:'run'})).id,15);assert.equal(posts,1);
 await m.startDemoComment({...common,phase:'finalize'});assert.equal(patches,1);assert.match(comments[0].body,/Verification is incomplete/);
 assert.equal(await m.startDemoComment({...common,phase:'run'}),null);
 await m.startDemoComment({...common,phase:'finalize'});assert.equal(patches,1);
 comments[0].body=marker+'\n'+m.demoComment({...args,repairPerformed:true,native:{status:'ORIGINAL_TARGET_VERIFIED',axioms:['propext']}});
 await m.startDemoComment({...common,phase:'finalize'});assert.equal(patches,1);assert.match(comments[0].body,/Repair verified/);
});

test('an already valid source never invents a repair or a publication failure',()=>{
 const b=m.demoComment({command:'fix',sha:'a'.repeat(40),native:{status:'ORIGINAL_TARGET_VERIFIED',axioms:['propext']}});
 assert.match(b,/original claim passes/);assert.doesNotMatch(b,/Conclusion assumed|Repair verified|Opening a repair PR/);
});

test('publisher uses the fixed MathGraph App identity and separates read and write tokens',()=>{
 const a=m.publicationAuth({GITHUB_TOKEN:'actions-token-for-read'});
 assert.equal(a.botLogin,'github-actions[bot]');assert.equal(m.publicationToken(a,'POST'),'actions-token-for-read');
 const app=m.publicationAuth({GITHUB_TOKEN:'actions-token-for-read',MATHGRAPH_APP_TOKEN:'app-token-for-publish',MATHGRAPH_APP_SLUG:'mathgraph-check'});
 assert.equal(app.botLogin,'mathgraph-check[bot]');assert.equal(m.publicationToken(app,'GET'),'actions-token-for-read');
 assert.equal(m.publicationToken(app,'POST'),'app-token-for-publish');
 assert.equal(m.publicationToken(app,'PATCH','github-actions[bot]'),'actions-token-for-read');
 assert.equal(m.publicationToken(app,'PATCH','mathgraph-check[bot]'),'app-token-for-publish');
 assert.throws(()=>m.publicationToken(a,'PATCH','mathgraph-check[bot]'),/APP_TOKEN_REQUIRED/);
 assert.throws(()=>m.publicationAuth({GITHUB_TOKEN:'actions-token-for-read',MATHGRAPH_APP_TOKEN:'wrong-app-token',MATHGRAPH_APP_SLUG:'someone-else'}),/APP_IDENTITY/);
 assert.throws(()=>m.publicationToken(app,'PATCH','someone'),/AUTHOR_REFUSED/);
});
test('App progress is resumed only by the selected bot and receipts name the publisher',()=>{
 const args={command:'fix',sha:'a'.repeat(40),runId:12,botLogin:'mathgraph-check[bot]'};
 const body=m.demoProgress(args),c={user:{login:'mathgraph-check[bot]'},body};
 assert.equal(m.ownsDemoProgress(c,args),true);assert.equal(m.ownsDemoProgress(c,{...args,botLogin:'github-actions[bot]'}),false);
 assert.match(m.demoComment({...args,native:{status:'ORIGINAL_TARGET_VERIFIED',axioms:['propext']}}),/as `mathgraph-check\[bot\]`/);
});
test('withdrawal preserves authorship when old Actions and new App results coexist',async()=>{
 const root='/repos/metalogiclabs/mathgraph',old='a'.repeat(40),head='b'.repeat(40),authors=[];
 const api=async(path,options={})=>{
  if(path.endsWith('/pulls/1'))return {head:{sha:head}};
  if(path.includes('/comments?'))return ['github-actions[bot]','mathgraph-check[bot]','stranger'].map((login,i)=>({id:i+1,user:{login},body:'<!-- mathgraph-actions-demo-v1:1 -->\nRevision: `'+old+'`'}));
  authors.push(options.author);return {};
 };
 assert.equal(await m.withdrawDemoComments({api,root,number:1}),2);assert.deepEqual(authors,['github-actions[bot]','mathgraph-check[bot]']);
});
