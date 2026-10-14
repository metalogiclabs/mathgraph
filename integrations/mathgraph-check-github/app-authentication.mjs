// Authenticate directly as the registered GitHub App, then use the existing
// MathGraph Check publisher. No intermediate PEM or bearer-token outputs.
import { createPrivateKey } from "node:crypto";
import { appendFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { makeJWT } from "./webhook.mjs";
import { publishAppCheck, PILOT } from "./app-native-check.mjs";

export const APP_CLIENT_ID = "Iv23lioiUs5KfHD7mkkw";
export const TARGET_OWNER = "metalogiclabs";
const MAX_KEY_TEXT = 100000;
const REQUESTED_PERMISSIONS = Object.freeze({
  checks: "write", pull_requests: "read", actions: "read"
});

function must(ok, code) {
  if (!ok) throw new Error(code);
}

export function normalizePrivateKey(raw) {
  must(typeof raw === "string" && raw.trim().length > 0 &&
    raw.length < MAX_KEY_TEXT, "APP_PRIVATE_KEY_MISSING_OR_OVERSIZED");
  const value = raw.trim();
  const candidates = [];
  const add = (label, text) => {
    if (typeof text !== "string") return;
    if (candidates.some(c => c.value === text)) return;
    candidates.push({ label, value: text });
  };
  add("PEM", value);
  add("ESCAPED_NEWLINES", value.replace(/\\r\\n/g, "\n").replace(/\\n/g, "\n"));
  if ((value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))) {
    const inside = value.slice(1, -1);
    add("QUOTED_PEM", inside);
    add("QUOTED_ESCAPED_NEWLINES",
      inside.replace(/\\r\\n/g, "\n").replace(/\\n/g, "\n"));
    // A JSON-quoted PEM has doubled backslashes; decode only valid JSON
    // string literals, never execute or print the secret.
    if (value.startsWith('"')) {
      try {
        const parsed = JSON.parse(value);
        if (typeof parsed === "string") {
          add("JSON_QUOTED_PEM", parsed);
          add("JSON_QUOTED_ESCAPED_NEWLINES",
            parsed.replace(/\\r\\n/g, "\n").replace(/\\n/g, "\n"));
        }
      } catch {
        // Other quoting styles remain safe to reject.
      }
    }
  }
  if (/^[A-Za-z0-9+/=\s]+$/.test(value) && value.replace(/\s/g, "").length % 4 === 0) {
    const decoded = Buffer.from(value.replace(/\s+/g, ""), "base64").toString("utf8");
    add("BASE64_ENCODED_PEM", decoded);
    add("BASE64_ESCAPED_PEM", decoded.replace(/\\n/g, "\n"));
  }
  for (const candidate of [...candidates]) {
    // Repair an otherwise complete PEM accidentally flattened into one line.
    const compact = candidate.value.trim().match(
      /^-----BEGIN (RSA PRIVATE KEY|PRIVATE KEY)-----(.*?)-----END \1-----$/s
    );
    if (compact) {
      const body = compact[2].replace(/\s+/g, "");
      if (/^[A-Za-z0-9+/=]+$/.test(body) && body.length >= 64) {
        const lines = body.match(/.{1,64}/g);
        add(candidate.label + "_COMPACTED",
          "-----BEGIN " + compact[1] + "-----\n" +
          lines.join("\n") + "\n-----END " + compact[1] + "-----\n");
      }
    }
  }
  for (const c of candidates) {
    const pem = c.value.trim() + "\n";
    if (!/^-----BEGIN (?:RSA )?PRIVATE KEY-----/.test(pem) ||
        !/-----END (?:RSA )?PRIVATE KEY-----\s*$/.test(pem)) continue;
    try {
      const key = createPrivateKey(pem);
      if (key.asymmetricKeyType !== "rsa") continue;
      return { key, encoding: c.label };
    } catch {
      // Intentionally do not leak OpenSSL parser messages or secret text.
    }
  }
  throw new Error("APP_PRIVATE_KEY_UNPARSEABLE_OR_INCOMPLETE");
}

function permits(granted, label) {
  must(granted && granted.checks === "write" &&
    (granted.pull_requests === "read" || granted.pull_requests === "write") &&
    (granted.actions === "read" || granted.actions === "write"),
    label + "_MISSING_REQUIRED_PERMISSIONS");
}

export async function appHttp(path, credential, {
  method = "GET", body, fetcher = fetch
} = {}) {
  const permitted = path === "/app" ||
    path === "/repos/metalogiclabs/go-ethereum/installation" ||
    /^\/app\/installations\/[1-9][0-9]*\/access_tokens$/.test(path) ||
    path === "/installation/token";
  must(permitted, "INVALID_GITHUB_APP_API_PATH");
  must(typeof credential === "string" && credential.length > 0,
    "MISSING_GITHUB_APP_CREDENTIAL");
  const headers = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "MathGraph-Check-Registered-App-Gate",
    "Authorization": "Bearer " + credential
  };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetcher("https://api.github.com" + path, {
    method, headers, body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(20000)
  });
  if (!response.ok) {
    const endpoint = path === "/app" ? "APP_IDENTITY" :
      path.endsWith("/installation") ? "REPOSITORY_INSTALLATION" :
      path === "/installation/token" ? "TOKEN_REVOCATION" : "INSTALLATION_TOKEN";
    throw new Error("GITHUB_" + endpoint + "_HTTP_" + response.status);
  }
  if (response.status === 204) return { revoked: true };
  return await response.json();
}

export async function authenticateAndPublish({
  keyText,
  fetcher = fetch,
  publish = publishAppCheck
} = {}) {
  const material = normalizePrivateKey(keyText);
  const jwt = makeJWT(APP_CLIENT_ID, material.key);
  const api = (path, credential, options = {}) =>
    appHttp(path, credential, { ...options, fetcher });

  const app = await api("/app", jwt);
  must(app?.id === PILOT.appID && app.owner?.login === TARGET_OWNER,
    "WRONG_REGISTERED_GITHUB_APP");
  permits(app.permissions, "APP");

  const installation = await api(
    "/repos/" + PILOT.repository + "/installation", jwt);
  must(Number.isSafeInteger(installation?.id) && installation.id > 0 &&
    installation.app_id === PILOT.appID &&
    installation.account?.login === TARGET_OWNER &&
    !installation.suspended_at,
    "REGISTERED_APP_NOT_INSTALLED_ON_TARGET");
  permits(installation.permissions, "INSTALLATION");

  const minted = await api("/app/installations/" + installation.id +
    "/access_tokens", jwt, {
      method: "POST",
      body: {
        repositories: ["go-ethereum"],
        permissions: REQUESTED_PERMISSIONS
      }
    });
  must(typeof minted?.token === "string" && minted.token.length >= 10,
    "APP_INSTALLATION_TOKEN_NOT_RETURNED");
  permits(minted.permissions, "TOKEN");

  let published;
  let publicationError;
  let revoked = false;
  try {
    published = await publish({ token: minted.token });
    must(published && published.appID === PILOT.appID &&
      published.repository === PILOT.repository &&
      published.pr === PILOT.pr && published.sha === PILOT.sha &&
      published.conclusion === "neutral" &&
      (published.outcome === "CREATED" || published.outcome === "EXISTING"),
      "PUBLISHED_CHECK_APP_IDENTITY_MISMATCH");
  } catch (error) {
    publicationError = error;
  } finally {
    try {
      const result = await api("/installation/token", minted.token,
        { method: "DELETE" });
      revoked = result.revoked === true;
    } catch {
      revoked = false;
    }
  }
  if (publicationError) throw publicationError;
  must(revoked, "INSTALLATION_TOKEN_REVOCATION_NOT_VERIFIED");
  return {
    outcome: published.outcome,
    appID: PILOT.appID, checkId: published.checkId,
    repository: PILOT.repository, pr: PILOT.pr, sha: PILOT.sha,
    conclusion: "neutral", keyEncoding: material.encoding, tokenRevoked: true
  };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const result = await authenticateAndPublish({
      keyText: process.env.MATHGRAPH_CHECK_APP_PRIVATE_KEY
    });
    console.log("MATHGRAPH_REGISTERED_APP_CHECK_VERIFIED " + JSON.stringify(result));
    if (process.env.GITHUB_STEP_SUMMARY) {
      appendFileSync(process.env.GITHUB_STEP_SUMMARY,
        "### Registered MathGraph Check App — " + result.outcome + "\n" +
        "App ID: " + result.appID + " · Check: " + result.checkId +
        " · Neutral: yes · Installation token revoked: yes\n" +
        "PR SHA: " + result.sha + "\n");
    }
  } catch (error) {
    // Emit stable diagnostics only. Never print PEMs, JWTs or installation tokens.
    console.error("MATHGRAPH_APP_GATE_REJECTED " + String(error.message || "UNKNOWN"));
    process.exitCode = 1;
  }
}
