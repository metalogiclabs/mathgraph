// One native GitHub Check under the registered MathGraph App identity.
// Credentials arrive only through Actions' secret-scoped installation token.
// No GitHub Actions GITHUB_TOKEN write permission, webhook hosting, or PR code execution.
import { appendFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { githubAPI, loadPR, analyze, checkOutput } from "./core.mjs";

export const PILOT = Object.freeze({
  appID: 5308912,
  repository: "metalogiclabs/go-ethereum",
  pr: 19,
  sha: "a04aa77aaebd81d11274560e8d24d90c6f417589"
});
function requireCondition(ok, code) {
  if (!ok) throw new Error(code);
}
export async function publishAppCheck({
  token,
  request = githubAPI,
  loadSnapshot = loadPR
} = {}) {
  requireCondition(typeof token === "string" && token.length >= 10,
    "GITHUB_APP_INSTALLATION_TOKEN_MISSING");
  const { repository, pr, sha, appID } = PILOT;
  const snapshot = await loadSnapshot(repository, pr, token);
  requireCondition(snapshot?.sha === sha, "SOURCE_HEAD_MOVED_FAIL_CLOSED");
  requireCondition(snapshot.files_visibility === "COMPLETE" &&
    snapshot.ci_visibility === "COMPLETE", "PR_EVIDENCE_INCOMPLETE");

  const result = analyze(snapshot);
  requireCondition(result.authority === "ADVISORY_ONLY" &&
    result.ci.state === "GITHUB_REPORTED_SUCCESS_AT_EXACT_HEAD" &&
    result.finding.code === "DECLARED_VERIFICATION_RESIDUAL",
    "EXPECTED_EVIDENCE_SCOPE_NOT_ESTABLISHED");
  const obligations = result.declared_limits.map(v => v.name);
  requireCondition(obligations.includes("remote_conflicting_fcu") &&
    obligations.includes("concurrent_fcu"), "EXPECTED_RESIDUALS_NOT_PRESENT");

  const live = await request("/repos/" + repository + "/pulls/" + pr, token);
  requireCondition(live?.head?.sha === sha, "STALE_PR_HEAD_FAIL_CLOSED");

  const check = checkOutput(result);
  requireCondition(check.conclusion === "neutral" &&
    check.status === "completed" &&
    check.name === "MathGraph Check / evidence scope",
    "FORBIDDEN_CHECK_AUTHORITY");
  const externalId = repository + "#" + pr + "@" + sha;
  const listPath = "/repos/" + repository + "/commits/" + sha +
    "/check-runs?per_page=100&filter=all&check_name=" +
    encodeURIComponent(check.name);

  const matches = async () => {
    const checks = await request(listPath, token);
    requireCondition(Array.isArray(checks?.check_runs) &&
      Number.isSafeInteger(checks.total_count) &&
      checks.total_count <= checks.check_runs.length,
      "CHECK_RUNS_INCOMPLETE");
    return checks.check_runs.filter(x =>
      x.name === check.name && x.external_id === externalId &&
      x.app?.id === appID);
  };

  const previous = await matches();
  if (previous.length) {
    requireCondition(previous.length === 1 && previous[0].head_sha === sha &&
      previous[0].status === "completed" && previous[0].conclusion === "neutral",
      "PRIOR_APP_CHECK_INCONSISTENT");
    return { outcome: "EXISTING", checkId: previous[0].id,
      appID, repository, pr, sha, conclusion: "neutral" };
  }

  const created = await request("/repos/" + repository + "/check-runs",
    token, "POST", { ...check, external_id: externalId, head_sha: sha });
  requireCondition(Number.isSafeInteger(created?.id) &&
    created.app?.id === appID &&
    created.head_sha === sha &&
    created.status === "completed" && created.conclusion === "neutral",
    "POST_DID_NOT_ESTABLISH_REGISTERED_APP_IDENTITY");

  const readback = await matches();
  requireCondition(readback.length === 1 &&
    readback[0].id === created.id &&
    readback[0].head_sha === sha &&
    readback[0].conclusion === "neutral" &&
    readback[0].status === "completed",
    "GITHUB_APP_CHECK_READBACK_MISMATCH");
  return { outcome: "CREATED", checkId: created.id,
    appID, repository, pr, sha, conclusion: "neutral" };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const result = await publishAppCheck({
      token: process.env.MATHGRAPH_APP_INSTALLATION_TOKEN
    });
    console.log("MATHGRAPH_REGISTERED_APP_CHECK " + JSON.stringify(result));
    if (process.env.GITHUB_STEP_SUMMARY) {
      appendFileSync(process.env.GITHUB_STEP_SUMMARY,
        "### MathGraph Check — registered App verified\n" +
        "App ID: " + result.appID + "; check: " + result.checkId +
        "; outcome: " + result.outcome + "; conclusion: neutral\n" +
        "Exact PR head: " + result.sha + "\n");
    }
  } catch (err) {
    // No JSON bodies, tokens, private keys, or authentication headers in logs.
    console.error("MATHGRAPH_APP_CHECK_NOT_QUALIFIED " +
      String(err.message || "UNKNOWN"));
    process.exitCode = 1;
  }
}
