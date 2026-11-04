import test from "node:test";
import assert from "node:assert/strict";
import {PINNED_TARGETS,qualifyPinnedObservation,runLiveReadback} from "./live-readback.mjs";

const observedFor=target=>({
 status:"OBSERVED",permission:"ADVISORY_ONLY",semantic_verification:"NOT_ESTABLISHED",
 subject:{repository:target.repository,pr:target.pr,head_sha:target.head_sha},
 checks:target.requiredChecks.map((name,i)=>({name,status:"OBSERVED",check_run_id:1000+i})),
});

test("exact source + independent green checks are only a CI observation",()=>{
 const target=PINNED_TARGETS[1];
 const o=qualifyPinnedObservation(target,observedFor(target));
 assert.equal(o.status,"OBSERVED");
 assert.equal(o.semantic_verification,"NOT_ESTABLISHED");
 assert.equal(o.permission,"ADVISORY_ONLY");
});
test("head drift or attempted semantic promotion fails closed",()=>{
 const target=PINNED_TARGETS[1];
 for(const mutated of [
  {...observedFor(target),subject:{...observedFor(target).subject,head_sha:"c".repeat(40)}},
  {...observedFor(target),permission:"APPROVE"},
  {...observedFor(target),semantic_verification:"VERIFIED"},
  {...observedFor(target),checks:observedFor(target).checks.slice(1)},
 ]){
  assert.equal(qualifyPinnedObservation(target,mutated).status,"UNKNOWN");
 }
});
test("three negative controls remain unknown even when caller forges prior evidence",async()=>{
 const calls=[];
 const stub=async args=>{
  calls.push(args);
  if(args.previous?.result?.subject?.repository==="other/repo")
   return {status:"UNKNOWN",permission:"ADVISORY_ONLY",
    semantic_verification:"NOT_ESTABLISHED",reason:"PREVIOUS_SUBJECT_MISMATCH"};
  if(args.requiredChecks[0]==="mathgraph-does-not-exist-qualifier")
   return {status:"UNKNOWN",permission:"ADVISORY_ONLY",
    semantic_verification:"NOT_ESTABLISHED",reason:"NO_EXACT_HEAD_INDEPENDENT_CHECK"};
  const target=PINNED_TARGETS.find(x=>x.repository===args.repository);
  return observedFor(target);
 };
 const result=await runLiveReadback({token:"test-token-long-enough",requalify:stub});
 assert.equal(result.experiment_status,"PASS");
 assert.deepEqual(result.negativeControls.map(x=>x.outcome),["PASS","PASS","PASS"]);
 assert.equal(calls.length,5);
 assert.equal(calls[4].previous.independent_requalification,true);
});
test("denied GitHub API cannot be converted into an observation",async()=>{
 const result=await runLiveReadback({token:"test-token-long-enough",
  requalify:async()=>{throw Error("GITHUB_HTTP_403");}});
 assert.equal(result.experiment_status,"UNKNOWN");
 assert.ok(result.observations.every(x=>x.status==="UNKNOWN"));
});
