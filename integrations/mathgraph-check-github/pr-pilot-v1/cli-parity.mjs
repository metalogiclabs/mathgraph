// Independent mechanical admission of CLI receipts; never imported by the Worker.
import fs from 'node:fs';import {createHash} from 'node:crypto';import {CLI_MODE} from './cli-profiles.mjs';
const read=p=>fs.readFileSync(new URL(p,import.meta.url));
const contractBytes=read('../cli-parity-v1/contract.json'),caseBytes=read('../cli-parity-v1/cases.json'),contract=JSON.parse(contractBytes),allCases=JSON.parse(caseBytes);
const hash=b=>createHash('sha256').update(b).digest('hex'),ensure=(b,c)=>{if(!b)throw Error(c);};
const canonical=x=>x&&typeof x==='object'?(Array.isArray(x)?'['+x.map(canonical).join(',')+']':'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}'):JSON.stringify(x);
function observation(o){ensure(o?.complete===true&&Number.isSafeInteger(o.exit)&&o.exit>=0&&o.exit<=255&&![124,125,126,127,137].includes(o.exit)&&typeof o.stdout==='string'&&typeof o.stderr==='string'&&Buffer.byteLength(o.stdout)+Buffer.byteLength(o.stderr)<=contract.limits.output_bytes&&o.effects&&typeof o.effects==='object'&&!Array.isArray(o.effects),'CLI_EXECUTION_INCOMPLETE');}
function stdout(text,mode){if(mode==='exact')return text;ensure(mode==='generator-provenance','CLI_POLICY_UNKNOWN');const lines=text.split('\n'),hits=[];for(let i=0;i<lines.length;i++)if(contract.generator_provenance_lines.includes(lines[i].replace(/\r$/,'')))hits.push(i);ensure(hits.length===1,'CLI_PROVENANCE_UNKNOWN');const i=hits[0];lines[i]='-- GENERATED: declared generator provenance'+(lines[i].endsWith('\r')?'\r':'');return lines.join('\n');}
function compare(b,again,h,spec){
 for(const o of [b,again,h])observation(o);ensure(b.exit===spec.expected_base_exit,'CLI_REFERENCE_EXIT_UNEXPECTED');ensure(['exit','stdout','stderr','effects'].every(k=>canonical(b[k])===canonical(again[k])),'CLI_REFERENCE_NONDETERMINISTIC');const differences=[];
 for(const[key,mode]of Object.entries(spec.comparison)){let x=b[key],y=h[key];if(key==='stdout'){x=stdout(x,mode);y=stdout(y,mode);}else if(key==='stderr'&&mode==='nonempty'){ensure(x.length>0,'CLI_REFERENCE_DIAGNOSTIC_ABSENT');x=true;y=y.length>0;}else ensure(mode==='exact','CLI_POLICY_UNKNOWN');if(canonical(x)!==canonical(y))differences.push(key);}
 return {state:differences.length?'DIFFERENCE':'PARITY',differences};
}
export function admitCliResult(r,request,context){
 const unknown=reason=>({context,subject:request,status:'UNKNOWN',reason,whole_pr_correctness:'UNKNOWN'});
 try{
  ensure(request.command==='check'&&request.profile.mode===CLI_MODE,'CLI_CHECK_ONLY');ensure(r?.schema==='mathgraph.cli-parity.report.v1','CLI_RECEIPT_MISSING');
  ensure(r.repository===contract.repository&&r.repository===request.repository&&r.pr===request.number&&r.base_sha===request.base_sha&&r.head_sha===request.head_sha&&r.profile===request.profile.cli_profile,'CLI_SUBJECT_MISMATCH');
  ensure(r.controller_sha===context.verifier_sha,'CLI_CONTROLLER_MISMATCH');ensure(r.contract_sha256===hash(contractBytes)&&r.cases_sha256===hash(caseBytes),'CLI_CONTRACT_CHANGED');ensure(r.whole_pr_correctness==='UNKNOWN','CLI_AUTHORITY_INVALID');
  const profile=contract.profiles.find(p=>p.id===r.profile),cases=allCases[r.profile];ensure(profile&&r.build_exit===0&&r.source_preserved===true&&/^[a-f0-9]{64}$/.test(r.oracle_sha256??'')&&/^[a-f0-9]{64}$/.test(r.source_hashes?.[profile.head_entry]??''),'CLI_NATIVE_INCOMPLETE');
  ensure(Array.isArray(r.cases)&&r.cases.length===cases.length,'CLI_CASES_INCOMPLETE');const rows=[];
  for(let i=0;i<cases.length;i++){const spec=cases[i],row=r.cases[i];ensure(row.id===spec.id&&canonical(row.policy)===canonical(spec.comparison),'CLI_CASE_IDENTITY_CHANGED');const actual=compare(row.base,row.reference_repeat,row.head,spec);ensure(actual.state===row.state&&canonical(actual.differences)===canonical(row.differences),'CLI_VERDICT_MISMATCH');rows.push({...row,state:actual.state,differences:actual.differences});}
  const first=rows[0],controls=r.controls;ensure(controls?.reference_replay_qualified===true&&controls.changed_native_output_detected===true&&controls.head_withdrawal_identical===true,'CLI_CONTROLS_FAILED');ensure(compare(first.base,first.reference_repeat,controls.negative,cases[0]).state==='DIFFERENCE','CLI_NEGATIVE_CONTROL_FAILED');observation(controls.withdrawal);ensure(canonical(controls.withdrawal)===canonical(first.head),'CLI_WITHDRAWAL_FAILED');
  const counts={PARITY:rows.filter(x=>x.state==='PARITY').length,DIFFERENCE:rows.filter(x=>x.state==='DIFFERENCE').length,UNKNOWN:0};ensure(canonical(counts)===canonical(r.counts),'CLI_COUNTS_MISMATCH');const status=counts.DIFFERENCE?'CLI_BEHAVIOR_DIFFERENCE':'CLI_PARITY_OBSERVED';ensure(r.state===status,'CLI_STATE_MISMATCH');
  return {context,subject:request,status,scope:profile.runtime_scope,counts,cases:rows,contract_sha256:r.contract_sha256,cases_sha256:r.cases_sha256,whole_pr_correctness:'UNKNOWN'};
 }catch(e){return unknown(e.message);}
}
