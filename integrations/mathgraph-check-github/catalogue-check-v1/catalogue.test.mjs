import test from 'node:test';
import assert from 'node:assert/strict';
import {CATALOGUE,PROFILES,coverageFor,validateCatalogue} from './catalogue.mjs';

const records=status=>Object.fromEntries(PROFILES.map(p=>[p.id,{status,reason:null,base:{cases:2,mismatches:0},head:{cases:2,mismatches:0}}]));

test('the public catalogue is self-contained without private drafting provenance',()=>{
 assert.equal(CATALOGUE.source.kind,'EDITORIAL_RESEARCH_CATALOGUE');
 assert.equal(CATALOGUE.source.path,'integrations/mathgraph-check-github/catalogue-check-v1/catalogue.json');
 assert.equal(CATALOGUE.source.executable_mapping,'catalogue.mjs');
 assert.equal('url' in CATALOGUE.source,false);
 assert.equal('manuscript_origin' in CATALOGUE.source,false);
 assert.doesNotMatch(JSON.stringify(CATALOGUE),/chatgpt\.com\/library|account_id=|libfile_/);
 assert.doesNotMatch(JSON.stringify(CATALOGUE.source),/https?:\/\/|58ddb19|074ddb7|\.md/);
});

test('the canonical 104 prompts keep stable IDs and candidate status',()=>{
 assert.equal(CATALOGUE.items.length,104);
 assert.deepEqual(CATALOGUE.items.map(x=>x.id),Array.from({length:104},(_,i)=>i+1));
 assert.equal(CATALOGUE.items[84].title,'Security and trust boundaries');
 assert.equal(CATALOGUE.items[95].title,'Unknown unknowns');
 assert.equal(CATALOGUE.items[3].title,'Values');
 assert.equal(CATALOGUE.items[103].title,'Assurance value');
 assert.ok(CATALOGUE.items.every(x=>x.lifecycle==='CANDIDATE_PROMPT'&&x.prompt.length>20));
 const duplicate=structuredClone(CATALOGUE);duplicate.items[1].id=1;
 assert.throws(()=>validateCatalogue(duplicate),/CATALOGUE_IDS/);
});

test('bounded agreement never promotes a whole failure family or unmapped prompts',()=>{
 const c=coverageFor(records('OBSERVED_AGREEMENT'));
 assert.equal(c.items.length,104);assert.equal(c.complete_failure_coverage,false);
 assert.equal(c.items.find(x=>x.id===28).status,'BOUNDED_AGREEMENT');
 assert.equal(c.items.find(x=>x.id===28).checks.length,4);
 assert.equal(c.items.find(x=>x.id===97).status,'UNSUPPORTED_BY_THIS_COMMAND');
 assert.equal(c.items.find(x=>x.id===104).status,'UNSUPPORTED_BY_THIS_COMMAND');
 assert.ok(c.items.every(x=>x.full_family_coverage==='UNESTABLISHED'));
 assert.equal(c.counts.accounted_prompts,104);
 assert.equal(c.counts.fully_covered_families,0);
});

test('a failure survives a second UNKNOWN on the same family',()=>{
 const r=records('OBSERVED_AGREEMENT');
 r['suite-per-case-agreement-v1']={status:'OBSERVED_MISMATCH',head:{cases:5,mismatches:2}};
 r['suite-refusal-integrity-v1']={status:'UNKNOWN',reason:'toolchain unavailable'};
 const c=coverageFor(r),row=c.items.find(x=>x.id===28);
 assert.equal(row.status,'BOUNDED_MISMATCH');assert.equal(row.incomplete,true);
 assert.ok(row.checks.some(x=>x.status==='UNKNOWN'));
 assert.ok(row.checks.some(x=>x.status==='OBSERVED_MISMATCH'));
 assert.equal(c.items.find(x=>x.id===55).status,'UNKNOWN');
});

test('omitted checks remain NOT_RUN and cannot inherit previous observations',()=>{
 const c=coverageFor({'suite-per-case-agreement-v1':{status:'OBSERVED_AGREEMENT',head:{cases:5,mismatches:0}}});
 assert.equal(c.items.find(x=>x.id===35).status,'BOUNDED_AGREEMENT');
 assert.equal(c.items.find(x=>x.id===28).status,'NOT_RUN');
 assert.equal(c.items.find(x=>x.id===39).status,'NOT_RUN');
 assert.equal(c.counts.fully_covered_families,0);
});

test('unrecognized or fabricated outcomes do not produce agreement',()=>{
 const c=coverageFor({'junit-status-preservation-v1':{status:'PASSED'}});
 assert.equal(c.items.find(x=>x.id===39).status,'UNKNOWN');
 assert.ok(c.items.find(x=>x.id===39).checks.some(x=>x.reason==='INVALID_PROFILE_OUTCOME'));
});
