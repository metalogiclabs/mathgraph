import test from "node:test";
import assert from "node:assert/strict";
import {spawnSync} from "node:child_process";
import {existsSync} from "node:fs";
import {resolve,dirname,join} from "node:path";
import {fileURLToPath} from "node:url";

const here=dirname(fileURLToPath(import.meta.url));
const script=join(here,"consequential-metatron-replay.py");
const checkout=process.env.METATRON_SOURCE_CHECKOUT||resolve(here,"../../../metatron");
const cases=()=>({schema:"mathgraph.two-target-replay.v1",research_only:true,
  cases:[
    {id:"goeth_v19",decision:"ABSTAIN",
      frame_sha256:"b6ee6aee99405607e924b8eba6a6b668522b0c40fdace4c7f0d9ecb3bf2e50cd",
      source:"metalogiclabs/go-ethereum#19@a04aa77aaebd81d11274560e8d24d90c6f417589"},
    {id:"goccy_pr958",decision:"ADMIT",
      frame_sha256:"0f36816614d9b7464a437f60680b663e25783161f9831c2bff6067f912c1736c",
      source:"goccy/go-yaml#958@a34b94ecb553bb5a693296c30232a89026db79ca"}
  ]});
function execute(input,sourcePath=checkout){
  return spawnSync("python3",[script,"--checkout",sourcePath],{
    encoding:"utf8",input:JSON.stringify(input),timeout:20000
  });
}

test("actual pinned Metatron Nucleus cuts only revoked causal descendants after cold replay",t=>{
  if(!existsSync(join(checkout,"runtime/metatron/nucleus.py"))){
    assert.notEqual(process.env.METATRON_REQUIRED,"1",
      "CI_REQUIRED_PINNED_METATRON_CHECKOUT_MISSING");
    return t.skip("requires independent pinned Metatron checkout");
  }
  const r=execute(cases());
  assert.equal(r.status,0,r.stderr);
  const result=JSON.parse(r.stdout);
  assert.equal(result.source_commit,"b9d1b5cc10477188be6e55617699be60e70f6dad");
  assert.equal(result.nucleus_sha256,"13f840fa61ef28803a17a7a7266f80e19fdcbdde90703969dbd83f232f44300d");
  assert.deepEqual(result.initial_live,[
    "goeth_v19_source","goeth_v19_receipt","goeth_v19_decision",
    "goccy_pr958_source","goccy_pr958_receipt","goccy_pr958_decision"]);
  assert.deepEqual(result.after_goeth_source_withdrawal,[
    "goccy_pr958_source","goccy_pr958_receipt","goccy_pr958_decision"]);
  assert.deepEqual(result.after_goccy_receipt_withdrawal,["goccy_pr958_source"]);
  assert.deepEqual(result.after_cold_restart,["goccy_pr958_source"]);
  assert.equal(result.history_count,8);
  assert.equal(result.no_external_authorization,true);
  // A second Python process imports the same pinned Nucleus and independently
  // parses/recloses the exported append-only history from bytes.
  const cold=execute({schema:"mathgraph.metatron-cold-replay.v1",
    history_jsonl:result.history_jsonl});
  assert.equal(cold.status,0,cold.stderr);
  const replay=JSON.parse(cold.stdout);
  assert.deepEqual(replay.live_names,["goccy_pr958_source"]);
  assert.equal(replay.history_sha256,result.history_sha256);
});

test("missing or non-pinned Metatron source cannot be treated as a replay",()=>{
  const r=execute(cases(),"/tmp/nonexistent-metatron-source-checkout");
  assert.notEqual(r.status,0);
  assert.match(r.stderr,/METATRON_PIN_MISMATCH|METATRON_SOURCE_UNAVAILABLE/);
});

test("invented universal-proof or production-action label is refused before lineage append",t=>{
  if(!existsSync(join(checkout,"runtime/metatron/nucleus.py"))){
    assert.notEqual(process.env.METATRON_REQUIRED,"1",
      "CI_REQUIRED_PINNED_METATRON_CHECKOUT_MISSING");
    return t.skip("requires independent pinned Metatron checkout");
  }
  const input=cases();input.cases[1].decision="UNIVERSAL_PROOF";
  const r=execute(input);
  assert.notEqual(r.status,0);
  assert.match(r.stderr,/INVALID_RESEARCH_DECISION/);
});
