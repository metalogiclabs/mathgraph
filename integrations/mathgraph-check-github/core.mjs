// MathGraph Check GitHub App: exact-head evidence, advisory only.
// A GitHub CI success is not independent verification of its declared objectives.
import { createHash } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { analyze, checkOutput } from "./analysis.mjs";
export { analyze, checkOutput } from "./analysis.mjs";
export class GitHubHttpError extends Error {
  constructor(status) { super("GITHUB_HTTP_"+status); this.status=status; }
}
export async function githubAPI(path, token="", method="GET", body) {
  if (!path.startsWith("/repos/") && !path.startsWith("/app/installations/"))
    throw new Error("INVALID_GITHUB_API_PATH");
  const headers={"Accept":"application/vnd.github+json",
    "X-GitHub-Api-Version":"2022-11-28",
    "User-Agent":"MathGraph-Check-v0"};
  if (token) headers.Authorization="Bearer "+token;
  if (body!==undefined) headers["Content-Type"]="application/json";
  const resp=await fetch("https://api.github.com"+path,{
    method,headers,body:body===undefined?undefined:JSON.stringify(body),
    signal:AbortSignal.timeout(15000)
  });
  if (!resp.ok) throw new GitHubHttpError(resp.status);
  return resp.json();
}

export async function loadPR(repository,number,token="") {
  if (!REPO.test(repository) || !Number.isSafeInteger(number) || number<1)
    throw new Error("INVALID_REPO_PR");
  const prefix="/repos/"+repository;
  const pr=await githubAPI(prefix+"/pulls/"+number,token);
  if (!SHA.test(pr?.head?.sha || "")) throw new Error("MISSING_HEAD_SHA");
  const files=[];
  let files_visibility="COMPLETE";
  for (let page=1;page<=3;page++) {
    const batch=await githubAPI(prefix+"/pulls/"+number+"/files?per_page=100&page="+page,token);
    if (!Array.isArray(batch)) throw new Error("BAD_FILE_RESPONSE");
    files.push(...batch);
    if (batch.length<100) break;
    if (page===3) files_visibility="TRUNCATED_AT_300";
  }
  let runs=[],ci_visibility="COMPLETE";
  try {
    const data=await githubAPI(prefix+"/actions/runs?head_sha="+pr.head.sha+"&per_page=100",token);
    if (!Array.isArray(data.workflow_runs)) throw new Error("BAD_ACTIONS_RESPONSE");
    runs=data.workflow_runs;
    if ((data.total_count||0)>runs.length) ci_visibility="TRUNCATED";
  } catch(e) {
    if (e instanceof GitHubHttpError && (e.status===403 || e.status===404))
      ci_visibility="UNKNOWN_NO_ACTIONS_ACCESS";
    else throw e;
  }
  return {repository,number,sha:pr.head.sha,files,runs,files_visibility,ci_visibility};
}


async function shadowCLI() {
  const opts=new Map();
  for(let i=2;i<process.argv.length;i+=2) opts.set(process.argv[i],process.argv[i+1]);
  const repository=opts.get("--repo"),number=Number(opts.get("--pr")),out=opts.get("--out");
  if (!out || !Number.isSafeInteger(number)) throw new Error("REQUIRE_REPO_PR_OUT");
  const snapshot=await loadPR(repository,number,process.env.GH_PUBLIC_TOKEN||"");
  const result=analyze(snapshot);
  const raw=JSON.stringify(snapshot);
  result.transport={sha256:createHash("sha256").update(raw).digest("hex"),
    meaning:"TRANSPORT_HASH_NOT_PUBLISHER_AUTHENTICATION"};
  await mkdir(dirname(out),{recursive:true});
  await writeFile(out,JSON.stringify(result,null,2)+"\n");
  await writeFile(out.replace(/\.json$/,"")+".md",checkOutput(result).output.summary+"\n");
  console.log(JSON.stringify({source:result.source,ci:result.ci.state,
    finding:result.finding.code,declared_limits:result.declared_limits.map(x=>x.name)}));
}
if (process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url))
  await shadowCLI();
