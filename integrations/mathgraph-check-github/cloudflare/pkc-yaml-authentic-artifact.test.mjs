// Runs with independently downloaded, SHA-256 authenticated Actions archive.
// No GitHub Check is published: the entire GitHub REST interface is simulated.
import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {generateKeyPairSync} from "node:crypto";
import {processCarrierPR,SCOPE} from "./worker.mjs";
import {extractBoundReport,PIN} from "../pkc-yaml-live-boundary.mjs";
import {projectPKCYamlCheck} from "../pkc-yaml-check-projection.mjs";

const ZIP=process.env.MATHGRAPH_PKC_ZIP;
const META=process.env.MATHGRAPH_PKC_META;
const REPO="metalogiclabs/mathgraph";
const HEAD="05a6057e94d899ded94374db4a831963034aea93";
const ITEM={schema:"mathgraph.pkcyaml-pr-delivery.v1",repository:REPO,
  number:178,sha:HEAD,installationID:42,
  delivery:"123e4567-e89b-12d3-a456-426614174000",action:"opened"};
const PERMS={checks:"write",pull_requests:"read",actions:"read"};
const bytes=ZIP&&META?readFileSync(ZIP):null;
const meta=ZIP&&META?JSON.parse(readFileSync(META,"utf8")):null;

function setup(options={}){
  const key=generateKeyPairSync("rsa",{modulusLength:2048}).privateKey;
  const env={GITHUB_APP_ID:String(SCOPE.appID),GITHUB_APP_CLIENT_ID:SCOPE.clientID,
    GITHUB_APP_PRIVATE_KEY:key.export({type:"pkcs1",format:"pem"}).toString(),
    PKC_YAML_CARRIER_ENABLED:"true"};
  const calls=[],checks=options.unrelated?[{id:13,name:"Other Tool",external_id:"other",
    app:{id:888},output:{title:"KEEP",summary:"independent"}}]:[];
  let nextID=400;
  const json=(obj,status=200)=>new Response(JSON.stringify(obj),{status});
  const fetcher=async(raw,init={})=>{
    const u=new URL(raw),p=u.pathname,m=init.method||"GET";
    assert.equal(u.origin,"https://api.github.com");
    calls.push({p,m});
    assert.match(init.headers.Authorization,/^Bearer /);
    if(p==="/app")return json({id:SCOPE.appID,owner:{login:"metalogiclabs"},permissions:PERMS});
    if(p==="/repos/"+REPO+"/installation")return json({id:42,app_id:SCOPE.appID,
      account:{login:"metalogiclabs"},suspended_at:null,permissions:PERMS});
    if(p==="/app/installations/42/access_tokens"){
      assert.deepEqual(JSON.parse(init.body),{repositories:["mathgraph"],permissions:PERMS});
      return json({token:"mock-carrier-scoped-token",permissions:PERMS});
    }
    if(p==="/installation/token")return new Response(null,{status:204});
    if(p==="/repos/"+REPO+"/pulls/178")return json({state:"open",
      head:{sha:HEAD,repo:{full_name:REPO}},base:{repo:{full_name:REPO}}});
    if(p==="/repos/"+REPO+"/pulls/178/files")return json([{
      filename:".mathgraph-check/pkc-yaml/EXTERNAL-RESEARCH-RECEIPT.md"}]);
    if(p==="/repos/"+REPO+"/actions/artifacts/"+PIN.artifact)return json({
      ...meta,digest:options.tamperedMetadata?"sha256:"+"a".repeat(64):meta.digest});
    if(p==="/repos/"+REPO+"/actions/artifacts/"+PIN.artifact+"/zip")
      return new Response(bytes,{headers:{"Content-Type":"application/zip"}});
    if(p==="/repos/"+REPO+"/commits/"+HEAD+"/check-runs")
      return json({total_count:checks.length,check_runs:checks});
    if(p==="/repos/"+REPO+"/check-runs" && m==="POST"){
      const check={...JSON.parse(init.body),id:++nextID,app:{id:SCOPE.appID}};
      checks.push(check);return json(check);
    }
    const match=p.match(/^\/repos\/metalogiclabs\/mathgraph\/check-runs\/([1-9][0-9]*)$/);
    if(match){
      const check=checks.find(c=>c.id===Number(match[1]));
      assert.ok(check,"Check must exist");
      if(m==="PATCH")Object.assign(check,JSON.parse(init.body));
      return json(options.badReadback&&m==="GET"?{...check,app:{id:999}}:check);
    }
    throw Error("UNEXPECTED_FIXTURE_REQUEST:"+m+" "+p);
  };
  return {env,calls,checks,fetcher};
}

test("real archive: signed carrier produces one neutral Check and replay reuses it",
  {skip:!bytes},async()=>{
    const m=setup({unrelated:true});
    const first=await processCarrierPR(ITEM,m.env,{fetcher:m.fetcher});
    assert.equal(first.outcome,"APP_CHECK_VERIFIED");
    const owned=m.checks.filter(c=>c.app.id===SCOPE.appID);
    assert.equal(owned.length,1);
    assert.equal(owned[0].head_sha,HEAD);
    assert.equal(owned[0].conclusion,"neutral");
    assert.match(owned[0].output.summary,/Historical native evidence replay/);
    assert.equal((await processCarrierPR(ITEM,m.env,{fetcher:m.fetcher})).outcome,
      "EXISTING_CHECK");
    assert.equal(m.checks.length,2);
    assert.equal(m.checks[0].output.title,"KEEP");
    owned[0].output={...owned[0].output,summary:"stale evidence at same SHA"};
    assert.equal((await processCarrierPR(ITEM,m.env,{fetcher:m.fetcher})).outcome,
      "UPDATED_CHECK");
    assert.match(owned[0].output.summary,/Historical native evidence replay/);
    assert.equal(m.checks.length,2);
  });

test("real archive: invalid metadata and incorrect Check readback fail closed",
  {skip:!bytes},async()=>{
    const wrong=setup({tamperedMetadata:true});
    await assert.rejects(processCarrierPR(ITEM,wrong.env,{fetcher:wrong.fetcher}),
      /ARTIFACT_AUTHORITY_MISMATCH/);
    assert.equal(wrong.checks.length,0);
    const readback=setup({badReadback:true});
    await assert.rejects(processCarrierPR(ITEM,readback.env,{fetcher:readback.fetcher}),
      /APP_CHECK_READBACK_MISMATCH/);
  });

test("real archive: a forged verifier assertion cannot promote a report",
  {skip:!bytes},()=>{
    const report=extractBoundReport(bytes);
    const bad=projectPKCYamlCheck({...report,authority:"APP_SELF_VERIFIED"},
      {carrierRepo:REPO,carrierHead:HEAD,authorized:true});
    assert.equal(bad.output.title,"PKC_L4YAML_EVIDENCE_UNKNOWN");
  });
