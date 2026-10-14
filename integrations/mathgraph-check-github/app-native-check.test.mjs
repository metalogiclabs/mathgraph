import test from "node:test";
import assert from "node:assert/strict";
import { publishAppCheck, PILOT } from "./app-native-check.mjs";

function makeFixture(options = {}) {
  const recorded = [];
  const seen = [];
  let seq = 1000;
  const data = {
    repository: PILOT.repository, number: PILOT.pr, sha: PILOT.sha,
    files_visibility: "COMPLETE", ci_visibility: "COMPLETE",
    files: [
      { filename: ".github/workflows/bal-engine-crossfork-v19.yml",
        patch: "+echo concurrent_fcu=UNKNOWN;remote_conflicting_fcu=UNKNOWN\n" },
      { filename: "eth/catalyst/bal_engine_crossfork_v19_test.go",
        patch: "+func TestBALV19CrossForkAdmissionPredicate(t *testing.T) {}" }
    ],
    runs: [{
      id:38202260024, name:"BAL V19 Engine Crossfork Qualification (Fork Only)",
      head_sha:PILOT.sha, status:"completed", conclusion:"success"
    }]
  };
  const request = async (path, token, method = "GET", body) => {
    assert.equal(token, "app-installation-test-token");
    seen.push({path, method});
    if (path === "/repos/" + PILOT.repository + "/pulls/" + PILOT.pr)
      return {head:{sha:options.stale ? "f".repeat(40) : PILOT.sha}};
    if (path.startsWith("/repos/" + PILOT.repository + "/commits/" +
        PILOT.sha + "/check-runs?")) {
      const url = new URL("https://api.github.com"+path);
      assert.equal(url.searchParams.get("filter"),"all");
      assert.equal(url.searchParams.get("check_name"),"MathGraph Check / evidence scope");
      return {total_count:recorded.length, check_runs:recorded};
    }
    if (path === "/repos/" + PILOT.repository + "/check-runs") {
      assert.equal(method,"POST");
      const c={...body,id:++seq,
        app:{id:options.wrongApp ? 15368 : PILOT.appID}};
      recorded.push(c);
      return c;
    }
    throw new Error("UNEXPECTED_MOCKED_ROUTE");
  };
  const loadSnapshot = async (repo,pr,token) => {
    assert.equal(repo,PILOT.repository);
    assert.equal(pr,PILOT.pr);
    assert.equal(token,"app-installation-test-token");
    return {...data,sha:options.moved ? "f".repeat(40) : PILOT.sha};
  };
  return {recorded,seen,request,loadSnapshot};
}
const execute = fx => publishAppCheck({
  token:"app-installation-test-token",
  request:fx.request,loadSnapshot:fx.loadSnapshot
});

test("creates one native neutral Check bound to App 5308912 and exact SHA",async()=>{
  const fx=makeFixture(), result=await execute(fx);
  assert.equal(result.outcome,"CREATED");
  assert.equal(result.appID,5308912);
  assert.equal(result.sha,PILOT.sha);
  assert.equal(fx.recorded.length,1);
  assert.equal(fx.recorded[0].external_id,
    PILOT.repository+"#19@"+PILOT.sha);
  assert.equal(fx.recorded[0].conclusion,"neutral");
  assert.match(fx.recorded[0].output.summary,/concurrent_fcu=UNKNOWN/);
  assert.equal(fx.seen.filter(x=>x.method==="POST").length,1);
});

test("same source and App identity is idempotent on retry",async()=>{
  const fx=makeFixture();
  await execute(fx);
  const again=await execute(fx);
  assert.equal(again.outcome,"EXISTING");
  assert.equal(fx.recorded.length,1);
});

test("moving PR head or stale snapshot refuses publication",async()=>{
  for (const options of [{stale:true},{moved:true}]) {
    const fx=makeFixture(options);
    await assert.rejects(execute(fx),/(STALE_PR_HEAD|SOURCE_HEAD_MOVED)/);
    assert.equal(fx.recorded.length,0);
  }
});

test("a check attributed to GitHub Actions cannot qualify registered App",async()=>{
  const fx=makeFixture({wrongApp:true});
  await assert.rejects(execute(fx),/POST_DID_NOT_ESTABLISH_REGISTERED_APP_IDENTITY/);
});

test("no App token is a hard blocker",async()=>{
  await assert.rejects(publishAppCheck({token:""}),/INSTALLATION_TOKEN_MISSING/);
});
