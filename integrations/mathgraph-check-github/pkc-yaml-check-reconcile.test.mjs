import test from "node:test";
import assert from "node:assert/strict";
import {reconcileCarrierCheck} from "./pkc-yaml-publish-adapter.mjs";

const SHA="05a6057e94d899ded94374db4a831963034aea93";
const EXTERNAL="metalogiclabs/mathgraph#178@"+SHA;
const check={name:"MathGraph Check / evidence scope",status:"completed",conclusion:"neutral",
  output:{title:"RESEARCH_BOUNDED",summary:"authenticated evidence 1"}};
const previous={id:42,app:{id:5308912},name:check.name,status:"completed",
  conclusion:"neutral",head_sha:SHA,external_id:EXTERNAL,
  details_url:"https://github.com/metalogiclabs/mathgraph/runs/42",output:check.output};

test("identical current neutral App-owned Check can be reused",()=>{
  assert.deepEqual(reconcileCarrierCheck(check,previous,SHA),{operation:"EXISTING",id:42});
});
test("same-SHA evidence or link change must update the existing Check",()=>{
  assert.deepEqual(reconcileCarrierCheck(check,{...previous,output:{...check.output,
    summary:"old evidence"}},SHA),{operation:"UPDATE",id:42});
  assert.deepEqual(reconcileCarrierCheck(check,{...previous,details_url:"https://mathgraph.org/"},SHA),
    {operation:"UPDATE",id:42});
});
test("stale identity, foreign App or non-neutral prior Check denies reconciliation",()=>{
  for(const bad of [{app:{id:999}},{head_sha:"a".repeat(40)},
    {external_id:"other/repo#178@"+SHA},{conclusion:"success"},{status:"in_progress"}]){
    assert.throws(()=>reconcileCarrierCheck(check,{...previous,...bad},SHA),
      /EXISTING_CARRIER_CHECK_INVALID/);
  }
});
