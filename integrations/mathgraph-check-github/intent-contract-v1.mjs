/**
 * MathGraph Check: exact-source bounded intent/probe audit (pure, read-only).
 *
 * The caller authenticates receipt IDs and independently qualifies verifier
 * and oracle source hashes. In-band booleans, raw CI-success strings, badges,
 * and self-hashes never grant authority.
 * OBSERVED means only that finite pinned probes passed, not that user intent
 * is satisfied on all possible executions. BLOCKED needs a qualified witness.
 */
import {createHash} from 'node:crypto';

export const SCHEMA='mathgraph.intent-probes.v1';
const SHA40=/^[a-f0-9]{40}$/;
const SHA256=/^[a-f0-9]{64}$/;
const REPO=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const ID=/^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,79}$/;
const plain=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&
  (Object.getPrototypeOf(x)===Object.prototype||Object.getPrototypeOf(x)===null);
const keys=(obj,expected)=>plain(obj)&&Object.keys(obj).every(k=>expected.includes(k))&&
  expected.every(k=>Object.hasOwn(obj,k));
const unique=a=>new Set(a).size===a.length;
const canon=x=>Array.isArray(x)?x.map(canon):plain(x)?
  Object.fromEntries(Object.keys(x).sort().map(k=>[k,canon(x[k])])):x;
export const digestContract=x=>createHash('sha256').update(JSON.stringify(canon(x))).digest('hex');
const fail=(reason,details={})=>({schema:SCHEMA,status:'UNKNOWN',reason,
  permission:'ADVISORY_ONLY',intent_verification:'NOT_ESTABLISHED',
  checked_scope:'NONE',source:null,results:[],claim_dependencies:[],
  next_actions:[],...details});

function validateContract(c){
  if(!keys(c,['schema','subject','claims','probes'])||c.schema!==SCHEMA)return 'INVALID_CONTRACT_SCHEMA';
  const s=c.subject;
  if(!keys(s,['repository','pr','base_sha','head_sha'])||!REPO.test(s.repository)||
    !Number.isSafeInteger(s.pr)||s.pr<1||!SHA40.test(s.base_sha)||!SHA40.test(s.head_sha))
    return 'INVALID_SOURCE_BINDING';
  if(!Array.isArray(c.claims)||!c.claims.length||c.claims.length>32||
    !Array.isArray(c.probes)||!c.probes.length||c.probes.length>64)
    return 'INVALID_PROBE_UNIVERSE';
  if(!c.claims.every(q=>keys(q,['id','statement','requires'])&&ID.test(q.id)&&
      typeof q.statement==='string'&&q.statement.trim().length>0&&q.statement.length<=1000&&
      Array.isArray(q.requires)&&q.requires.length>0&&q.requires.length<=64&&
      q.requires.every(x=>typeof x==='string'&&ID.test(x))&&unique(q.requires)))
    return 'INVALID_CLAIM';
  if(!c.probes.every(p=>keys(p,['id','input_sha256','oracle_sha256','verifier_sha'])&&
      ID.test(p.id)&&SHA256.test(p.input_sha256)&&SHA256.test(p.oracle_sha256)&&
      SHA40.test(p.verifier_sha)))return 'INVALID_PROBE';
  const qIds=c.claims.map(q=>q.id),pIds=c.probes.map(p=>p.id);
  if(!unique(qIds)||!unique(pIds))return 'DUPLICATE_ID';
  if(!c.claims.every(q=>q.requires.every(id=>pIds.includes(id))))return 'UNKNOWN_REQUIRED_PROBE';
  if(Buffer.byteLength(JSON.stringify(c))>32768)return 'OVERSIZE_CONTRACT';
  return null;
}
function receiptShape(r){
  return keys(r,['id','probe_id','subject_sha','contract_sha256','input_sha256',
                 'oracle_sha256','verifier_sha','result','exit_code','log_sha256','witness_sha256'])&&
    ID.test(r.id)&&ID.test(r.probe_id)&&SHA40.test(r.subject_sha)&&
    SHA256.test(r.contract_sha256)&&SHA256.test(r.input_sha256)&&
    SHA256.test(r.oracle_sha256)&&SHA40.test(r.verifier_sha)&&
    ['PASS','COUNTEREXAMPLE','INCONCLUSIVE','ERROR'].includes(r.result)&&
    Number.isSafeInteger(r.exit_code)&&SHA256.test(r.log_sha256)&&
    (r.witness_sha256===null||SHA256.test(r.witness_sha256));
}

/**
 * Authority is an authenticated caller argument, never a field read from
 * a developer-authored contract or receipt.
 */
export function auditIntent(contract,receipts,authority={}){
  const malformed=validateContract(contract);
  if(malformed)return fail(malformed);
  const source=contract.subject,contractSha=digestContract(contract);
  const policy=plain(authority)?authority:{};
  if(!Array.isArray(policy.allowedRepositories)||!policy.allowedRepositories.includes(source.repository))
    return fail('REPOSITORY_NOT_AUTHORIZED',{source,contract_sha256:contractSha});
  if(policy.expectedHeadSha!==source.head_sha||policy.expectedContractSha256!==contractSha)
    return fail('SOURCE_OR_CONTRACT_UNBOUND',{source,contract_sha256:contractSha});
  if(!Array.isArray(policy.authenticatedReceiptIds)||
     !Array.isArray(policy.qualifiedVerifierShas)||
     !Array.isArray(policy.qualifiedOracleShas))
    return fail('INDEPENDENT_AUTHORITY_REQUIRED',{source,contract_sha256:contractSha});
  const authentic=new Set(policy.authenticatedReceiptIds);
  const verifier=new Set(policy.qualifiedVerifierShas);
  const oracle=new Set(policy.qualifiedOracleShas);
  if(!Array.isArray(receipts)||receipts.length>128||
    !receipts.every(receiptShape)||!unique(receipts.map(r=>r.id)))
    return fail('INVALID_RECEIPT_SET',{source,contract_sha256:contractSha});
  const dependency=contract.claims.map(q=>({id:q.id,requires:[...q.requires]}));
  const probeResults=new Map();
  for(const p of contract.probes){
    const matches=receipts.filter(r=>r.probe_id===p.id);
    const result=(state,reason,receipt=null)=>({id:p.id,status:state,reason,
      receipt_id:receipt?.id??null,witness_sha256:receipt?.witness_sha256??null});
    if(matches.length!==1){probeResults.set(p.id,result('UNKNOWN',matches.length?'CONFLICTING_RECEIPTS':'MISSING_RECEIPT'));continue;}
    const r=matches[0];
    if(!authentic.has(r.id)||!verifier.has(r.verifier_sha)||!oracle.has(r.oracle_sha256)){
      probeResults.set(p.id,result('UNKNOWN','EVIDENCE_NOT_INDEPENDENTLY_QUALIFIED'));continue;
    }
    if(r.subject_sha!==source.head_sha||r.contract_sha256!==contractSha||
       r.input_sha256!==p.input_sha256||r.oracle_sha256!==p.oracle_sha256||
       r.verifier_sha!==p.verifier_sha){
      probeResults.set(p.id,result('UNKNOWN','EXACT_SOURCE_OR_PROBE_MISMATCH'));continue;
    }
    if(r.result==='PASS'&&r.exit_code===0&&r.witness_sha256===null){
      probeResults.set(p.id,result('OBSERVED','PINNED_PROBE_PASSED',r));continue;
    }
    if(r.result==='COUNTEREXAMPLE'&&r.exit_code===1&&r.witness_sha256!==null){
      probeResults.set(p.id,result('BLOCKED','PINNED_COUNTEREXAMPLE_OBSERVED',r));continue;
    }
    probeResults.set(p.id,result('UNKNOWN','INCONCLUSIVE_ERROR_OR_INVALID_EXIT'));
  }
  const results=contract.claims.map(q=>{
    const checked=q.requires.map(id=>probeResults.get(id));
    const bad=checked.filter(x=>x.status==='BLOCKED');
    const missing=checked.filter(x=>x.status==='UNKNOWN');
    return {id:q.id,status:bad.length?'BLOCKED':missing.length?'UNKNOWN':'OBSERVED',
      reason:bad.length?'QUALIFIED_BOUNDED_COUNTEREXAMPLE':
        missing.length?'MISSING_OR_INCONCLUSIVE_BOUNDED_PROBE':
        'PINNED_PROBES_ONLY_NOT_INTENT_PROOF',probes:checked};
  });
  const status=results.some(q=>q.status==='BLOCKED')?'BLOCKED':
    results.some(q=>q.status==='UNKNOWN')?'UNKNOWN':'OBSERVED';
  return {schema:SCHEMA,status,reason:'BOUNDED_PROBE_AUDIT',
    permission:'ADVISORY_ONLY',intent_verification:'NOT_ESTABLISHED',
    checked_scope:'DECLARED_PINNED_PROBES_ONLY',freshness:'NOT_CHECKED',
    revocation:'NOT_CHECKED',current_applicability:'UNKNOWN',
    source,subject:source,contract_sha256:contractSha,results,
    claim_dependencies:dependency,
    next_actions:results.filter(x=>x.status!=='OBSERVED').map(x=>({claim:x.id,
      action:x.status==='BLOCKED'?'INSPECT_QUALIFIED_WITNESS':'RUN_MISSING_EXACT_HEAD_PROBES'}))};
}

const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',
  '"':'&quot;',"'":'&#39;'}[c]));
/** Human-readable projection. It is *not* a proof badge or authorization. */
export function renderIntentReport(report){
  if(!plain(report)||report.schema!==SCHEMA)throw Error('INVALID_REPORT');
  const names={OBSERVED:'Observed checks',BLOCKED:'Behavioral counterexample',UNKNOWN:'Evidence incomplete'};
  const headline=names[report.status]??'Evidence incomplete';
  const rows=(report.results??[]).map(c=>'<tr><td>'+esc(c.id)+'</td><td>'+esc(c.status)+'</td><td>'+esc(c.reason)+'</td></tr>').join('');
  const sha=report.source?.head_sha??'unbound';
  return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MathGraph Check — '+esc(headline)+'</title><style>body{margin:3rem auto;max-width:780px;padding:0 1.3rem;background:#0b1220;color:#e9f0f7;font:16px/1.6 system-ui}header{margin-bottom:2rem}h1{font-size:2.8rem;line-height:1.1;letter-spacing:-.05em}p{color:#a5b5c9}.eyebrow{letter-spacing:.15em;font-size:.75rem;color:#9ec5f3;text-transform:uppercase}table{border-collapse:collapse;width:100%;margin:2rem 0}td,th{padding:1rem;border-bottom:1px solid #34455b;text-align:left}code{overflow-wrap:anywhere}footer{border-top:1px solid #34455b;margin-top:3rem;padding-top:1rem;font-size:.9rem;color:#a5b5c9}</style><main><header><div class="eyebrow">MathGraph Check / Bounded Intent Audit</div><h1>'+esc(headline)+'</h1><p>Evidence for exact source: <code>'+esc(sha)+'</code></p></header><table><thead><tr><th>Claim</th><th>Finding</th><th>Boundary</th></tr></thead><tbody>'+rows+'</tbody></table><footer>ADVISORY ONLY · Intent fidelity: NOT ESTABLISHED · No merge authorization · Source changes require requalification.</footer></main></html>';
}
