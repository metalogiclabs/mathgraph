/** Node 24 local HTTP client. No packages, producer imports, services, or writes.
 * Usage: node resolve-consumer-v1.ts https://mathgraph.org
 * Authority constants must be obtained/reviewed separately from the queried host.
 * This online client is not an OS-isolated offline replay or a current warrant.
 */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';

type ObjectValue = Record<string, any>; // Untrusted JSON is runtime-validated below.
const ID = 'mg-living-warrant-openai-jpl-20261010';
const PREFIX = `/evidence/${ID}/`;
const HASHES: Record<string, string> = {
  'record.json': '0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87',
  'scenarios.json': 'ed458ccbee85e3aa3f49d9d38e7ad5380515d00d707bac09c584cc4955b88181',
  'offline/bundle.json': '957080db79555f982fd3a314c263cf5177ef506969229e856897f0b19ccc1d62',
  'offline/trust-policy.json': '09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a',
};
const MEMBER_PINS: Record<string, [number, string]> = {
  'record.json': [5290, HASHES['record.json']],
  'history.md': [2281, '41c2a2d470014b3628695c7aabf5fd0c93f6f687621fca172062f22b59ed6a1e'],
  'jpl-record.json': [4321, '7b59ee76a39995f35a0feb0f4d91a3c6ab1234393143480c4f3e361a79fee703'],
};
const SNAPSHOT = 'b95297a081d513fb0ec145a776cc997eaed18109d6b2af39fa8e61f6d637af41';
const JPL_CONTENT = 'f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb';
const JPL_SCOPE = 'nasa-jpl/L4YAML@62bf7077910e888a0bc8adfc8e08a5f500ff3ca3:yaml/yaml-test-suite@da267a5c4782e7361e82889e76c0dc7df0e1e870:48-cases';
const TITLES = ['Algebraicity of Weil classes on split abelian eightfolds', 'Algebraicity of Kuga–Satake Correspondences for K3 Surfaces', 'The rational Hodge conjecture for products of K3 surfaces'];
const PROVENANCE = {
  producer: { repository: 'metalogiclabs/mathgraph', commit: '040456fc8862c79c8b384ce63846628274b678be', actions_run: '38025044631' },
  prior_independent_replay: { repository: 'heathsanchez/realitygraph', commit: '9b3189a64825e2cb6ebc7b5c17f5f193bdf5cfe3', actions_run: '38025236380', independently_owned: false },
};
const hash = (bytes: string | Uint8Array) => createHash('sha256').update(bytes).digest('hex');
export function canonical(value: any): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  return Array.isArray(value) ? `[${value.map(canonical).join(',')}]` : `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
}
function same(actual: any, expected: any, reason: string) { assert.equal(canonical(actual), canonical(expected), reason); }
function fields(value: ObjectValue, keys: string[]) { assert(value && !Array.isArray(value) && typeof value === 'object'); same(Object.keys(value).sort(), [...keys].sort(), 'unsupported fields'); }

/** Recursive JSON grammar, including decoded-key uniqueness at every depth. */
export function parseStrict(bytes: Uint8Array): ObjectValue {
  const text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  let offset = 0;
  const space = () => { while (/[\x20\t\r\n]/.test(text[offset] ?? '\0')) offset++; };
  function value(): any {
    space(); const first = text[offset];
    if (first === '{' || first === '[') {
      const object = first === '{'; const result: any = object ? Object.create(null) : [];
      const end = object ? '}' : ']'; offset++; space();
      if (text[offset] === end) { offset++; return result; }
      while (true) {
        if (object) {
          space(); assert.equal(text[offset], '"', 'object key must be string'); const key = value();
          assert(!Object.hasOwn(result, key), 'duplicate JSON key'); space(); assert.equal(text[offset++], ':'); result[key] = value();
        } else result.push(value());
        space(); if (text[offset] === end) { offset++; return result; }
        assert.equal(text[offset++], ',', 'invalid JSON delimiter');
      }
    }
    const match = text.slice(offset).match(/^(?:"(?:[^"\\\u0000-\u001f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"|true|false|null|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)/u);
    assert(match, 'invalid JSON token'); offset += match[0].length;
    const parsed = JSON.parse(match[0]); assert(typeof parsed !== 'number' || Number.isFinite(parsed), 'non-finite number'); return parsed;
  }
  const result = value(); space(); assert.equal(offset, text.length, 'trailing JSON');
  assert(result && typeof result === 'object' && !Array.isArray(result), 'object root required'); return result;
}

/** Independent work-queue closure. No published status is an input. */
export function closeGraph(graph: ObjectValue, admissions: ObjectValue): Record<string, string> {
  fields(graph, ['claims', 'receipts', 'routes', 'withdrawn_evidence']);
  const index = (nodes: any[]) => {
    assert(Array.isArray(nodes)); const map = new Map<string, ObjectValue>();
    for (const n of nodes) {
      fields(n, ['id', 'kind', 'scope']); assert(Object.values(n).every(v => typeof v === 'string' && v));
      assert(['formal', 'documentary'].includes(n.kind), 'unsupported semantic kind'); assert(!map.has(n.id), 'duplicate identity'); map.set(n.id, n);
    } return map;
  };
  const claims = index(graph.claims), receipts = index(graph.receipts);
  same(Object.keys(admissions).sort(), [...receipts.keys()].sort(), 'admission identities');
  const refs = (list: any, available: Map<string, ObjectValue>) => {
    assert(Array.isArray(list) && list.every(x => typeof x === 'string' && available.has(x)), 'unresolved reference');
    assert.equal(new Set(list).size, list.length, 'duplicate reference'); return list as string[];
  };
  const withdrawn = new Set(refs(graph.withdrawn_evidence, receipts));
  for (const [id, node] of receipts) {
    const a = admissions[id]; fields(a, ['kind', 'scope', 'verifier', 'source', 'assumptions', 'outcome']);
    same([a.kind, a.scope, a.assumptions, a.outcome], [node.kind, node.scope, [], 'SUPPORT'], 'receipt context');
    same([a.verifier, a.source], node.kind === 'documentary' ? ['pinned-publisher-notice-v1', 'history.md'] : ['pinned-jpl-qualified-receipt-v1', 'jpl-record.json'], 'verifier/source identity');
  }
  assert(Array.isArray(graph.routes));
  const states = Object.fromEntries([...claims.keys()].map(id => [id, 'UNKNOWN']));
  const waiting = new Map<string, number[]>();
  const ready: number[] = [];
  const routes = graph.routes.map((r: ObjectValue, i: number) => {
    fields(r, ['conclusion', 'premises', 'evidence']); assert(claims.has(r.conclusion), 'unknown conclusion');
    const premises = refs(r.premises, claims), evidence = refs(r.evidence, receipts);
    assert(premises.length + evidence.length, 'empty root route'); const target = claims.get(r.conclusion)!;
    for (const n of [...premises.map(x => claims.get(x)!), ...evidence.map(x => receipts.get(x)!)]) same([n.kind, n.scope], [target.kind, target.scope], 'unsupported semantic transport');
    const enabled = !evidence.some(x => withdrawn.has(x));
    for (const p of premises) waiting.set(p, [...(waiting.get(p) ?? []), i]);
    if (enabled && !premises.length) ready.push(i);
    return { target, enabled, remaining: new Set(premises) };
  });
  for (let cursor = 0; cursor < ready.length; cursor++) {
    const route = routes[ready[cursor]];
    if (!route.enabled || route.remaining.size || states[route.target.id] !== 'UNKNOWN') continue;
    states[route.target.id] = route.target.kind === 'formal' ? 'WARRANTED_BOUNDED' : 'SOURCE_DOCUMENTED';
    for (const dependent of waiting.get(route.target.id) ?? []) {
      routes[dependent].remaining.delete(route.target.id);
      if (!routes[dependent].remaining.size) ready.push(dependent);
    }
  }
  return states;
}

/** Semantic boundary separately exposed for adversarial tests after byte admission. */
export function replayGraph(record: ObjectValue, policy: ObjectValue) {
  fields(record, ['schema', 'id', 'derivation', 'interpretation', 'publisher_notice', 'resolutions', 'snapshot_sha256', 'sources']);
  assert.equal(record.schema, 'mathgraph.living-warrant-snapshot.v1'); assert.equal(record.id, ID);
  same(record.sources, { jpl_record_id: 'mg-l4yaml-source-check-20261010', jpl_record_sha256: JPL_CONTENT, openai: {
    byte_sha256: MEMBER_PINS['history.md'][1], commit: 'fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb', git_blob_sha1: '693874f398905b1bc59e01b898b223ae9956bfc2', notice_date: '2026-10-07', path: 'history.md', url: 'https://github.com/openai/math/blob/fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb/history.md',
  } }, 'source authority');
  const expectedClaims: ObjectValue[] = [], expectedReceipts: ObjectValue[] = [];
  TITLES.forEach((title, i) => {
    const scope = `openai/math:${title}:original-withdrawn-edition`;
    expectedClaims.push({ id: `openai.original_support.${i + 1}`, kind: 'documentary', scope }, { id: `openai.theorem.${i + 1}`, kind: 'formal', scope });
    expectedReceipts.push({ id: `openai.original_publication_receipt.${i + 1}`, kind: 'documentary', scope });
  });
  expectedClaims.push({ id: 'jpl.l4yaml.finite_parser_acceptance', kind: 'formal', scope: JPL_SCOPE });
  expectedReceipts.push({ id: 'mathgraph.l4yaml.48-case-qualification', kind: 'formal', scope: JPL_SCOPE });
  fields(record.derivation, ['claims', 'receipts', 'routes', 'receipt_admission', 'withdrawn_evidence']);
  same(record.derivation.claims, expectedClaims, 'historical claim identities/scopes');
  same(record.derivation.receipts, expectedReceipts, 'historical receipt identities/scopes');
  same(record.derivation.receipt_admission, { documentary: 'exact pinned OpenAI history notice', formal: 'exact pinned JPL finite parser receipt' }, 'admission contract');
  same(record.derivation.withdrawn_evidence, expectedReceipts.slice(0, 3).map(r => r.id), 'withdrawals');
  const { receipt_admission: _unused, ...graph } = record.derivation;
  const before = closeGraph({ ...graph, withdrawn_evidence: [] }, policy.admissions);
  const after = closeGraph(graph, policy.admissions);
  const results = Object.fromEntries(Object.keys(before).sort().map(id => {
    const final = before[id] !== 'UNKNOWN' && after[id] === 'UNKNOWN' ? 'STALE' : after[id];
    return [id, { before: before[id], after: final, changed: before[id] !== final }];
  }));
  same(record.resolutions, results, 'producer assertion differs from independent closure'); return results;
}

export function validateInputs(index: ObjectValue, resources: Record<string, Uint8Array>) {
  assert.equal(index.schema, 'mathgraph.record-index.v2'); assert(Array.isArray(index.records));
  const entries = index.records.filter((e: ObjectValue) => e.id === ID && e.version === 1); assert.equal(entries.length, 1);
  const entry = entries[0];
  same([entry.record_kind, entry.record_schema, entry.record_content_sha256, entry.record_transport_sha256, entry.scenarios_schema, entry.scenarios_transport_sha256], ['RESOLUTION_SNAPSHOT', 'mathgraph.living-warrant-snapshot.v1', SNAPSHOT, HASHES['record.json'], 'mathgraph.resolve-scenarios.v1', HASHES['scenarios.json']], 'catalogue cannot redefine authority');
  for (const name of ['record.json', 'scenarios.json']) assert.equal(entry[name === 'record.json' ? 'record_json_url' : 'scenarios_json_url'], `https://mathgraph.org${PREFIX}${name}`, 'unsupported resource location');
  for (const [name, expected] of Object.entries(HASHES)) assert.equal(hash(resources[name]), expected, `external transport pin: ${name}`);
  const policy = parseStrict(resources['offline/trust-policy.json']), bundle = parseStrict(resources['offline/bundle.json']);
  fields(policy, ['schema', 'members', 'provenance', 'admissions']); fields(bundle, ['schema', 'members', 'provenance']);
  assert.equal(policy.schema, 'mathgraph.resolve-trust-policy.v1'); assert.equal(bundle.schema, 'mathgraph.resolve-bundle.v1');
  same(policy.provenance, PROVENANCE, 'policy provenance'); same(bundle.provenance, PROVENANCE, 'bundle provenance');
  fields(bundle.members, Object.keys(MEMBER_PINS)); fields(policy.members, Object.keys(MEMBER_PINS));
  const decoded: Record<string, Buffer> = {};
  for (const [name, [size, expected]] of Object.entries(MEMBER_PINS)) {
    const member = bundle.members[name]; fields(member, ['encoding', 'data', 'size', 'sha256']);
    same(policy.members[name], { size, sha256: expected }, 'external member authority');
    same([member.encoding, member.size, member.sha256], ['base64', size, expected], 'member declaration');
    assert.equal(typeof member.data, 'string'); const raw = Buffer.from(member.data, 'base64');
    assert.equal(raw.toString('base64'), member.data, 'noncanonical base64'); assert.equal(raw.length, size); assert.equal(hash(raw), expected); decoded[name] = raw;
  }
  assert(Buffer.from(resources['record.json']).equals(decoded['record.json']));
  const record = parseStrict(decoded['record.json']), jpl = parseStrict(decoded['jpl-record.json']);
  for (const [document, field, expected] of [[record, 'snapshot_sha256', SNAPSHOT], [jpl, 'content_sha256', JPL_CONTENT]] as const) {
    assert.equal(document[field], expected); const unsigned = { ...document }; delete unsigned[field]; assert.equal(hash(canonical(unsigned)), expected, 'content integrity');
  }
  const historical = replayGraph(record, policy); const scenarios = parseStrict(resources['scenarios.json']);
  assert.equal(scenarios.schema, 'mathgraph.resolve-scenarios.v1'); assert.equal(scenarios.record_id, ID);
  const publishedAfter = scenarios.PUBLISHED_RECORD.scenarios.find((s: ObjectValue) => s.id === 'published-after');
  same(publishedAfter.resolutions, historical, 'scenario assertion differs from replay');
  return { schema: 'mathgraph.resolve-http-report.v1', record_id: ID, historical_evidence_qualification: 'PINNED_INPUTS_QUALIFIED_UNDER_POLICY', historical_resolution: historical, current_applicability: 'UNKNOWN', freshness: 'NOT_CHECKED', revocation_or_supersession: 'NOT_CHECKED', lifecycle: 'IMMUTABLE_HISTORICAL_SNAPSHOT', action_authorization: 'NONE', original_jpl_lean_rerun: false, independent_ownership: false };
}

export async function consumeOrigin(origin: string) {
  const base = new URL(origin);
  assert(['https:', 'http:'].includes(base.protocol) && !base.username && !base.password && base.pathname === '/' && !base.search && !base.hash, 'an HTTP(S) origin without credentials or path is required');
  async function get(path: string) {
    const response = await fetch(new URL(path, base), { redirect: 'error', signal: AbortSignal.timeout(15000) });
    assert.equal(response.status, 200, `HTTP input unavailable: ${path}`);
    const bytes = new Uint8Array(await response.arrayBuffer()); assert(bytes.length <= 256000, 'input too large'); return bytes;
  }
  const index = parseStrict(await get('/records/index.json'));
  const resources = Object.fromEntries(await Promise.all(Object.keys(HASHES).map(async name => [name, await get(PREFIX + name)])));
  return validateInputs(index, resources);
}

if (import.meta.main) {
  try { assert.equal(process.argv.length, 3, 'usage: node resolve-consumer-v1.ts https://mathgraph.org'); console.log(canonical(await consumeOrigin(process.argv[2]))); }
  catch (error) { console.error(`RESOLVE_REJECTED: ${(error as Error).message}`); process.exitCode = 1; }
}
