import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,readFile,writeFile,cp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {PER_CASE_CASES,PER_CASE_METHOD,PER_CASE_CORPUS_SHA,assessPerCaseArm,
  renderedAgreement,runPerCase} from './per-case.mjs';

const sha=x=>createHash('sha256').update(x).digest('hex');
const source={source_sha256:'a'.repeat(64)};
const presets=['unlimited','default','strict','permissive','safe_tags'];
function qualified(){return {source_sha256:source.source_sha256,corpus_sha256:PER_CASE_CORPUS_SHA,
  schema_family:'per-case-acceptance-v2',build_exit:0,observer_exit:0,source_preserved:true,
  inputs_preserved:true,observer_sha256:'b'.repeat(64),
  controls:{pass:{exit:0,guard_false:false,other_errors:false},fail:{exit:1,guard_false:true,other_errors:false}},
  observations:PER_CASE_CASES.map(c=>({id:c.id,agreement:c.expected.agreement,decoded_ok:c.expected.agreement,
    readback_agreement:c.expected.agreement,
    preset_agreement:c.expected.preset_agreement.map(p=>({...p,line:'native observation'})),
    verdict:'native verdict',serialized:'{}',html:c.expected.agreement?
      '<html><p class="match">Per-case acceptance agrees</p></html>':
      '<html><p class="mismatch">Insufficient or inconsistent evidence</p></html>'}))};}

test('the retained method has five literal expectations, with agreement and rejection controls',()=>{
  assert.equal(PER_CASE_METHOD,'suite-per-case-agreement-v1');
  assert.deepEqual(PER_CASE_CASES.map(c=>[c.id,c.expected.agreement]),[
    ['identical_outcomes',true],['reordered_same_cases',true],['different_totals',false],
    ['equal_totals_swapped_outcomes',false],['single_preset_swapped_outcomes',false]]);
});

test('independent keyed reference qualifies every literal expectation and corpus identity',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'mathgraph-per-case-reference-'));
  try{
    const out=join(dir,'reference.json');
    const p=spawnSync('python3',[new URL('./per-case-reference.py',import.meta.url).pathname,out],{encoding:'utf8'});
    assert.equal(p.status,0,p.stderr);
    const r=JSON.parse(await readFile(out,'utf8'));
    assert.equal(r.corpus_sha256,PER_CASE_CORPUS_SHA);
    assert.equal(r.runner_sha256,sha(await readFile(new URL('./per-case-reference.py',import.meta.url))));
    assert.deepEqual(r.records,PER_CASE_CASES.map(c=>({id:c.id,observed:c.expected})));
  }finally{await rm(dir,{recursive:true,force:true});}
});

test('the independent reference refuses an expectation weakened to accept swapped outcomes',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'mathgraph-per-case-mutation-'));
  try{
    await cp(new URL('./per-case-reference.py',import.meta.url),join(dir,'per-case-reference.py'));
    const corpus=structuredClone(PER_CASE_CASES);
    corpus.find(c=>c.id==='equal_totals_swapped_outcomes').expected.agreement=true;
    await writeFile(join(dir,'per-case-cases.json'),JSON.stringify(corpus));
    const p=spawnSync('python3',[join(dir,'per-case-reference.py'),join(dir,'result.json')],{encoding:'utf8'});
    assert.notEqual(p.status,0);
    assert.match(p.stderr,/REFERENCE_EXPECTATION_MISMATCH/);
    await assert.rejects(readFile(join(dir,'result.json')),/ENOENT/);
  }finally{await rm(dir,{recursive:true,force:true});}
});

test('native consumer and renderer must both agree with the independent requirement',()=>{
  const raw=qualified();
  assert.equal(assessPerCaseArm(raw,source).complete,true);
  assert.equal(assessPerCaseArm(raw,source).mismatches.length,0);
  const witness=raw.observations.find(c=>c.id==='equal_totals_swapped_outcomes');
  witness.agreement=true;
  witness.html='<html><p class="match">Per-case acceptance agrees</p></html>';
  const checked=assessPerCaseArm(raw,source);
  assert.equal(checked.complete,true);
  assert.deepEqual(checked.mismatches.map(c=>c.id),['equal_totals_swapped_outcomes']);
});

test('missing rows, changed sources, failed controls and malformed observer data remain UNKNOWN',()=>{
  for(const mutation of [
    r=>r.observations.pop(),r=>r.observations.push(r.observations[0]),
    r=>r.source_sha256='c'.repeat(64),r=>r.corpus_sha256='d'.repeat(64),
    r=>r.build_exit=1,r=>r.observer_exit=1,r=>r.source_preserved=false,
    r=>r.controls.fail.exit=0,r=>r.observations[0].agreement='true',
    r=>r.observations[0].preset_agreement.pop(),r=>r.observations[0].html='<p>unknown layout</p>'
  ]){
    const raw=qualified();mutation(raw);
    const result=assessPerCaseArm(raw,source);
    assert.equal(result.complete,false);
    assert.deepEqual(result.observations,[]);
    assert.deepEqual(result.mismatches,[]);
  }
});

test('HTML projection refuses missing, duplicated or conflicting terminal claims',()=>{
  assert.equal(renderedAgreement('<p class="summary match">agreement</p>','aggregate-counts-v1'),true);
  assert.equal(renderedAgreement('<p class="summary mismatch">mismatch</p>','aggregate-counts-v1'),false);
  assert.equal(renderedAgreement('<p class="match">agreement</p>','per-case-acceptance-v2'),true);
  for(const html of ['','<p class="match">yes</p><p class="match">again</p>',
    '<p class="match">yes</p><p class="mismatch">no</p>'])
    assert.throws(()=>renderedAgreement(html,'per-case-acceptance-v2'),/HTML_TERMINAL_STATUS_UNRECOGNIZED/);
});

test('commented, scripted and hidden agreement markup cannot qualify a rendered claim',()=>{
  for(const html of [
    '<html><body><!-- <p class="match">agreement</p> --></body></html>',
    '<html><body><script>const text = \'<p class="match">agreement</p>\';</script></body></html>',
    '<html><body><p class="match" hidden>agreement</p></body></html>',
    '<html><body hidden><p class="match">agreement</p></body></html>',
    '<html><head><style>.match { display: none }</style></head><body><p class="match">agreement</p></body></html>'
  ])assert.throws(()=>renderedAgreement(html,'per-case-acceptance-v2'),/HTML_TERMINAL_STATUS_UNRECOGNIZED/);
});

test('a wrong preset result is a discrepancy even when the overall rejection is unchanged',()=>{
  const raw=qualified();
  const row=raw.observations.find(c=>c.id==='single_preset_swapped_outcomes');
  row.preset_agreement=presets.map(p=>({preset:p,agreement:p!=='strict',line:'native observation'}));
  assert.equal(assessPerCaseArm(raw,source).mismatches.length,0);
  row.preset_agreement.find(p=>p.preset==='default').agreement=false;
  assert.deepEqual(assessPerCaseArm(raw,source).mismatches.map(c=>c.id),['single_preset_swapped_outcomes']);
});

test('an unavailable local Git source leaves a durable UNKNOWN result',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'mathgraph-per-case-source-'));
  try{
    const out=join(dir,'result');
    const {result,exit_code}=await runPerCase({repo:dir,base:'missing',head:'missing',out,lean:'lean',python:'python3',timeout:10});
    assert.equal(exit_code,2);assert.equal(result.status,'UNKNOWN');
    assert.match(result.reason,/REVISION_UNAVAILABLE/);
    assert.equal(JSON.parse(await readFile(join(out,'result.json'),'utf8')).status,'UNKNOWN');
  }finally{await rm(dir,{recursive:true,force:true});}
});
