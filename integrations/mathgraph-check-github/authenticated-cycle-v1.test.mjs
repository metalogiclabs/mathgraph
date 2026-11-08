import test from "node:test";
import assert from "node:assert/strict";
import {githubSnapshot,compareSnapshots} from "./authenticated-cycle-v1.mjs";
import {digestProjectionClaim} from './projection-claim-v1.mjs';
import {hashFiniteUniverse} from './finite-warrant-quotient-v1.mjs';
const a="a".repeat(40),b="b".repeat(40);
function mock({runs,head=a,status=200}={}){
 const got=[];
 const fetcher=async (url,opts)=>{
  got.push(url);
  if(status!==200)return {ok:false,status};
  const data=url.includes("/pulls/")?
   {base:{sha:b,repo:{full_name:"metalogiclabs/mathgraph"}},head:{sha:head,repo:{full_name:"metalogiclabs/mathgraph"}}}:
   {total_count:runs.length,check_runs:runs};
  return {ok:true,json:async()=>data};
 };
 return {fetcher,got};
}
function run(id,name,conclusion="success",status="completed",sha=a){
 return {id,name,head_sha:sha,status,conclusion,started_at:"2026-10-23T00:00:00Z",app:{slug:"github-actions"}};
}
const args={repository:"metalogiclabs/mathgraph",pr:195,token:"not-real-but-long"};
function projection(){
 const claim={id:'required-behavior',statement:'The required behavior holds',
   observation:'green CI',universe:{schema:'mathgraph.finite-warrant-quotient.v1',
     scope:'authenticated-pr-witness',rows:[
       {id:'compliant',source_sha:a,alpha_key:'CI=green',protected_status:'OBSERVED'},
       {id:'violation',source_sha:a,alpha_key:'CI=green',protected_status:'BLOCKED'},
     ]}};
 const subject={repository:args.repository,pr:args.pr,base_sha:b,head_sha:a};
 const authority={allowedRepositories:[args.repository],expectedHeadSha:a,
   expectedContractSha256:digestProjectionClaim(subject,claim),
   expectedUniverseSha256:hashFiniteUniverse(claim.universe),allowedSourceShas:[a]};
 return {claim,authority};
}
test("authenticated GitHub readback yields observation but not proof",async()=>{
 const m=mock({runs:[run(1,"native")]});
 const r=await githubSnapshot({...args,fetcher:m.fetcher});
 assert.equal(r.result.status,"OBSERVED");assert.equal(r.result.permission,"ADVISORY_ONLY");
 assert.equal(r.result.subject.head_sha,a);assert.equal(m.got.length,2);
});
test("untrusted extra-head checks are ignored",async()=>{
 const m=mock({runs:[run(1,"native","success","completed",b)]});
 await assert.rejects(githubSnapshot({...args,fetcher:m.fetcher}),/NO_INDEPENDENT_CHECKS/);
});
test("pending latest rerun does not reuse old green result",async()=>{
 const older=run(1,"native");older.started_at="2026-10-22T00:00:00Z";
 const m=mock({runs:[older,run(2,"native","success","in_progress")]});
 const r=await githubSnapshot({...args,fetcher:m.fetcher});
 assert.equal(r.result.status,"UNKNOWN");
});
test("checker cannot self-certify",async()=>{
 const m=mock({runs:[{...run(1,"MathGraph Check / evidence scope"),app:{slug:"mathgraph-check"}}]});
 await assert.rejects(githubSnapshot({...args,fetcher:m.fetcher}),/NO_INDEPENDENT_CHECKS/);
});
test("failed run blocks only its exact obligation",async()=>{
 const m=mock({runs:[run(1,"native","failure"),run(2,"lint")]});
 const r=await githubSnapshot({...args,fetcher:m.fetcher});
 assert.equal(r.result.results.find(x=>x.id==="native").status,"BLOCKED");
 assert.equal(r.result.results.find(x=>x.id==="lint").status,"OBSERVED");
});
test("invalid PR sha rejected",async()=>{
 const m=mock({runs:[run(1,"native")],head:"wrong"});
 await assert.rejects(githubSnapshot({...args,fetcher:m.fetcher}),/PR_SOURCE_UNKNOWN/);
});
test("API denial cannot produce a warrant",async()=>{
 const m=mock({runs:[],status:403});
 await assert.rejects(githubSnapshot({...args,fetcher:m.fetcher}),/GITHUB_HTTP_403/);
});
test("change triggers withdrawal; untouched evidence remains",async()=>{
 const first=await githubSnapshot({...args,fetcher:mock({runs:[run(1,"native"),run(2,"lint")]}).fetcher});
 const after=await githubSnapshot({...args,fetcher:mock({runs:[run(1,"native","failure"),run(2,"lint")]}).fetcher});
 const result=compareSnapshots(first,after,{changedEvidenceIds:["github-check:1"]});
 assert.equal(result.transitions.find(x=>x.claim==="native").to,"BLOCKED");
 assert.equal(result.transitions.find(x=>x.claim==="lint").to,"OBSERVED");
});
test("after failure, fresh green result needs requalification",async()=>{
 const before=await githubSnapshot({...args,fetcher:mock({runs:[run(1,"native","failure")]}).fetcher});
 const after=await githubSnapshot({...args,fetcher:mock({runs:[run(1,"native")]}).fetcher});
 const result=compareSnapshots(before,after,{changedEvidenceIds:["github-check:1"]});
 assert.equal(result.transitions[0].to,"UNKNOWN");
});
test('qualified projection witness enters live Check and only permitted Resolve proposals',async()=>{
 const p=projection(),m=mock({runs:[run(1,'native')]});
 const r=await githubSnapshot({...args,fetcher:m.fetcher,projectionClaim:p.claim,
  projectionAuthority:p.authority,plans:{'required-behavior':[
    {id:'auto-fix',cost:0,allowed:false,source_authoritative:true},
    {id:'refine-observation',cost:2,allowed:true,source_authoritative:true}]}});
 assert.equal(r.result.status,'BLOCKED');
 assert.equal(r.result.results.find(x=>x.id==='required-behavior').status,'BLOCKED');
 assert.equal(r.projection.terminal_form,'NAMED_OBSTRUCTION');
 assert.equal(r.plans.find(x=>x.claim==='required-behavior').next.experiment,'refine-observation');
 assert.equal(r.plans.find(x=>x.claim==='required-behavior').next.kind,'PROPOSAL_NOT_EXECUTED');
 assert.equal(r.result.permission,'ADVISORY_ONLY');
});
test('untrusted projection does not inherit a semantic verdict from green CI',async()=>{
 const p=projection();
 const r=await githubSnapshot({...args,fetcher:mock({runs:[run(1,'native')]}).fetcher,
   projectionClaim:p.claim});
 assert.equal(r.result.results.find(x=>x.id==='required-behavior').status,'UNKNOWN');
 assert.equal(r.result.status,'UNKNOWN');
});
test('changing PR head withdraws projection and preserves monitor lineage',async()=>{
 const p=projection(),before=await githubSnapshot({...args,
  fetcher:mock({runs:[run(1,'native')]}).fetcher,
  projectionClaim:p.claim,projectionAuthority:p.authority});
 const c='c'.repeat(40),after=await githubSnapshot({...args,
  fetcher:mock({head:c,runs:[run(2,'native','success','completed',c)]}).fetcher,
  projectionClaim:p.claim,projectionAuthority:p.authority});
 assert.equal(after.projection.status,'UNKNOWN');
 const transition=compareSnapshots(before,after);
 assert.equal(transition.transitions.find(x=>x.claim==='required-behavior').from,'BLOCKED');
 assert.equal(transition.transitions.find(x=>x.claim==='required-behavior').to,'UNKNOWN');
});
test('qualified witness may explain a PR even when it has no other check runs',async()=>{
 const p=projection();
 const r=await githubSnapshot({...args,fetcher:mock({runs:[]}).fetcher,
  projectionClaim:p.claim,projectionAuthority:p.authority});
 assert.equal(r.result.status,'BLOCKED');
 assert.equal(r.input.evidence.length,0);
});
test('an old or in-band projection cannot replace missing independent check runs',async()=>{
 const p=projection();p.claim.universe.rows[1].source_sha=b;
 await assert.rejects(githubSnapshot({...args,fetcher:mock({runs:[]}).fetcher,
  projectionClaim:p.claim,projectionAuthority:p.authority}),/NO_INDEPENDENT_CHECKS/);
});
