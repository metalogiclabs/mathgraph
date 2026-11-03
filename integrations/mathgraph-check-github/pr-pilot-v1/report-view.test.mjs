import test from 'node:test';import assert from 'node:assert/strict';import {reportView} from './report-view.mjs';
const request={repository:'metalogiclabs/L4YAML',number:6,base_sha:'a'.repeat(40),head_sha:'b'.repeat(40),command:'check',profile:{mode:'OWNED_FORK_CLI_PARITY',cli_profile:'traceof',claim_profile:'empty-tail-v1'}};
const assessment={status:'CLI_BEHAVIOR_DIFFERENCE',counts:{PARITY:4,DIFFERENCE:3},cases:[],claim:{status:'SUPPORTED',proof_assumptions:{strong_consumer:['propext']}}};
test('shared view separates supported capability from observed CLI differences',()=>{const v=reportView(assessment,request);assert.equal(v.title,'Declared capability supported');assert.equal(v.capabilities.find(x=>x.id==='behavior').status,'CLI_BEHAVIOR_DIFFERENCE');assert.equal(v.capabilities.find(x=>x.id==='claim').status,'SUPPORTED');assert.match(v.assumptions,/propext/);assert.match(v.scope,/UNKNOWN/);});
test('missing claim and source withdrawal cannot become supported',()=>{assert.equal(reportView({...assessment,claim:{status:'UNKNOWN',reason:'INCOMPLETE'}},request).capabilities.find(x=>x.id==='claim').status,'UNKNOWN');const v=reportView({...assessment,status:'STALE'},request);assert.doesNotMatch(v.title,/supported/);assert.equal(v.findings.length,0);});
test('fix remains available only for admitted qualified Ledger failure',()=>{assert.equal(reportView(assessment,request).fix.available,false);const r={...request,profile:{mode:'OWNED_FORK_PR_PILOT'}};assert.equal(reportView({status:'CANDIDATE_ASSERTION_FAILURE',expectations:{status:'ADMITTED',repair_eligible:true}},r).fix.available,true);assert.equal(reportView({status:'CANDIDATE_ASSERTION_FAILURE'},r).fix.available,false);assert.equal(reportView({status:'UNKNOWN'},r).fix.available,false);});
test('unsupported fix explains its boundary and incomplete source cannot offer repair',()=>{const r={...request,command:'fix',profile:{mode:'OWNED_FORK_PR_PILOT'}};assert.equal(reportView({status:'UNKNOWN',reason:'UNSUPPORTED_CHANGED_FILE_SCOPE'},r).title,'Repair unavailable for this scope');const v=reportView({status:'CANDIDATE_ASSERTION_FAILURE',head_complete:false,repair:{status:'PATCH_PASSES_FROZEN_GUARDS_AND_REPOSITORY_GATE'}},r);assert.equal(v.fix.available,false);assert.equal(v.title,'Repair incomplete');});
test('unadmitted expectations cannot offer fix or inherit verified repair title',()=>{
 const r={...request,command:'fix',profile:{mode:'OWNED_FORK_PR_PILOT'}};
 const v=reportView({status:'CANDIDATE_ASSERTION_FAILURE',expectations:{status:'UNKNOWN',repair_eligible:false},repair:{status:'PATCH_PASSES_FROZEN_GUARDS_AND_REPOSITORY_GATE'}},r);
 assert.equal(v.fix.available,false);assert.equal(v.title,'Expectation review required');assert.doesNotMatch(v.next,/@MathGraph -fix/);
});
test('admitted expectation failure offers bounded repair and exposes admission capability',()=>{
 const r={...request,profile:{mode:'OWNED_FORK_PR_PILOT'}};
 const v=reportView({status:'CANDIDATE_ASSERTION_FAILURE',expectations:{status:'ADMITTED',repair_eligible:true,probes:[]}},r);
 assert.equal(v.fix.available,true);assert.equal(v.title,'Reviewed expectation fails');assert.equal(v.capabilities.find(c=>c.id==='expectations').status,'ADMITTED');
});
test('repair summary leads with the repaired failure and retains the paired observations',()=>{
 const r={...request,command:'fix',profile:{mode:'OWNED_FORK_PR_PILOT'}};
 const v=reportView({status:'CANDIDATE_ASSERTION_FAILURE',expectations:{status:'ADMITTED',repair_eligible:true,probes:[{id:'preserved',status:'ADMITTED'},{id:'repaired',status:'ADMITTED'}]},original:[{id:'preserved',execution:'GUARD_PASSED'},{id:'repaired',execution:'CANDIDATE_ASSERTION_FAILURE'}],repair:{status:'PATCH_PASSES_FROZEN_GUARDS_AND_REPOSITORY_GATE',repaired:[{id:'repaired',execution:'GUARD_PASSED'}],withdrawn:[{id:'repaired',execution:'CANDIDATE_ASSERTION_FAILURE'}]}},r);
 assert.equal(v.findings[0].title,'repaired');assert.match(v.findings[0].evidence,/Candidate: GUARD_PASSED/);assert.match(v.findings[0].evidence,/Withdrawn:/);
});
