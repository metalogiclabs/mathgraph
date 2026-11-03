import test from 'node:test';import assert from 'node:assert/strict';
import {admitRequest,formatResult} from './policy.mjs';import {logicalIdentity} from './lifecycle.mjs';import {reportView} from './report-view.mjs';
const repository='metalogiclabs/L4YAML',side=sha=>({sha,repo:{full_name:repository,private:false}}),pr={number:28,state:'open',draft:true,head:side('a'.repeat(40)),base:side('b'.repeat(40)),user:{id:32909488,type:'User'},body:'Source qualification: https://github.com/metalogiclabs/mathgraph/actions/runs/41713506095'};
const make=p=>admitRequest({repository,pr:p,files:[{filename:'Scripts/Ledger.lean',status:'modified'}],permission:'admin',comment:{id:9,body:'@MathGraph -check',user:{id:32909488,login:'heathsanchez',type:'User'}}});
test('owner research draft is only a producer locator, not an admitted expectation set',()=>{const r=make(pr);assert.equal(r.profile.expectation_candidate,true);assert.equal(r.profile.expectation_profile,undefined);assert.equal(r.profile.report_version,'expectations-v2-complete');assert.match(logicalIdentity(r),/:report:expectations-v2-complete/);});
test('seed requests select v2 while v1 historical identity is preserved',()=>{const r=make({...pr,head:side('fba155bf31918f9b03394ae9bfb8cd17c91ecfb8')});assert.equal(r.profile.expectation_profile,'ledger-shell-v2');assert.match(logicalIdentity({...r,profile:{...r.profile,report_version:'expectations-v1'}}),/:report:expectations-v1/);});
test('v2 report states actual requirement and input counts',()=>{const r=make(pr),a={status:'NO_COUNTEREXAMPLE_IN_GENERATED_GUARDS',head_complete:true,expectations:{status:'ADMITTED',repair_eligible:true,expectation_set:'ledger-shell-v2',requirement_count:3,input_count:5,probes:[]}};const v=reportView(a,r);assert.match(v.summary,/3.*5/);assert.match(v.scope,/5 finite shell inputs/);assert.doesNotMatch(v.summary,/Two operator/);});
test('GitHub finding preserves the exact redirection symbol safely',()=>{
 const r=make(pr),a={status:'CANDIDATE_ASSERTION_FAILURE',original:[{id:'leading_output_ok',execution:'CANDIDATE_ASSERTION_FAILURE',hypothesis:'Leading redirect'}],expectations:{status:'ADMITTED',repair_eligible:true,expectation_set:'ledger-shell-v2',probes:[{id:'leading_output_ok',status:'ADMITTED',input:'>out python3 scripts/a.py',expectation:'scripts/a.py'}]}};
 const s=formatResult(a,r,'https://github.com/metalogiclabs/mathgraph/actions/runs/1');assert.match(s,/&gt;out python3 scripts\/a.py/);assert.doesNotMatch(s,/Input:  out/);
});
test('passed reviewed checks recommend review rather than missing diagnostics',()=>{
 const a={status:'NO_COUNTEREXAMPLE_IN_GENERATED_GUARDS',expectations:{status:'ADMITTED',repair_eligible:true,expectation_set:'ledger-shell-v2'}};assert.match(reportView(a,make(pr)).next,/Review the diff/);assert.doesNotMatch(reportView(a,make(pr)).next,/diagnostic/);
});
test('a resolved requirement leads a passing PR report ahead of preserved controls',()=>{
 const a={status:'NO_COUNTEREXAMPLE_IN_GENERATED_GUARDS',original:[{id:'attached_ok',execution:'GUARD_PASSED'},{id:'leading_output_ok',execution:'GUARD_PASSED'}],comparison:[{id:'attached_ok',change:'BOTH_PASS'},{id:'leading_output_ok',change:'RESOLVED_FAILURE'}],expectations:{status:'ADMITTED',repair_eligible:true,expectation_set:'ledger-shell-v2',probes:[{id:'attached_ok',label:'Preserved control',status:'ADMITTED'},{id:'leading_output_ok',label:'Leading redirect resolved',status:'ADMITTED'}]}};
 assert.equal(reportView(a,make(pr)).findings[0].title,'Leading redirect resolved');
});
