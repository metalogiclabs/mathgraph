import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {inspectArm,admitLeanPatch,guardBlocks} from '../../integrations/mathgraph-check-github/lean-investigator-v1/contracts.mjs';
const hash=s=>createHash('sha256').update(s).digest('hex');
export const planFor=policy=>({summary:'Frozen finite binding audit; denied probes are diagnostic only',tests:policy.proposals.map(p=>({id:p.id,hypothesis:'Binding audit '+p.id,contract:policy.relation,expression:p.expression}))});
export function inspectNative({policy,snapshot,plan,state,context,native,repair,patch}){
 const ensure=(b,why)=>{if(!b)throw Error(why);};
 ensure(isDeepStrictEqual(plan,planFor(policy)),'PLAN_CHANGED');
 ensure(snapshot.repository===policy.subject.repository&&snapshot.path===policy.subject.path&&snapshot.head_sha===policy.subject.revision&&snapshot.toolchain===policy.toolchain,'SUBJECT_CHANGED');
 ensure(hash(snapshot.source)===policy.subject.sha256&&snapshot.source_sha256===policy.subject.sha256&&hash(snapshot.cli_source)===policy.cli_sha256,'SOURCE_CHANGED');
 ensure(snapshot.module==='Scripts.Ledger'&&snapshot.namespace==='Scripts.Ledger','MODULE_CHANGED');
 ensure(state.test_digest===hash(JSON.stringify(plan.tests)),'TEST_DIGEST_CHANGED');
 for(const n of [native,repair])ensure(isDeepStrictEqual(n.context,context)&&n.source_sha===snapshot.head_sha&&n.test_digest===state.test_digest,'NATIVE_CONTEXT_CHANGED');
 const content=admitLeanPatch(policy.patch,snapshot.source);
 ensure(content===patch.content&&hash(content)===patch.patched_sha256,'PATCH_CHANGED');
 ensure(repair.patched_sha256===patch.patched_sha256,'NATIVE_PATCH_CHANGED');
 const initial=inspectArm(native.arm,{profile:snapshot,plan,source:snapshot.source});
 const original=inspectArm(repair.original,{profile:snapshot,plan,source:snapshot.source});
 const repaired=inspectArm(repair.repaired,{profile:snapshot,plan,source:content});
 const withdrawn=inspectArm(repair.withdrawn,{profile:snapshot,plan,source:snapshot.source});
 return {complete:[initial,original,repaired,withdrawn].every(a=>a.complete),context,subject:policy.subject,
  policy_sha256:hash(JSON.stringify(policy)),patch_sha256:patch.patched_sha256,
  initial,original,repaired,withdrawn,source_guard_count:guardBlocks(snapshot.source).length,
  repository_gate_exits:[native.arm.repository_gate_exit,repair.original.repository_gate_exit,repair.repaired.repository_gate_exit,repair.withdrawn.repository_gate_exit]};
}
