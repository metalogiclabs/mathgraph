import {createHash} from 'node:crypto';
import {LEADING_TARGET,leadingReferenceOK} from './leading-obligation.mjs';
export {LEADING_REFERENCE_IDENTITY} from './leading-obligation.mjs';
export const REFERENCE_IDENTITY={cohort_sha256:'a221224d2f8939b68619df66c6b22cf5614d908ad363c97b532554581901ee9b',runner_sha256:'47683258544a0b9a4e1697a9c8d9683184ccd7100da125aebbe999fb77cef12e'};
const SOURCES=Object.freeze({fba155bf31918f9b03394ae9bfb8cd17c91ecfb8:'2e682e47ad98d581f7b075dfb880934ff89a3e3e287ac654d877cf1dee53ced4','796dcffde4e9d4d1c805199b9f795fa3c6152f1b':'578b095eed0d0b766819bf0939d6f89bf56659f1e5c8cf666273e6ed5ee886a2'});
const CLI='64bb20331484ef711b6a752af1770959164c82308fd9ae79fbf954678ebbdbcf';
const TARGETS=[
 {id:'attached_ok',reference_id:'attached_redirect',command:'python3 -c 1>out',calls:[['-c']],expression:'pyCallsOfLine "python3 -c 1>out" == [.inline "python3 -c"]',hypothesis:'A file-descriptor redirect does not become an interpreter argument.'},
 {id:'keyword_ok',reference_id:'argument_keyword',command:'echo if python3 scripts/a.py > /dev/null',calls:[],expression:'pyCallsOfLine "echo if python3 scripts/a.py > /dev/null" == []',hypothesis:'An if word used as an echo argument does not open command position.'}
];
const contract='Operator-adopted finite shell command-position/prefix obligation, independently replayed with Bash; PR259/run41643264976. Not general Bash conformance.';
const hash=s=>createHash('sha256').update(s).digest('hex'),same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
// Trusted method adapter boundary, analogous to a caller-qualified Receipt.
// This capability is process-local: artifact JSON/status labels cannot carry it.
const transported=new WeakMap();
export function qualifyProducerSubject(subject){const token=Object.freeze({});transported.set(token,JSON.stringify(subject));return token;}
const transportedSubject=(subject,token)=>token&&transported.get(token)===JSON.stringify(subject)&&subject.repository==='metalogiclabs/L4YAML'&&subject.path==='Scripts/Ledger.lean'&&subject.cli_sha256===CLI&&subject.toolchain==='leanprover/lean4:v4.35.0';
function qualified(s){return s?.repository==='metalogiclabs/L4YAML'&&s.path==='Scripts/Ledger.lean'&&s.toolchain==='leanprover/lean4:v4.35.0'&&SOURCES[s.head_sha]===s.sha256&&typeof s.sha256==='string'&&s.cli_sha256===CLI;}
export function expectationProfileFor(r){return r.repository==='metalogiclabs/L4YAML'&&r.profile?.mode==='OWNED_FORK_PR_PILOT'&&Object.hasOwn(SOURCES,r.head_sha)?'ledger-shell-v1':null;}
export function expectationSubject(s){return {repository:s.repository,head_sha:s.head_sha,path:s.path,sha256:hash(s.source),cli_sha256:hash(s.cli_source),toolchain:s.toolchain};}
export function reviewedPlan(s,token,profile='ledger-shell-v1'){
 if(!['ledger-shell-v1','ledger-shell-v2'].includes(profile)||!(qualified(s)||transportedSubject(s,token)))return null;
 const tests=TARGETS.map(t=>({id:t.id,hypothesis:t.hypothesis,contract,expression:t.expression}));
 if(profile==='ledger-shell-v2')tests.push({id:LEADING_TARGET.id,hypothesis:LEADING_TARGET.hypothesis,contract:LEADING_TARGET.contract,expression:LEADING_TARGET.expression});
 return {summary:profile==='ledger-shell-v1'?'Two reviewed finite shell obligations':'Three reviewed finite obligations across five shell inputs',tests};
}
function referenceOK(record,target){
 const good=(o,calls)=>o?.status==='OK'&&o.exit===0&&same(o.calls,calls);
 return record?.Conclusion?.status==='SUPPORTED'&&record.Obligation?.id===target.reference_id&&record.Obligation.command===target.command&&same(record.Obligation.expected_calls,target.calls)&&record.Obligation.authority?.state==='DECLARED'&&Object.entries(REFERENCE_IDENTITY).every(([k,v])=>record.Dependencies?.[k]===v)&&/^[a-f0-9]{64}$/.test(record.Dependencies?.bash_sha256??'')&&good(record.Verification?.execution,target.calls)&&good(record.Verification?.repeat,target.calls)&&good(record.Verification?.controls?.positive,[['guard.py']])&&good(record.Verification?.controls?.negative,[]);
}
export function admitExpectations(subject,plan,receipt,context,token,profile='ledger-shell-v1'){
 const expected=reviewedPlan(subject,token,profile),result={status:'UNKNOWN',repair_eligible:false,reason:'EXPECTATION_SOURCE_NOT_QUALIFIED',subject,plan_sha256:hash(JSON.stringify(plan)),authority:contract,expectation_set:profile,requirement_count:profile==='ledger-shell-v2'?3:2,input_count:profile==='ledger-shell-v2'?5:2,probes:(plan?.tests??[]).map(p=>({id:p.id,status:'UNKNOWN',reason:'UNREVIEWED_EXPECTATION'}))};
 if(!expected)return result;
 const records=receipt?.reference?.records;
 const fresh=receipt?.schema==='mathgraph.expectations.reference.v1'&&same(receipt.context,context)&&same(receipt.subject,subject)&&Array.isArray(records);
 result.probes=(plan?.tests??[]).map(p=>{
  if(profile==='ledger-shell-v2'&&p.id===LEADING_TARGET.id&&p.expression===LEADING_TARGET.expression){
   const admitted=fresh&&receipt.expectation_set===profile&&leadingReferenceOK(receipt.leading_reference?.records);
   return {id:p.id,label:LEADING_TARGET.label,input:LEADING_TARGET.command,expectation:LEADING_TARGET.expectation,requirement:LEADING_TARGET.contract,status:admitted?'ADMITTED':'UNKNOWN',reason:admitted?'EXACT_FINITE_REFERENCE_BINDING':'REFERENCE_INCOMPLETE',expression_sha256:hash(p.expression)};
  }
  if(p.expression==='pyCallsOfLine "python3 -c 1>out" == [.inline "python3 -c 1"]')return {id:p.id,status:'REJECTED',reason:'REFERENCE_CONTRADICTS_EXPECTED_VALUE'};
  const target=TARGETS.find(t=>t.id===p.id&&t.expression===p.expression);
  const found=target&&fresh?records.filter(r=>r.Obligation?.id===target.reference_id):[];
  const admitted=target&&found.length===1&&referenceOK(found[0],target);
  return {id:p.id,label:target?.id==='keyword_ok'?'Keywords used as arguments':target?.id==='attached_ok'?'Attached redirection':p.id,input:target?.command,expectation:target?.id==='keyword_ok'?'No Python invocation':target?'Inline prefix python3 -c':undefined,status:admitted?'ADMITTED':'UNKNOWN',reason:admitted?'EXACT_FINITE_REFERENCE_BINDING':!target?'UNREVIEWED_EXPECTATION':'REFERENCE_INCOMPLETE',expression_sha256:hash(p.expression??''),reference_id:target?.reference_id,requirement:target?contract:undefined};
 });
 const complete=same(plan,expected)&&result.probes.every(p=>p.status==='ADMITTED');
 return {...result,status:complete?'ADMITTED':'UNKNOWN',repair_eligible:complete,reason:complete?'EXACT_FINITE_REFERENCE_BINDING':!same(plan,expected)?'UNREVIEWED_EXPECTATION':'REFERENCE_INCOMPLETE'};
}
