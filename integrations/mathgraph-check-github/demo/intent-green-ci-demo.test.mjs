import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,readFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {buildSyntheticDemo,writeSyntheticDemo} from './intent-green-ci-demo.mjs';
test('green agent happy-path tests do not establish an independent user requirement',()=>{
 const d=buildSyntheticDemo();
 assert.equal(d.demo_only,true);
 assert.equal(d.agent_tests,'GREEN_HAPPY_PATH_ONLY');
 assert.equal(d.report.status,'BLOCKED');
 assert.equal(d.report.intent_verification,'NOT_ESTABLISHED');
 assert.equal(d.report.results[0].probes[0].status,'BLOCKED');
 assert.equal(d.witness.observed.status,'REFUNDED');
 assert.equal(d.witness.expected.status,'DENIED_ALREADY_REFUNDED');
});
test('read-only HTML and JSON synthetic outputs are deterministic and labeled',()=>{
 const out=mkdtempSync(join(tmpdir(),'mg-intent-demo-'));
 try{
  const a=writeSyntheticDemo(out);
  const j=JSON.parse(readFileSync(join(out,'report.json'),'utf8'));
  const html=readFileSync(join(out,'report.html'),'utf8');
  assert.equal(j.report.contract_sha256,a.report.contract_sha256);
  assert.match(html,/SYNTHETIC DEMO/);
  assert.match(html,/Independent requirement: FAILED/);
  assert.match(html,/NOT ESTABLISHED/);
  assert.match(html,/No merge authorization/);
 }finally{rmSync(out,{recursive:true,force:true});}
});
