import test from 'node:test';
import assert from 'node:assert/strict';
import {assessLedgerReceipt, ledgerCheck} from './adapter.mjs';
const a='a'.repeat(40),b='b'.repeat(40),v='c'.repeat(40);
const context={subjectRepository:'metalogiclabs/L4YAML',subjectHead:b,verifierHead:v,runId:123,authenticated:true};
const receipt=()=>({schema:'mathgraph.ledger-obligation.v1',subject:{repository:context.subjectRepository,base_sha:a,head_sha:b},verifier:{repository:'metalogiclabs/mathgraph',head_sha:v,toolchain:'leanprover/lean4:v4.35.0'},run:{id:123,attempt:1},cases:['clean','direct','no_bytecode','isolated','warning_option','heredoc_data','literal_backslashes'],arms:['original','repaired','withdrawn'].map(id=>({id,source_sha:id==='repaired'?b:a,guards_exit:id==='repaired'?0:1,rows:['clean','direct','no_bytecode','isolated','warning_option','heredoc_data','literal_backslashes'].map(name=>({id:name,oracle_exit:0,oracle_executed:!['clean','heredoc_data'].includes(name),gate_exit:['clean','heredoc_data'].includes(name)?0:(id==='repaired'||['direct','literal_backslashes'].includes(name)?1:0)})),repository_exits:id==='repaired'?[0,1,1,0]:[0,1,0,0],restored_clean:true}))});
const assess=r=>assessLedgerReceipt(r,context);
test('real protocol catches false green, accepts bounded repair, detects withdrawal',()=>{const r=assess(receipt());assert.equal(r.status,'PASS');assert.deepEqual(r.arms.map(x=>x.status),['FAIL','PASS','FAIL']);assert.equal(r.permission,'ADVISORY_ONLY');});
for(const [name,mutate] of [
 ['stale subject',r=>r.subject.head_sha=a],['wrong verifier',r=>r.verifier.head_sha=a],['wrong run',r=>r.run.id=124],['wrong toolchain',r=>r.verifier.toolchain='other'],['missing arm',r=>r.arms.pop()],['duplicate case',r=>r.arms[1].rows[1]=r.arms[1].rows[0]],['missing case',r=>r.arms[1].rows.pop()],['unknown gate error',r=>r.arms[1].rows[0].gate_exit=2],['oracle crash',r=>r.arms[1].rows[0].oracle_exit=1],['wrong source arm',r=>r.arms[1].source_sha=a],['unrestored tree',r=>r.arms[1].restored_clean=false],['changed frozen obligation',r=>r.cases.pop()]
])test(name+' cannot pass',()=>{const r=receipt();mutate(r);assert.equal(assess(r).status,'UNKNOWN');});
test('JSON cannot authenticate itself',()=>{const r=receipt();r.authenticated=true;assert.equal(assessLedgerReceipt(r,{...context,authenticated:false}).status,'UNKNOWN');});
test('green repaired gate with missed execution fails',()=>{const r=receipt();r.arms[1].rows.find(x=>x.id==='no_bytecode').gate_exit=0;assert.equal(assess(r).status,'FAIL');});
test('repair rejecting clean input fails',()=>{const r=receipt();r.arms[1].rows[0].gate_exit=1;assert.equal(assess(r).status,'FAIL');});
test('repair not passing regression guards fails',()=>{const r=receipt();r.arms[1].guards_exit=1;assert.equal(assess(r).status,'FAIL');});
test('red controls must actually fail before repair',()=>{const r=receipt();r.arms[0]=structuredClone(r.arms[1]);r.arms[0].id='original';r.arms[0].source_sha=a;assert.equal(assess(r).status,'FAIL');});
test('advisory GitHub Check distinguishes carrier and subject',()=>{const report=assess(receipt());const c=ledgerCheck(report,{carrierSha:v,runUrl:'https://github.com/metalogiclabs/mathgraph/actions/runs/123'});assert.equal(c.head_sha,v);assert.equal(c.conclusion,'neutral');assert.match(c.output.summary,/metalogiclabs\/L4YAML/);assert.match(c.output.summary,/bounded/i);});
