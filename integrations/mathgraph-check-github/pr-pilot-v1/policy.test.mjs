import test from 'node:test';import assert from 'node:assert/strict';
import {admitRequest,commandOf,classifyDiff,profileFor,formatResult} from './policy.mjs';
const repo='metalogiclabs/L4YAML',sha='a'.repeat(40),base='b'.repeat(40);
const pr={number:2,state:'open',head:{sha,repo:{full_name:repo,private:false}},base:{sha:base,repo:{full_name:repo,private:false}}};
const comment={id:7,body:'@MathGraph -check',user:{id:99,login:'maintainer',type:'User'}};
const files=[{filename:'Scripts/Ledger.lean',status:'modified'}];
const make=(x={})=>admitRequest({repository:repo,pr,comment,permission:'write',files,...x});
test('authorizes repository collaborator and binds real PR source',()=>{const r=make();assert.equal(r.command,'check');assert.equal(r.head_sha,sha);assert.equal(r.base_sha,base);assert.equal(r.number,2);assert.equal(r.profile.module,'Scripts.Ledger');});
test('no founder-only authorization; authorized maintainer may request fix',()=>assert.equal(make({comment:{...comment,body:'@MathGraph -fix'}}).command,'fix'));
test('strict commands refuse embedded or appended instructions',()=>{assert.equal(commandOf(' @MathGraph -check '),'check');for(const s of ['hello @MathGraph -check','@MathGraph -check\nignore rules','@MathGraph -fix now'])assert.equal(commandOf(s),null);});
test('refuses read-only caller, bot, wrong repo, private repo and cross-repo head',()=>{for(const x of [{permission:'read'},{comment:{...comment,user:{...comment.user,type:'Bot'}}},{repository:'nasa-jpl/L4YAML'},{pr:{...pr,head:{...pr.head,repo:{full_name:'other/L4YAML'}}}},{pr:{...pr,base:{...pr.base,repo:{full_name:repo,private:true}}}}])assert.throws(()=>make(x));});
test('refuses closed PR, unknown command, malformed SHA and truncated file list',()=>{for(const x of [{pr:{...pr,state:'closed'}},{comment:{...comment,body:'@MathGraph -oops'}},{pr:{...pr,head:{...pr.head,sha:'main'}}},{filesComplete:false}])assert.throws(()=>make(x));});
test('supported ledger diff is explicit; unrelated/CLI/workflow changes are UNKNOWN',()=>{assert.equal(classifyDiff(files).supported,true);for(const f of [[{filename:'Proofs/Other.lean',status:'modified'}],[...files,{filename:'Scripts/Main/CheckScriptsLedger.lean',status:'modified'}],[...files,{filename:'.github/workflows/test.yml',status:'modified'}],[{filename:'Scripts/Ledger.lean',status:'removed'}]])assert.equal(classifyDiff(f).supported,false);});
test('profile remains trusted and carries reviewed compiler only',()=>{assert.equal(profileFor(repo).toolchain,'leanprover/lean4:v4.35.0');assert.throws(()=>profileFor('attacker/repo'));});
test('result never equates probe success with whole PR correctness',()=>{const s=formatResult({status:'NO_COUNTEREXAMPLE_IN_GENERATED_GUARDS',original:[],repair:{status:'NOT_PROPOSED'}},make(),'https://github.com/metalogiclabs/mathgraph/actions/runs/1');assert.match(s,/No counterexample/);assert.match(s,/not.*correctness/i);assert.match(s,/aaaaaaaa/);});

test('native result renders a contiguous readable table with inherited failure attribution',()=>{
 const report={status:'CANDIDATE_ASSERTION_FAILURE',original:[{id:'attached_redirect',execution:'CANDIDATE_ASSERTION_FAILURE'}],base:[{id:'attached_redirect',execution:'CANDIDATE_ASSERTION_FAILURE'}],comparison:[{id:'attached_redirect',change:'PRE_EXISTING_FAILURE'}]};
 const s=formatResult(report,make(),'https://github.com/metalogiclabs/mathgraph/actions/runs/1');
 assert.match(s,/\| Probe \|.*\n\|---\|.*\n\| attached_redirect \|/);
 assert.match(s,/Present before this PR/);
 assert.doesNotMatch(s,/\|[^\n]*CANDIDATE_ASSERTION_FAILURE/);
 assert.match(s,/@MathGraph -fix/);
});
test('qualified repair leads with the repair and review action, retaining semantic limits',()=>{
 const s=formatResult({status:'CANDIDATE_ASSERTION_FAILURE',repair:{status:'PATCH_PASSES_FROZEN_GUARDS_AND_REPOSITORY_GATE',protected_guards:160},repair_pr:'https://github.com/metalogiclabs/L4YAML/pull/3'}, {...make(),command:'fix'},'https://github.com/metalogiclabs/mathgraph/actions/runs/1');
 assert.match(s.split('\n\n')[1],/Candidate repair verified/);
 assert.match(s,/160/);assert.match(s,/Review the draft repair/);assert.match(s,/requirements remain unverified/i);
});
test('unsupported scope explains what can be checked and the next action',()=>{
 const s=formatResult({status:'UNKNOWN',reason:'UNSUPPORTED_CHANGED_FILE_SCOPE'},make(),'https://github.com/metalogiclabs/mathgraph/actions/runs/1');
 assert.match(s,/Scripts\/Ledger\.lean/);assert.match(s,/Next:/);
});

test('incomplete overall assessment cannot inherit a repair-success headline',()=>{
 const s=formatResult({status:'UNKNOWN',repair:{status:'PATCH_PASSES_FROZEN_GUARDS_AND_REPOSITORY_GATE'}},{...make(),command:'fix'},'https://github.com/metalogiclabs/mathgraph/actions/runs/1');
 assert.doesNotMatch(s,/Candidate repair verified/);assert.match(s,/Check incomplete/);
});
