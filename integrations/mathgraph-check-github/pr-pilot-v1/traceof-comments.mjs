import {createHash} from 'node:crypto';
import {activeSource,admitLeanPatch} from '../lean-investigator-v1/contracts.mjs';
export const GENERATOR_METHOD='traceof-comments-v1';
export const GENERATOR_GATE='import Scripts.TraceOf.Gen\n\ndef main (_ : List String) : IO UInt32 := pure 0\n';
export const GENERATOR_PROFILE=Object.freeze({method:GENERATOR_METHOD,path:'Scripts/TraceOf/Gen.lean',module:'Scripts.TraceOf.Gen',namespace:'Scripts.TraceOf.Gen',cli_path:'MathGraphGate.lean',cli_module:'MathGraphGate',toolchain:'leanprover/lean4:v4.35.0',mode:'OWNED_FORK_PR_PILOT',gate_kind:'SELECTED_MODULE_BUILD'});
const hash=s=>createHash('sha256').update(s).digest('hex'),same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const contract='Operator-adopted finite nested Lean block-comment projection; 20 frozen inputs at depths 1–5. Independent active-source lexer reference. Not full Lean lexical conformance or whole-PR correctness.';
export const GENERATOR_CASES=[];
for(let depth=1;depth<=5;depth++)for(const body of ['note','line\ntext','-- is comment text','λ unicode']){let c='/- '+body+' ';for(let i=1;i<depth;i++)c='/- outer '+c+' -/ ';c+='-/';GENERATOR_CASES.push(Object.freeze({depth,input:'SCNsProperties n '+c+' c',expected:'SCNsProperties n  c'}));}
Object.freeze(GENERATOR_CASES);
const valid=s=>s?.repository==='metalogiclabs/L4YAML'&&s.path===GENERATOR_PROFILE.path&&s.toolchain===GENERATOR_PROFILE.toolchain&&/^[a-f0-9]{40}$/.test(s.head_sha??'')&&/^[a-f0-9]{64}$/.test(s.sha256??'')&&s.cli_sha256===hash(GENERATOR_GATE);
const groups=[{id:'shallow_comments',label:'Ordinary block-comment controls',min:1,max:1},{id:'nested_comments',label:'Nested block comments (depths 2–3)',min:2,max:3},{id:'deep_comments',label:'Nested block comments (depths 4–5)',min:4,max:5}];
const norm=s=>s.replace(/\s+/g,' ').trim();
export function generatorPlan(s){if(!valid(s))return null;return {summary:'Three reviewed finite comment-stripping obligations across twenty native inputs',tests:groups.map(g=>({id:g.id,hypothesis:'Removing valid block comments preserves the surrounding premise text.',contract,expression:GENERATOR_CASES.filter(c=>c.depth>=g.min&&c.depth<=g.max).map(c=>'(stripComments '+JSON.stringify(c.input)+' == '+JSON.stringify(c.expected)+')').join(' && ')}))};}
export function generatorReference(subject,context){return {schema:'mathgraph.expectations.reference.v1',context,subject,expectation_set:GENERATOR_METHOD,reference:{records:GENERATOR_CASES.map(c=>({input:c.input,expected:c.expected,active_source:norm(activeSource(c.input).code),expected_active_source:norm(activeSource(c.expected).code)}))}};}
export function admitGeneratorExpectations(subject,plan,receipt,context){const expected=generatorPlan(subject),reference=generatorReference(subject,context);const complete=!!expected&&same(expected,plan)&&same(receipt,reference)&&reference.reference.records.every(r=>r.active_source===r.expected_active_source);return {status:complete?'ADMITTED':'UNKNOWN',repair_eligible:complete,reason:complete?'EXACT_FINITE_REFERENCE_BINDING':'REFERENCE_INCOMPLETE',subject,plan_sha256:hash(JSON.stringify(plan)),authority:contract,expectation_set:GENERATOR_METHOD,requirement_count:3,input_count:20,probes:(plan?.tests??[]).map(p=>{const g=groups.find(g=>g.id===p.id);return {id:p.id,status:complete?'ADMITTED':'UNKNOWN',label:g?.label??p.id,input:g?'Frozen comment depths '+g.min+'–'+g.max:undefined,expectation:'Surrounding premise text preserved',requirement:contract,expression_sha256:hash(p.expression)};})};}
const OLD_DOC="/-- `strip_comments` on a term's source text: `/- … -/` (nested once as the Python's\n    non-greedy match read it) and `-- …` to end of line removed. -/";
const NEW_DOC="/-- `strip_comments` on a term's source text: nested Lean `/- … -/` block comments and `-- …` line comments removed. -/";
// Permit only this reviewed strengthening of the implementation description;
// every other original docstring, signature and guard remains protected.
export function admitProfilePatch(p,source,snapshot){if(snapshot?.method!==GENERATOR_METHOD)return admitLeanPatch(p,source);if(typeof p?.summary!=='string'||!p.summary.trim()||p.summary.length>1200||!Array.isArray(p.edits)||p.edits.length<1||p.edits.length>3)throw Error('INVALID_LEAN_PATCH');let raw=source;for(const e of p.edits??[]){if(typeof e.old!=='string'||typeof e.new!=='string'||!e.old||Buffer.byteLength(e.old)>16000||Buffer.byteLength(e.new)>16000||raw.split(e.old).length!==2)throw Error('AMBIGUOUS_LEAN_EDIT');raw=raw.replace(e.old,()=>e.new);}if(source.includes(OLD_DOC)&&!raw.includes(OLD_DOC)&&raw.split(NEW_DOC).length===2){const normalized=raw.replace(NEW_DOC,OLD_DOC);admitLeanPatch({summary:p.summary,edits:[{old:source,new:normalized}]},source);return raw;}return admitLeanPatch(p,source);}

export function qualifiedGeneratorPatch(source){
 if(hash(source)!=='de52cee293d1921b4ef350fbd3b77c8c0a336703c612f9945079a1a29e2f355d')return null;
 const old=`      let mut rest := t
      let mut go := true
      while go do
        match rest with
        | '-' :: '/' :: r => rest := r; go := false
        | _ :: r => rest := r
        | [] => go := false
      cs := rest`;
 const replacement=`      let mut rest := t
      let mut depth : Nat := 1
      while depth > 0 do
        match rest with
        | '/' :: '-' :: r => rest := r; depth := depth + 1
        | '-' :: '/' :: r => rest := r; depth := depth - 1
        | _ :: r => rest := r
        | [] => depth := 0
      cs := rest`;
 const guard='#guard stripComments "a -/ b" == "a -/ b"';
 const guards=guard+'\n#guard stripComments "SCNsProperties n /- outer /- inner -/ outer -/ c" == "SCNsProperties n  c"\n#guard stripComments "a /- one /- two /- three -/ two -/ one -/ b" == "a  b"';
 const content=source.replace(old,replacement).replace(OLD_DOC,NEW_DOC).replace(guard,guards);
 if(hash(content)!=='edfae7b27b8cafc5a35e348dfe3e9a4490629b7a5ce453a036e8b78bf658d9db')throw Error('QUALIFIED_CANDIDATE_IDENTITY_MISMATCH');
 return {summary:'Reuse the previously qualified exact-source nested-comment candidate; fresh native verification is required',edits:[{old:source,new:content}]};
}
