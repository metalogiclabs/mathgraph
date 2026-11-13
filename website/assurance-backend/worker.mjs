/**
 * MathGraph Open Challenge intake — independently deployed Cloudflare Worker.
 * Sensitive input must never be logged or reflected into responses.
 * D1 data is owner-readable only through the authenticated Cloudflare account.
 * Production TURNSTILE_SECRET is configured as a Worker secret, never committed.
 */
const ALLOWED_ORIGINS = new Set(["https://mathgraph.org", "https://www.mathgraph.org"]);
const ALLOWED_HOSTNAMES = new Set(["mathgraph.org", "www.mathgraph.org"]);
const RECEIVED_URL = "https://mathgraph.org/assurance/received/";
const MAX_BYTES = 12_000;
const ACTION = "mathgraph_assurance";
const RETENTION_DAYS = 180;

function page(status, title, detail) {
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta name="robots" content="noindex"><title>${title} — MathGraph</title></head><body><main style="font:1rem/1.6 system-ui;margin:6vh auto;max-width:37rem;padding:1.5rem"><h1>${title}</h1><p>${detail}</p><p><a href="https://mathgraph.org/assurance/#challenge">Return to the Open Challenge</a></p></main></body></html>`;
  return new Response(html, { status, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer" } });
}
function field(form, name, min, max) {
  const value = form.get(name);
  if (typeof value !== "string") throw new Error("INVALID_INPUT");
  const text = value.trim();
  if (text.length < min || text.length > max || /[\u0000-\u0008\u000B\u000C\u000E-\u001F]/u.test(text)) throw new Error("INVALID_INPUT");
  return text;
}
function campaign(form, key) {
  const value = form.get(key);
  return typeof value === "string" && /^[a-z0-9_. -]{0,80}$/i.test(value) ? value : "";
}
export async function handleRequest(request, env, fetchImpl = fetch) {
  const url = new URL(request.url);
  if (request.method === "GET" && url.pathname === "/health") {
    try {
      if (!env.LEADS || !env.TURNSTILE_SECRET) throw new Error("UNCONFIGURED");
      await env.LEADS.prepare("SELECT 1 AS ok").first();
      return new Response(JSON.stringify({ status: "ready", service: "mathgraph-assurance-intake" }), { status: 200, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" } });
    } catch {
      return new Response(JSON.stringify({ status: "unavailable" }), { status: 503, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" } });
    }
  }
  if (request.method !== "POST" || url.pathname !== "/submit") return page(404, "Not found", "This endpoint only receives Open Challenge submissions.");
  if (!ALLOWED_ORIGINS.has(request.headers.get("Origin"))) return page(403, "Submission not accepted", "Please submit through the official MathGraph website.");
  if (!(request.headers.get("Content-Type") || "").toLowerCase().startsWith("application/x-www-form-urlencoded")) return page(415, "Unsupported submission", "Please use the Open Challenge form.");
  const length = Number(request.headers.get("Content-Length") || "0");
  if (!Number.isFinite(length) || length > MAX_BYTES) return page(413, "Submission too long", "Please shorten the answers and try again.");
  if (!env.LEADS || !env.TURNSTILE_SECRET) return page(503, "Submission unavailable", "Nothing was saved. Please try again later or contact us through the alternative channel.");
  let form;
  try {
    const raw = await request.text();
    if (new TextEncoder().encode(raw).length > MAX_BYTES) return page(413, "Submission too long", "Please shorten the answers and try again.");
    form = new URLSearchParams(raw);
  } catch {
    return page(400, "Invalid submission", "Please review the form and try again.");
  }
  if (form.get("website")) return page(400, "Invalid submission", "Please review the form and try again.");

  let repository, claim, decision, consequence, evidence, relationship, email, token;
  try {
    repository = field(form, "repository", 12, 360);
    const parsed = new URL(repository);
    if (parsed.protocol !== "https:" || !parsed.hostname.includes(".") || parsed.username || parsed.password || parsed.hash || ["localhost", "127.0.0.1"].includes(parsed.hostname)) throw new Error("INVALID_REPO");
    claim = field(form, "claim", 20, 1500);
    decision = field(form, "decision", 20, 1400);
    consequence = field(form, "consequence", 10, 1000);
    evidence = field(form, "evidence", 0, 900);
    relationship = field(form, "relationship", 3, 50);
    if (!["owner", "maintainer", "authorized_engineer", "contributor", "other"].includes(relationship)) throw new Error("INVALID_ROLE");
    email = field(form, "email", 5, 254);
    if (!/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/u.test(email)) throw new Error("INVALID_EMAIL");
    if (form.get("consent") !== "yes") throw new Error("NO_CONSENT");
    token = field(form, "cf-turnstile-response", 20, 2048);
  } catch {
    return page(422, "Check your answers", "A required answer or the human-verification token is missing or invalid. Please review the form.");
  }

  try {
    const verify = await fetchImpl("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ secret: env.TURNSTILE_SECRET, response: token }),
      signal: AbortSignal.timeout(8000),
    });
    if (!verify.ok) return page(503, "Verification unavailable", "Nothing was saved. Please try again later.");
    const result = await verify.json();
    if (result.success !== true || !ALLOWED_HOSTNAMES.has(result.hostname) || result.action !== ACTION) {
      return page(403, "Human verification failed", "Nothing was saved. Please refresh the form and complete human verification again.");
    }
  } catch {
    return page(503, "Verification unavailable", "Nothing was saved. Please try again later.");
  }

  try {
    const id = crypto.randomUUID();
    const result = await env.LEADS.prepare(`INSERT INTO submissions (id, repository_url, claim, decision, consequence, evidence, relationship, email, campaign_source, campaign_medium, campaign_name, status, consent_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'NEW', 'mathgraph-assurance-v1')`).bind(
      id, repository, claim, decision, consequence, evidence, relationship, email,
      campaign(form, "utm_source"), campaign(form, "utm_medium"), campaign(form, "utm_campaign"),
    ).run();
    if (result?.success !== true) throw new Error("NOT_STORED");
  } catch {
    return page(503, "Submission unavailable", "Nothing was confirmed as saved. Please try again or contact us through the alternative channel.");
  }
  return new Response(null, { status: 303, headers: { Location: RECEIVED_URL, "Cache-Control": "no-store", "Referrer-Policy": "no-referrer" } });
}

export default {
  fetch: handleRequest,
  scheduled(_event, env, ctx) {
    ctx.waitUntil(env.LEADS.prepare(`DELETE FROM submissions WHERE created_at < datetime('now', '-${RETENTION_DAYS} days')`).run());
  },
};
