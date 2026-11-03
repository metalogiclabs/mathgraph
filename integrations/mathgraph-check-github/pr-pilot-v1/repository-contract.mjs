// Trusted bridge from the fixed native contract to the existing neutral App.
// Source PRs cannot select this contract, its corpus, or native commands.
import {readFileSync} from 'node:fs';import {createHash} from 'node:crypto';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const contract=JSON.parse(read('../repository-contract-v1/contract.json'));
const contractHash=createHash('sha256').update(read('../repository-contract-v1/contract.json')).digest('hex');
const corpusHash=read('../repository-contract-v1/corpus.sha256').trim();
const sizes={208:1134,211:108,212:25,204:100};
const ensure=(b,c)=>{if(!b)throw Error(c);};
import {CONTRACT_MODE} from './repository-report.mjs';
export function admitRepositoryResult(r,request,context){
 const unknown=reason=>({context,subject:request,status:'UNKNOWN',reason,whole_pr_correctness:'UNKNOWN'});
 try{
  ensure(request.profile.mode===CONTRACT_MODE&&request.command==='check','CONTRACT_CHECK_ONLY');
  ensure(r?.schema==='mathgraph.repository-contract.report.v1','CONTRACT_RECEIPT_MISSING');
  ensure(r.repository===request.repository&&r.repository===contract.repository&&r.pr===request.number&&r.head_sha===request.head_sha&&r.base_sha===request.base_sha,'CONTRACT_SUBJECT_MISMATCH');
  ensure(r.controller_sha===context.verifier_sha,'CONTRACT_CONTROLLER_MISMATCH');
  ensure(r.contract_sha256===contractHash&&r.corpus_sha256===corpusHash,'CONTRACT_IDENTITY_MISMATCH');
  ensure(r.whole_pr_correctness==='UNKNOWN','INVALID_CONTRACT_AUTHORITY');
  if(r.state==='STALE')return {...unknown('SOURCE_CHANGED'),status:'STALE'};
  for(const side of ['base','head']){
   const a=r.arms?.[side];
   ensure(a?.qualified===true&&a.source_sha===request[side+'_sha']&&a.build_exit===0&&a.cases===contract.regression.expected_cases&&Number.isSafeInteger(a.passed)&&Array.isArray(a.failed)&&Array.isArray(a.unknown)&&a.unknown.length===0,'CONTRACT_NATIVE_INCOMPLETE');
   ensure(new Set(a.failed).size===a.failed.length&&a.failed.every(id=>{const m=typeof id==='string'&&id.match(/^(208|211|212|204):([0-9]+)$/);return m&&String(Number(m[2]))===m[2]&&Number(m[2])<sizes[m[1]];}),'INVALID_FROZEN_WITNESSES');
   ensure(a.passed>=0&&a.passed+a.failed.length===a.cases,'CONTRACT_COUNTS_MISMATCH');
   ensure(Array.isArray(a.roots)&&a.roots.length>0&&Array.isArray(a.modules)&&a.modules.length>0,'CONTRACT_COVERAGE_MISSING');
  }
  const b=r.arms.base,h=r.arms.head;
  const status=b.failed.length?(h.failed.length?'FAILURE_ON_BOTH_REVISIONS':'RESOLVED_FROZEN_PROBE_FAILURE'):(h.failed.length?'NEW_FROZEN_PROBE_FAILURE':'NO_FAILURE_IN_FROZEN_CORPUS');
  ensure(r.state===status,'CONTRACT_CLASSIFICATION_MISMATCH');
  ensure(r.scope&&['modules','base_modules','uncovered','deleted_modules'].every(k=>Array.isArray(r.scope[k])&&r.scope[k].every(x=>typeof x==='string')),'CONTRACT_SCOPE_MISSING');
  const coverage={uncovered:r.scope.uncovered,deleted_modules:r.scope.deleted_modules};
  for(const side of ['base','head']){const a=r.arms[side];coverage[side]={compiled_roots:a.roots,compiled_modules:a.modules,cases:a.cases,passed:a.passed,failed:a.failed};}
  return {context,subject:request,status,whole_pr_correctness:'UNKNOWN',contract_sha256:contractHash,corpus_sha256:corpusHash,coverage,
   introduced:h.failed.filter(id=>!b.failed.includes(id)),resolved:b.failed.filter(id=>!h.failed.includes(id)),inherited:h.failed.filter(id=>b.failed.includes(id))};
 }catch(e){return unknown(e.message);}
}
