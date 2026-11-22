import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import catalogue from './catalogue.json' with {type:'json'};
import xmlCases from '../pr-pilot-v1/report-cases.json' with {type:'json'};
import statusCases from '../pr-pilot-v1/report-status-cases.json' with {type:'json'};
import perCaseCases from '../retained-suite-v1/per-case-cases.json' with {type:'json'};
import refusalCases from '../retained-suite-v1/refusal-cases.json' with {type:'json'};

export const CATALOGUE_SHA256='13f1bee06b12fcafbaada31c7e4ed0818e40c3885355bd538d71bb0f5de29886';
const digest=x=>createHash('sha256').update(x).digest('hex');
export function validateCatalogue(value){
 if(value?.revision!=='2026-11-22-r2'||value.items?.length!==104||
  value.items.some((x,i)=>x.id!==i+1))throw Error('CATALOGUE_IDS_OR_REVISION_CHANGED');
 if(value.items.some(x=>!x.title||!x.prompt||x.lifecycle!=='CANDIDATE_PROMPT'))throw Error('CATALOGUE_PROMPTS_INVALID');
 return value;
}
if(digest(readFileSync(new URL('./catalogue.json',import.meta.url)))!==CATALOGUE_SHA256)throw Error('FROZEN_CATALOGUE_CHANGED');
export const CATALOGUE=validateCatalogue(catalogue);

// These are editorial mappings to finite facets, not whole-family detectors.
// EA01/03/04 are the controlled mechanisms in the source-bound L4YAML audit.
export const PROFILES=Object.freeze([
 {id:'junit-report-integrity-v1',title:'XML acceptance',case_count:19,
  failure_ids:[28,29,39,59,77],
  obligation:'Six malformed XML envelopes are refused; six valid reports and seven existing refusals retain their outcomes.',
  boundary:'19 fixed inputs through actual Reports.lean with the declared empty HtmlReport dependency; no complete XML conformance claim.',
  mapping_basis:'Editorial mapping of the previously retained XML acceptance profile.'},
 {id:'junit-status-preservation-v1',title:'JUnit status preservation',case_count:8,
  failure_ids:[28,39,59,77,78,100],
  obligation:'Error and failure remain nonpassing through the actual JUnit rows and fixed HTML report projection.',
  boundary:'Eight fixed cases, the selected three-status renderer and fixed supported HTML layout; no full report CLI or recovery claim.',
  mapping_basis:'EA04 finite status-preservation witness, mapped to catalogue r2 prompts.'},
 {id:'suite-per-case-agreement-v1',title:'Per-case agreement',case_count:5,
  failure_ids:[28,35,59,61,66,67,70,73,77,90],
  obligation:'Keyed case disagreement must remain disagreement even when backend totals are equal.',
  boundary:'Controlled four-backend, five-preset acceptance observations through actual isolated Reports comparison consumers; no AST/value equality or full CLI claim.',
  mapping_basis:'EA01 equal-totals/opposite-outcomes witness, mapped to catalogue r2 prompts.'},
 {id:'suite-refusal-integrity-v1',title:'Refusal versus apparatus failure',case_count:18,
  failure_ids:[28,55,59,60,77,78,100],
  obligation:'A negative test passes only on a deliberate parser refusal under the declared exact marker and exit-status protocol.',
  boundary:'Actual byte-preserved runTest declaration and required dependencies with controlled child processes; no full parser or recovery qualification.',
  mapping_basis:'EA03 abnormal-exit and missing-executable witness, mapped to catalogue r2 prompts.'}
].map((p,i)=>{
 const case_ids=[xmlCases,statusCases,perCaseCases,refusalCases.cases][i].map(c=>c.id);
 if(case_ids.length!==p.case_count||new Set(case_ids).size!==p.case_count)throw Error('FIXED_CASE_ROSTER_CHANGED: '+p.id);
 return Object.freeze({...p,case_ids:Object.freeze(case_ids),failure_ids:Object.freeze(p.failure_ids)});
}));

const OUTCOMES=new Set(['OBSERVED_AGREEMENT','OBSERVED_MISMATCH','UNKNOWN','NOT_RUN']);
export function coverageFor(results={}){
 const items=CATALOGUE.items.map(item=>{
  const checks=PROFILES.filter(p=>p.failure_ids.includes(item.id)).map(p=>{
   const r=results[p.id];const valid=!r||OUTCOMES.has(r.status);
   return {profile:p.id,obligation:p.obligation,boundary:p.boundary,
    status:valid?(r?.status??'NOT_RUN'):'UNKNOWN',
    reason:valid?(r?.reason??(r?null:'PROFILE_NOT_SELECTED')):'INVALID_PROFILE_OUTCOME',
    base:r?.base??null,head:r?.head??null,result:r?.result??null};
  });
  const incomplete=checks.some(c=>['UNKNOWN','NOT_RUN'].includes(c.status));
  const status=checks.length===0?'UNSUPPORTED_BY_THIS_COMMAND':
   checks.some(c=>c.status==='OBSERVED_MISMATCH')?'BOUNDED_MISMATCH':
   checks.some(c=>c.status==='UNKNOWN')?'UNKNOWN':checks.some(c=>c.status==='NOT_RUN')?'NOT_RUN':'BOUNDED_AGREEMENT';
  return {...item,status,full_family_coverage:'UNESTABLISHED',incomplete,checks,
   residual:checks.length?'All cases and mechanisms outside the declared finite obligations remain unassessed.':
    'No retained executable is connected to this prompt in this command. This is not a finding of inapplicability or absence of other Check capabilities.'};
 });
 const count=status=>items.filter(x=>x.status===status).length;
 return {revision:CATALOGUE.revision,catalogue_sha256:CATALOGUE_SHA256,source:CATALOGUE.source,
  mapping_status:'EDITORIAL_FINITE_FACETS',complete_failure_coverage:false,
  counts:{accounted_prompts:items.length,mapped_prompts:items.filter(x=>x.checks.length).length,
   bounded_agreement:count('BOUNDED_AGREEMENT'),bounded_mismatch:count('BOUNDED_MISMATCH'),
   unknown:count('UNKNOWN'),not_run:count('NOT_RUN'),unsupported_by_this_command:count('UNSUPPORTED_BY_THIS_COMMAND'),
   prompts_with_incomplete_checks:items.filter(x=>x.incomplete).length,fully_covered_families:0},items};
}
