// Read-only source-exact verification of already-installed App after PR edit.
const repo="metalogiclabs/go-ethereum",number=20,sha="b57c5493d2bc066c184cbc9335bdf635f045a026",appID=5308912;
const token=process.env.MATHGRAPH_APP_INSTALLATION_TOKEN;
if(!token)throw Error("NO_SCOPED_APP_TOKEN");
async function api(path){const r=await fetch("https://api.github.com/repos/"+repo+path,{headers:{Authorization:"Bearer "+token,Accept:"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"},signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error("GITHUB_HTTP_"+r.status);return r.json();}
const pr=await api("/pulls/"+number);if(pr.head?.sha!==sha||pr.state!=="open")throw Error("SOURCE_HEAD_CHANGED");
const d=await api("/commits/"+sha+"/check-runs?per_page=100&filter=all");
if(!Array.isArray(d.check_runs)||!Number.isSafeInteger(d.total_count)||d.total_count>d.check_runs.length)throw Error("INCOMPLETE_CHECK_READBACK");
const checks=d.check_runs.filter(c=>c.name==="MathGraph Check / evidence scope"&&c.app?.id===appID&&c.external_id===repo+"#"+number+"@"+sha);
if(checks.length!==1)throw Error("APP_CHECK_IDENTITY_COUNT_"+checks.length);
const c=checks[0];
if(c.conclusion!=="neutral"||c.status!=="completed"||typeof c.output?.summary!=="string")throw Error("NON_ADVISORY_OR_INCOMPLETE_CHECK");
const result={repo,number,sha,check_id:c.id,app_id:c.app.id,status:c.status,conclusion:c.conclusion,title:c.output.title,summary_sha256:await crypto.subtle.digest("SHA-256",new TextEncoder().encode(c.output.summary)).then(b=>Buffer.from(b).toString("hex")),updated_at:c.completed_at??null};
console.log("MATHGRAPH_MONITOR_LIVE_READBACK "+JSON.stringify(result));
