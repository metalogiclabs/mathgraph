import test from 'node:test';import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {inspectNative,planFor} from './binding-native.mjs';
import {renderProbe} from '../../integrations/mathgraph-check-github/lean-investigator-v1/contracts.mjs';
const hash=s=>createHash('sha256').update(s).digest('hex');
function fixture(){
 const source='namespace Example\ndef f : Bool := false\n#guard true\nend Example\n',content=source.replace(':= false',':= true'),cli='cli';
 const policy={subject:{repository:'metalogiclabs/L4YAML',revision:'a'.repeat(40),path:'Scripts/Ledger.lean',sha256:hash(source)},toolchain:'leanprover/lean4:v4.35.0',cli_sha256:hash(cli),relation:'finite test',proposals:[{id:'case_a',expression:'true'}],patch:{summary:'candidate',edits:[{old:':= false',new:':= true'}]}};
 const snapshot={...policy.subject,head_sha:policy.subject.revision,source,source_sha256:hash(source),cli_source:cli,module:'Scripts.Ledger',namespace:'Scripts.Ledger',toolchain:policy.toolchain};
 const context={verifier_sha:'b'.repeat(40),run_id:42,attempt:1},plan=planFor(policy),state={test_digest:hash(JSON.stringify(plan.tests))};
 const good={exit_code:0,guard_false:false,other_errors:false},bad={exit_code:1,guard_false:true,other_errors:false};
 const arm=(s,p=bad)=>({source_sha256:hash(s),build_exit:0,repository_gate_exit:0,controls:{pass:good,fail:bad},probes:[{id:'case_a',...p,test_file_sha256:hash(renderProbe(snapshot,'true'))}]});
 const common={context,source_sha:snapshot.head_sha,test_digest:state.test_digest};
 return {policy,snapshot,plan,state,context,native:{...common,arm:arm(source)},repair:{...common,patched_sha256:hash(content),original:arm(source),repaired:arm(content,good),withdrawn:arm(source)},patch:{content,patched_sha256:hash(content)}};
}
test('valid source/plan/context/paired arms remain separately inspectable',()=>{const r=inspectNative(fixture());assert.equal(r.complete,true);assert.equal(r.source_guard_count,1);assert.equal(r.initial.rows[0].execution,'CANDIDATE_ASSERTION_FAILURE');});
for(const [name,mutate] of [
 ['source',x=>x.snapshot.source+='\n'],['plan',x=>x.plan.tests[0].expression='false'],
 ['native context',x=>x.native.context={...x.context,run_id:43}],['repair context',x=>x.repair.context={...x.context,attempt:2}],
 ['patch',x=>x.patch.content+='\n'],['CLI',x=>x.snapshot.cli_source+='\n'],
 ['toolchain',x=>x.snapshot.toolchain='different']
])test(name+' identity mismatch cannot pass',()=>{const x=fixture();mutate(x);assert.throws(()=>inspectNative(x));});
for(const [name,mutate] of [
 ['build',x=>x.repair.repaired.build_exit=1],['gate',x=>x.repair.repaired.repository_gate_exit=1],
 ['controls',x=>x.repair.repaired.controls.fail.exit_code=0],
 ['probe bytes',x=>x.repair.repaired.probes[0].test_file_sha256='0'.repeat(64)],
 ['extra probe',x=>x.repair.repaired.probes.push({...x.repair.repaired.probes[0],id:'extra'})]
])test(name+' failure makes paired evidence incomplete',()=>{const x=fixture();mutate(x);assert.equal(inspectNative(x).complete,false);});
