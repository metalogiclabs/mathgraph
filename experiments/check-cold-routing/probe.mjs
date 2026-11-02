// Qualification harness only. Imports the unchanged production controller.
import {readFile,writeFile,mkdir,mkdtemp,rm} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import assert from 'node:assert/strict';
import {selectDemoCase} from '../../integrations/mathgraph-check-github/mention-demo-cases-v1.mjs';
import {runMention} from '../../integrations/mathgraph-check-github/mention-agent-v1.mjs';
const root=new URL('./',import.meta.url);
const protocol=JSON.parse(await readFile(new URL('protocol.json',root),'utf8'));
const snapshots=JSON.parse(await readFile(new URL('snapshots.json',root),'utf8'));
assert.equal(protocol.product_changes_permitted,false);
const controller=protocol.controller_sha;
const paths=['mention-demo-cases-v1.mjs','mention-actions-demo-v1.mjs','mention-agent-v1.mjs','mention-group-native-v1.mjs','mention-fresh-proof-v1.mjs'];
const identities=[];
for(const name of paths){
 const path='integrations/mathgraph-check-github/'+name;
 const actual=await readFile(path),frozen=execFileSync('git',['show',controller+':'+path]);
 assert.deepEqual(actual,frozen,'FROZEN_PRODUCT_SOURCE_CHANGED');
 identities.push({path,controller_sha:controller,sha256:createHash('sha256').update(actual).digest('hex')});
}
// Positive controls distinguish unsupported coverage from a broken import/router.
const controls=[];
for(const path of ['mathgraph-demo/ReverseLength.lean','mathgraph-demo/ArtinGenerators.lean','mathgraph-demo/GroupIdentity.lean']){
 const adapter=selectDemoCase([{filename:path}]);assert.equal(adapter.accepts(adapter.brokenSource),true);
 controls.push({path,adapter:adapter.id,status:'ADMITTED_REGISTERED_CONTROL'});
}
const rows=[];
for(const frozen of protocol.subjects){
 const s=snapshots.find(x=>x.repository===frozen.repository);assert.ok(s);
 for(const key of ['pr','base_sha','head_sha'])assert.equal(s[key],frozen[key]);
 let state,reason;
 try{const c=selectDemoCase(s.files);state='ADMITTED';reason=c.id;}
 catch(e){state='UNSUPPORTED';reason=e.message;assert.equal(reason,'DEMO_CASE_UNSUPPORTED_OR_AMBIGUOUS');}
 rows.push({repository:s.repository,pr:s.pr,base_sha:s.base_sha,head_sha:s.head_sha,changed_files:s.files.length,state,reason,discovery:'NOT_ATTEMPTED',repair:'NOT_ATTEMPTED',ground_truth:'UNKNOWN'});
}
// Separate library capability test: do not simulate a deployed webhook or a
// genuine model/native investigation. The generic -fix route must tell us if it
// is not configured, without pretending to have proposed or verified a repair.
const stateDir=await mkdtemp(join(tmpdir(),'mathgraph-cold-fix-'));
let modelCalls=0,nativeCalls=0,snapshotsRead=0,published=0;
let fix;
try{
 const policy={repositories:['metalogiclabs/mathgraph'],userIds:[32909488],handle:'MathGraph',model:'gpt-6.1-sol',inputCentsPerMillion:500,outputCentsPerMillion:2000,maxOutputTokens:4096,maxInputBytes:8000,jobCapCents:25,totalCapCents:25};
 const event={action:'created',repository:{full_name:'metalogiclabs/mathgraph'},sender:{id:32909488,type:'User'},issue:{number:1,pull_request:{}},comment:{id:1,body:'@MathGraph -fix',user:{id:32909488,type:'User'}}};
 fix=await runMention(event,{policy,stateDir,github:{publish:async()=>{published++;return 1;},snapshot:async()=>{snapshotsRead++;throw Error('UNEXPECTED_SNAPSHOT');}},model:async()=>{modelCalls++;throw Error('UNEXPECTED_MODEL');},observeProof:async()=>{nativeCalls++;throw Error('UNEXPECTED_NATIVE');}});
 assert.equal(fix.state,'REPAIR_NOT_CONFIGURED');assert.equal(modelCalls,0);assert.equal(nativeCalls,0);assert.equal(snapshotsRead,0);assert.equal(published,1);
}finally{await rm(stateDir,{recursive:true,force:true});}
const report={schema:'mathgraph.cold-admission-result.v1',controller_sha:controller,verifier_sha:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),subject_count:rows.length,admitted:rows.filter(x=>x.state==='ADMITTED').length,unsupported:rows.filter(x=>x.state==='UNSUPPORTED').length,rows,registered_controls:controls,generic_fix_library:{state:fix.state,model_calls:modelCalls,native_calls:nativeCalls,snapshot_reads:snapshotsRead,transport:'TEST_DOUBLE_NOT_LIVE_WEBHOOK'},source_identities:identities,boundary:'Unchanged production source admission, assuming an eligible first-party carrier. External repos are independently excluded by the live allowlist. No bug labels acquired, no semantic accuracy measurement, no model/native investigation and no live command posted.'};
await mkdir('cold-routing-results',{recursive:true});
await writeFile('cold-routing-results/REPORT.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
