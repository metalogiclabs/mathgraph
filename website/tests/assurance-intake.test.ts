import { describe, expect, it, vi } from 'vitest';
import { handleRequest } from '../assurance-backend/worker.mjs';

const endpoint = 'https://mathgraph-assurance-intake.metalogiclabs-check.workers.dev/submit';
function fixture(overrides: Record<string,string> = {}, origin = 'https://mathgraph.org') {
  const fields = {
    repository: 'https://github.com/example/aerospace-library',
    claim: 'Every exported trajectory row has the original physical reference frame.',
    decision: 'We would ship the updated trajectory exporter to our customers.',
    consequence: 'Incorrect frame metadata could cause a downstream orbit interpretation error.',
    evidence: 'Our current unit tests cover serialization.',
    relationship: 'maintainer',
    email: 'maintainer@example.org',
    consent: 'yes',
    'cf-turnstile-response': 'test-client-token-not-a-secret',
    website: '',
    utm_source: 'linkedin',
    utm_medium: 'paid',
    utm_campaign: 'open_challenge',
    ...overrides,
  };
  return new Request(endpoint, {
    method: 'POST',
    headers: { Origin: origin, 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(fields),
  });
}
function harness({ verified = true, saved = true, hostname = 'mathgraph.org', action = 'mathgraph_assurance', secret = 'test-secret' } = {}) {
  const bind = vi.fn().mockReturnValue({run: vi.fn().mockResolvedValue({success: saved})});
  const prepare = vi.fn().mockReturnValue({bind, first: vi.fn().mockResolvedValue({ok:1})});
  const verify = vi.fn().mockResolvedValue({ok: true, json: async () => ({success: verified,hostname,action})});
  const env = { LEADS: {prepare}, TURNSTILE_SECRET: secret };
  return {env, verify, prepare, bind};
}

describe('MathGraph private assurance intake', () => {
  it('persists a validated consequential claim and redirects only after D1 success', async () => {
    const h = harness();
    const r = await handleRequest(fixture(), h.env, h.verify);
    expect(r.status).toBe(303);
    expect(r.headers.get('Location')).toBe('https://mathgraph.org/assurance/received/');
    expect(h.verify).toHaveBeenCalledTimes(1);
    expect(h.prepare).toHaveBeenCalledTimes(1);
    expect(h.bind).toHaveBeenCalledTimes(1);
    const args = h.bind.mock.calls[0];
    expect(args).toContain('maintainer@example.org');
    expect(args).toContain('linkedin');
    expect(args).toContain('We would ship the updated trajectory exporter to our customers.');
  });
  it('rejects cross-origin posts before verification and database access', async () => {
    const h = harness();
    const r = await handleRequest(fixture({}, 'https://attacker.invalid'), h.env, h.verify);
    expect(r.status).toBe(403);
    expect(h.verify).not.toHaveBeenCalled();
    expect(h.prepare).not.toHaveBeenCalled();
  });
  it('fails closed on Turnstile failure, wrong origin hostname or wrong action', async () => {
    for (const options of [{verified:false},{hostname:'attacker.invalid'},{action:'other_action'}]) {
      const h=harness(options);
      const r=await handleRequest(fixture(),h.env,h.verify);
      expect(r.status).toBe(403);
      expect(h.prepare).not.toHaveBeenCalled();
    }
  });
  it('rejects fabricated inputs, private-key-like URLs, missing consent and honeypots', async () => {
    for (const input of [{consent:'no'},{repository:'https://username:pass@github.com/repo'},{claim:'too short'},{website:'spam'}]) {
      const h=harness();
      const r=await handleRequest(fixture(input),h.env,h.verify);
      expect(r.status).toBeGreaterThanOrEqual(400);
      expect(h.prepare).not.toHaveBeenCalled();
    }
  });
  it('never confirms success if D1 fails', async () => {
    const h=harness({saved:false});
    const r=await handleRequest(fixture(),h.env,h.verify);
    expect(r.status).toBe(503);
    expect(r.headers.get('Location')).toBeNull();
    expect(await r.text()).not.toContain('maintainer@example.org');
  });
  it('fails closed if verification secret is unavailable', async () => {
    const h=harness({secret:''});
    const r=await handleRequest(fixture(),h.env,h.verify);
    expect(r.status).toBe(503);
    expect(h.verify).not.toHaveBeenCalled();
  });
  it('only exposes a healthy status when both configuration and D1 are ready', async () => {
    const h=harness();
    const r=await handleRequest(new Request(endpoint.replace('/submit','/health')),h.env,h.verify);
    expect(r.status).toBe(200);
    expect(await r.json()).toEqual({status:'ready',service:'mathgraph-assurance-intake'});
    const fail=await handleRequest(new Request(endpoint.replace('/submit','/health')),{LEADS:h.env.LEADS,TURNSTILE_SECRET:''},h.verify);
    expect(fail.status).toBe(503);
  });
});
