// Evaluates an operator-configured evidence packet, not the owner's actual intent.
// Callers must source the packet outside untrusted PR content. This module does
// not authenticate its issuer and cannot grant GitHub merge/deployment authority.
const STATES=new Set([
  "WARRANTED_TRUE","WARRANTED_FALSE","INSUFFICIENT","CONFLICTING","OUT_OF_SCOPE"
]);
const IDENT=/^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$/;
const SHA=/^[a-f0-9]{40}$/i;
const REPO=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const residual=(code)=>({code});
const unresolved=(code)=>({
  boundary:"OPERATOR_CONFIGURED_PACKET_ONLY",decision:"ABSTAIN",
  residuals:[residual(code)],future:{grant_expires_at:null}
});
const validIdentifier=x=>typeof x==="string" && IDENT.test(x);
const validMoment=x=>Number.isSafeInteger(x) && x>=0;
const hasOwn=(x,k)=>Object.prototype.hasOwnProperty.call(x,k);

export function assessWarrant(snapshot,ownerContract,asOf) {
  // No PR-authored field is ever an independent owner contract.
  if (ownerContract===undefined || ownerContract===null)
    return unresolved("UNRESOLVED_OWNER_CONTRACT");
  if (!validMoment(asOf) || !ownerContract || typeof ownerContract!=="object" ||
      Array.isArray(ownerContract) || ownerContract.schema!=="mathgraph.owner-contract.v1")
    return unresolved("UNRESOLVED_MODEL_COVERAGE");

  const c=ownerContract,sub=c.subject,g=c.grant;
  if (!sub || typeof sub!=="object" || !REPO.test(String(sub.repository||"")) ||
      !Number.isSafeInteger(sub.pr) || sub.pr<1 || !SHA.test(String(sub.sha||"")))
    return unresolved("UNRESOLVED_MODEL_COVERAGE");
  if (sub.repository!==snapshot.repository || sub.pr!==snapshot.number ||
      sub.sha!==snapshot.sha)
    return unresolved("UNRESOLVED_OWNER_CONTRACT_BINDING");

  if (![c.policy_version,c.actor,c.action,c.scope].every(validIdentifier) ||
      !Array.isArray(c.conditions) || c.conditions.length===0 ||
      c.conditions.length>64 || !g || typeof g!=="object" || Array.isArray(g))
    return unresolved("UNRESOLVED_MODEL_COVERAGE");
  if (![g.id,g.issuer,g.actor,g.action,g.scope].every(validIdentifier) ||
      !validMoment(g.issued_at) || !validMoment(g.expires_at) ||
      g.expires_at<=g.issued_at ||
      (hasOwn(g,"revoked_at") && g.revoked_at!==null &&
        (!validMoment(g.revoked_at) || g.revoked_at<g.issued_at)))
    return unresolved("UNRESOLVED_MODEL_COVERAGE");
  const names=new Set();
  for (const condition of c.conditions) {
    if (!condition || typeof condition!=="object" ||
        ![condition.name,condition.scope,condition.source].every(validIdentifier) ||
        names.has(condition.name) || !STATES.has(condition.status) ||
        typeof condition.on_false!=="string" ||
        !/^FAIL_[A-Z0-9_]+$/.test(condition.on_false) ||
        typeof condition.on_unresolved!=="string" ||
        !/^UNRESOLVED_[A-Z0-9_]+$/.test(condition.on_unresolved))
      return unresolved("UNRESOLVED_MODEL_COVERAGE");
    names.add(condition.name);
  }

  const residuals=[];
  if (g.actor!==c.actor || g.action!==c.action || g.scope!==c.scope)
    residuals.push(residual("UNRESOLVED_AUTHORITY"));
  else if (g.revoked_at!==undefined && g.revoked_at!==null && g.revoked_at<=asOf)
    residuals.push(residual("FAIL_GRANT_REVOKED"));
  else if (asOf>=g.expires_at)
    residuals.push(residual("FAIL_GRANT_EXPIRED"));
  else if (asOf<g.issued_at)
    residuals.push(residual("UNRESOLVED_CURRENT_GRANT_STATUS"));

  for (const condition of c.conditions) {
    if (condition.scope!==c.scope) residuals.push(residual("UNRESOLVED_SOURCE_OUT_OF_SCOPE"));
    else if (condition.status==="WARRANTED_FALSE")
      residuals.push(residual(condition.on_false));
    else if (condition.status!=="WARRANTED_TRUE")
      residuals.push(residual(condition.on_unresolved));
  }
  const decision=residuals.some(r=>r.code.startsWith("FAIL_")) ? "REFUSE" :
    residuals.length ? "ABSTAIN" : "ADMIT";
  return {
    boundary:"OPERATOR_CONFIGURED_PACKET_ONLY",decision,residuals,
    future:{grant_expires_at:g.expires_at,grant_revoked_at:g.revoked_at??null},
    policy_version:c.policy_version,action:c.action,scope:c.scope,
    // Source labels are retained for private diagnostics, not emitted into
    // a public GitHub Check summary.
    evidence:c.conditions.map(x=>({name:x.name,scope:x.scope,status:x.status,source:x.source}))
  };
}
