import {createHash} from 'node:crypto';
import cases from './report-cases.json' with {type:'json'};
import recipe from './report-repair.json' with {type:'json'};
import {admitLeanPatch} from '../lean-investigator-v1/contracts.mjs';
export const REPORT_METHOD='junit-report-integrity-v1';
export const REPORT_GATE='import Tests.SuiteRunner.Reports\n\ndef main (_ : List String) : IO UInt32 := pure 0\n';
export const REPORT_PROFILE=Object.freeze({method:REPORT_METHOD,path:'Tests/SuiteRunner/Reports.lean',module:'Tests.SuiteRunner.Reports',namespace:'Tests.SuiteRunner.Reports',cli_path:'MathGraphGate.lean',cli_module:'MathGraphGate',toolchain:'leanprover/lean4:v4.35.0',mode:'OWNED_FORK_PR_PILOT',gate_kind:'SELECTED_MODULE_BUILD'});
export const REPORT_ORIGINAL_SHA='670b65c829bffcc3dcafb2fbdfe8aee5a1ec8dede7ce4d0547d11bb600848fae';
export const REPORT_CANDIDATE_SHA='6a417259978445c5c5609910fcd5d514c1ddbf9cd7e17678d6fecd03b4381513';
export const REPORT_REFERENCE_RUNNER_SHA='478712f343e4aae0a69b0a73bbca8e4c73ee95fc47248baf0558737275617049';
export const REPORT_CORPUS_SHA='751b26c525fb7024044e5cccbdcf794531634b930dbb69c87711cc0d400a53d0';
export const REPORT_CASES=Object.freeze(cases.map(c=>Object.freeze(c)));
const hash=s=>createHash('sha256').update(s).digest('hex'),same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const contract='Operator-adopted finite report acceptance requirement: reject six malformed XML envelopes, preserve six valid controls and seven existing refusals. Independent Python ElementTree reference. Not full XML conformance.';
const groups=[{id:'new_refusals',label:'Malformed evidence must be refused'},{id:'valid_controls',label:'Valid reports remain accepted'},{id:'legacy_refusals',label:'Existing refusals remain enforced'}];
const valid=s=>s?.repository==='metalogiclabs/L4YAML'&&s.path===REPORT_PROFILE.path&&s.toolchain===REPORT_PROFILE.toolchain&&/^[a-f0-9]{40}$/.test(s.head_sha??'')&&[REPORT_ORIGINAL_SHA,REPORT_CANDIDATE_SHA].includes(s.sha256)&&s.cli_sha256===hash(REPORT_GATE);
export function reportPlan(s){if(!valid(s))return null;return {summary:'Three fixed XML acceptance obligations across nineteen independently referenced inputs',tests:groups.map(g=>({id:g.id,hypothesis:g.label,contract,expression:REPORT_CASES.filter(c=>c.group===g.id).map(c=>'(junitCases '+JSON.stringify(c.input)+').toOption.isSome == '+c.accepted).map(e=>'('+e+')').join(' && ')}))};}
export function reportReference(subject,context,observations){return {schema:'mathgraph.expectations.reference.v1',context,subject,expectation_set:REPORT_METHOD,reference:observations};}
export function admitReportExpectations(subject,plan,receipt,context){const expected=reportPlan(subject),o=receipt?.reference;const complete=!!expected&&same(plan,expected)&&receipt?.schema==='mathgraph.expectations.reference.v1'&&same(receipt.context,context)&&same(receipt.subject,subject)&&receipt.expectation_set===REPORT_METHOD&&o?.runner_sha256===REPORT_REFERENCE_RUNNER_SHA&&o?.corpus_sha256===REPORT_CORPUS_SHA&&same(o.records,REPORT_CASES.map(c=>({...c,observed_acceptance:c.accepted})));return {status:complete?'ADMITTED':'UNKNOWN',repair_eligible:complete,reason:complete?'EXACT_FINITE_REFERENCE_BINDING':'REFERENCE_INCOMPLETE',subject,plan_sha256:hash(JSON.stringify(plan)),authority:contract,expectation_set:REPORT_METHOD,requirement_count:3,input_count:19,probes:(plan?.tests??[]).map(p=>({id:p.id,label:groups.find(g=>g.id===p.id)?.label??p.id,status:complete?'ADMITTED':'UNKNOWN',requirement:contract,expression_sha256:hash(p.expression)}))};}
export function qualifiedReportPatch(source){return hash(source)===REPORT_ORIGINAL_SHA?structuredClone(recipe):null;}
export function admitReportPatch(p,source){if(hash(source)!==REPORT_ORIGINAL_SHA)throw Error('REPORT_SOURCE_NOT_QUALIFIED');const patched=admitLeanPatch(p,source);if(hash(patched)!==REPORT_CANDIDATE_SHA)throw Error('REPORT_CANDIDATE_NOT_QUALIFIED');return patched;}
export function admitReportSources(base,head){if(![base,head].every(s=>[REPORT_ORIGINAL_SHA,REPORT_CANDIDATE_SHA].includes(hash(s))))throw Error('REPORT_SOURCE_NOT_QUALIFIED');return true;}
