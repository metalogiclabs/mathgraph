// Independent pinned-intent audit linked to a freshly observed GitHub PR source.
// This trusted-host adapter has no in-band requalification switch.
// Caller MUST supply external, independently qualified oracle/verifier/receipt
// authority: this module does not authenticate those records on its own.
import {auditIntent} from './intent-contract-v1.mjs';
import {githubSnapshot} from './authenticated-cycle-v1.mjs';
import {monitor} from './check-resolve-monitor-v1.mjs';

const fail=(reason,detail={})=>({status:'UNKNOWN',reason,permission:'ADVISORY_ONLY',
 intent_verification:'NOT_ESTABLISHED',checked_scope:'NONE',transitions:[],...detail});

// A claim ID is a locator, not the identity of the requirement. Unless an
// independent owner approves a revised basis, keep statements and their
// input/oracle obligations extensionally pinned across A -> B. Source and
// independently qualified verifier implementations may evolve separately.
function intentBasis(contract){
 const claims=(contract?.claims??[]).map(c=>({id:c.id,statement:c.statement,
  requires:[...c.requires].sort()})).sort((a,b)=>a.id.localeCompare(b.id));
 const probes=(contract?.probes??[]).map(p=>({id:p.id,
  input_sha256:p.input_sha256,oracle_sha256:p.oracle_sha256}))
  .sort((a,b)=>a.id.localeCompare(b.id));
 return JSON.stringify({claims,probes});
}

export async function qualifyIntentSourceTransition({repository,pr,token,before,after,
 trustedAuthorities,fetcher}={}) {
 const observed=await githubSnapshot({repository,pr,token,fetcher});
 const source=observed.input.subject;
 const prior=before?.contract?.subject,next=after?.contract?.subject;
 // Neither intent contract nor an in-band true flag can choose the current SHA.
 // Only the independently queried GitHub PR readback selects it.
 if(next?.repository!==repository||next?.pr!==pr||
    next?.base_sha!==source.base_sha||next?.head_sha!==source.head_sha)
  return fail('AUDIT_SOURCE_NOT_CURRENT_GITHUB_PR',{source});
 if(prior?.repository!==repository||prior?.pr!==pr)
  return fail('PRIOR_AUDIT_WRONG_PR',{source});
 if(intentBasis(before.contract)!==intentBasis(after.contract))
  return fail('INTENT_BASIS_CHANGED_WITHOUT_OWNER_APPROVAL',{source});
 if(observed.result.status!=='OBSERVED')
  return fail('EXACT_HEAD_CHECKS_NOT_OBSERVED',{source,
   github_check_status:observed.result.status});
 // Authority is a separate trusted-host input: never read it from the
 // developer-controlled before/after contract or receipt packet.
 const oldAudit=auditIntent(before.contract,before.receipts,trustedAuthorities?.before);
 const newAudit=auditIntent(after.contract,after.receipts,trustedAuthorities?.after);
 if(oldAudit.source?.repository!==repository||oldAudit.source?.pr!==pr)
  return fail('PRIOR_AUDIT_NOT_BOUND',{source});
 // auditIntent performs exact contract/source/receipt checks against host-supplied
 // verifier/oracle qualifications. There is no caller-controlled override here.
 const requalified=newAudit.status==='OBSERVED'&&
  newAudit.reason==='BOUNDED_PROBE_AUDIT'&&
  newAudit.results.length>0&&newAudit.results.every(x=>x.status==='OBSERVED');
 const transition=monitor(oldAudit,{...newAudit,independent_requalification:requalified});
 return {...transition,reason:requalified?'INDEPENDENT_PINNED_PROBES_AT_CURRENT_HEAD':
   newAudit.status==='BLOCKED'?'QUALIFIED_PINNED_COUNTEREXAMPLE':'B_PROBES_NOT_REQUALIFIED',
  source,contract_sha256:newAudit.contract_sha256??null,
  checked_scope:newAudit.checked_scope??'NONE',
  intent_verification:'NOT_ESTABLISHED',
  // auditIntent deliberately does not yet verify revocation or post-read
  // freshness; only a trusted host may supply its authority.
  freshness:'NOT_CHECKED_AFTER_READ',revocation:'NOT_CHECKED'};
}
