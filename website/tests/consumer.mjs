import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { stat, readFile, mkdtemp, copyFile, rm } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { tmpdir } from 'node:os';
import { pathToFileURL } from 'node:url';
import { createServer } from 'node:http';
import { resolve, sep } from 'node:path';

const RECORD_ID = 'mg-l4yaml-source-check-20261010';
const RECORD_DIGEST = 'f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb';
const SOURCE_COMMIT = '62bf7077910e888a0bc8adfc8e08a5f500ff3ca3';
const SUITE_COMMIT = 'da267a5c4782e7361e82889e76c0dc7df0e1e870';
const SUPPORTED_GOAL = 'finite_parser_acceptance';
const root = resolve(process.env.MATHGRAPH_CONSUMER_ROOT ?? new URL('../dist', import.meta.url).pathname);
const resolveId = 'mg-living-warrant-openai-jpl-20261010';
const offlinePath = `evidence/${resolveId}/offline`;
const publicPins = {
  'consumer.py': '27a9be606040cc94a47c9b903dfc1cb24a86cbbc4e05ce71040c6c3d6e8d527b',
  'bundle.json': '957080db79555f982fd3a314c263cf5177ef506969229e856897f0b19ccc1d62',
  'trust-policy.json': '09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a',
};
for (const [name, pin] of Object.entries(publicPins)) {
  const bytes = await readFile(resolve(root, offlinePath, name)).catch(() => null);
  assert(bytes, `missing built standalone input: ${name}`);
  assert.equal(sha256(bytes), pin, `wrong standalone input bytes: ${name}`);
}
const clientPath = resolve(root, 'examples/resolve-consumer-v1.ts');
assert(await stat(clientPath).catch(() => false), 'independent Node reference client missing');
const clientDirectory = await mkdtemp(resolve(tmpdir(), 'resolve-node-consumer-'));
await copyFile(clientPath, resolve(clientDirectory, 'consumer.ts'));
const reference = await import(pathToFileURL(resolve(clientDirectory, 'consumer.ts')).href);

function canonicalJson(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  return `{${Object.entries(value)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, child]) => `${JSON.stringify(key)}:${canonicalJson(child)}`)
    .join(',')}}`;
}

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function hasExpectedDigest(record, entry) {
  const unsigned = structuredClone(record);
  const declared = unsigned.content_sha256;
  delete unsigned.content_sha256;
  return declared === entry.record_content_sha256 && sha256(canonicalJson(unsigned)) === declared;
}

function consume(index, entry, record, recordBytes, request, fetchedAt, now = Date.now()) {
  const unknown = (reason) => ({ status: 'UNKNOWN', reason, truth_promotion: false });
  if (now - fetchedAt > index.lifecycle_freshness.max_age_seconds * 1000) return unknown('CATALOGUE_CACHE_EXPIRED');
  if (request.record_id !== entry.id) return unknown('RECORD_ID_MISMATCH');
  if (request.version !== entry.version) return unknown('VERSION_MISMATCH');
  if (request.source_commit !== entry.scope?.source_commit) return unknown('SOURCE_PIN_MISMATCH');
  if (request.external_suite_commit !== entry.scope?.external_suite_commit) return unknown('SUITE_PIN_MISMATCH');
  if (!entry.scope?.supported_goals?.includes(request.goal)) return unknown('UNSUPPORTED_GOAL');
  if (entry.lifecycle !== 'CURRENT') return unknown('LIFECYCLE_NOT_CURRENT');
  if (entry.historic_status !== 'WARRANTED_BOUNDED') return unknown('HISTORIC_STATUS_NOT_WARRANTED');
  if (record.extensions && Object.keys(record.extensions).length > 0) return unknown('UNSUPPORTED_EXTENSION');
  if (sha256(recordBytes) !== entry.record_transport_sha256) return unknown('RECORD_TRANSPORT_MISMATCH');
  if (!hasExpectedDigest(record, entry)) return unknown('RECORD_DIGEST_MISMATCH');
  if (
    record.id !== entry.id ||
    record.content_sha256 !== RECORD_DIGEST ||
    record.source?.commit !== entry.scope.source_commit ||
    record.source?.external_suite_commit !== entry.scope.external_suite_commit ||
    record.axes?.finite_executable?.matched_external_labels !== 48 ||
    record.axes?.finite_executable?.source_cases !== 48 ||
    record.axes?.finite_executable?.extra_controls !== 4 ||
    record.axes?.global_truth_promotion !== false
  ) return unknown('RECORD_BOUNDARY_MISMATCH');

  return {
    status: 'WARRANTED_BOUNDED',
    reason: 'EXACT_SCOPE_MATCH',
    matched: 48,
    total: 48,
    extra_controls: 4,
    whole_language_validity: record.axes.formal_verification.universal_yaml_correctness,
    truth_promotion: false,
  };
}

const overrides = new Map();
const server = createServer(async (request, response) => {
  const pathname = decodeURIComponent(new URL(request.url ?? '/', 'http://consumer.invalid').pathname);
  if (overrides.has(pathname)) {
    const value = overrides.get(pathname);
    response.writeHead(value.status ?? 200, value.headers ?? {}).end(value.bytes ?? '');
    return;
  }
  const target = resolve(root, `.${pathname}`);
  if (!target.startsWith(`${root}${sep}`)) {
    response.writeHead(403).end();
    return;
  }
  try {
    const details = await stat(target);
    if (!details.isFile()) throw new Error('not a file');
    response.writeHead(200, { 'content-type': 'application/json; charset=utf-8' });
    createReadStream(target).pipe(response);
  } catch {
    response.writeHead(404).end();
  }
});

try {
  await new Promise((resolveListening) => server.listen(0, '127.0.0.1', resolveListening));
  const address = server.address();
  assert(address && typeof address === 'object');
  const origin = `http://127.0.0.1:${address.port}`;
  const localUrl = (canonical) => `${origin}${new URL(canonical).pathname}`;
  const discoveryResponse = await fetch(`${origin}/.well-known/mathgraph.json`);
  assert.equal(discoveryResponse.status, 200, `discovery manifest returned ${discoveryResponse.status}`);
  const discovery = await discoveryResponse.json();
  assert.equal(discovery.capabilities.static_records, 'IMPLEMENTED');
  const indexResponse = await fetch(localUrl(discovery.record_index));
  assert.equal(indexResponse.status, 200, `record index returned ${indexResponse.status}`);
  const index = await indexResponse.json();
  const fetchedAt = Date.now();
  assert(Number.isFinite(Date.parse(index.generated_at)), 'catalogue generated_at is invalid');
  assert.equal(index.lifecycle_freshness.basis, 'CLIENT_FETCH_TIME');
  const entry = index.records.find((candidate) => candidate.id === RECORD_ID && candidate.version === 1);
  assert(entry, 'qualified V1 record is absent from catalogue');
  const fetched = await fetch(localUrl(entry.record_json_url));
  assert.equal(fetched.status, 200, `published record returned ${fetched.status}`);
  const recordBytes = Buffer.from(await fetched.arrayBuffer());
  const record = JSON.parse(recordBytes.toString('utf8'));
  const exactRequest = {
    record_id: RECORD_ID,
    version: 1,
    source_commit: SOURCE_COMMIT,
    external_suite_commit: SUITE_COMMIT,
    goal: SUPPORTED_GOAL,
  };

  const exact = consume(index, entry, record, recordBytes, exactRequest, fetchedAt);
  assert.deepEqual(exact, {
    status: 'WARRANTED_BOUNDED',
    reason: 'EXACT_SCOPE_MATCH',
    matched: 48,
    total: 48,
    extra_controls: 4,
    whole_language_validity: 'UNKNOWN',
    truth_promotion: false,
  });
  assert.deepEqual(consume(index, entry, record, recordBytes, { ...exactRequest, source_commit: '0'.repeat(40) }, fetchedAt), {
    status: 'UNKNOWN', reason: 'SOURCE_PIN_MISMATCH', truth_promotion: false,
  });
  assert.deepEqual(consume(index, entry, record, recordBytes, { ...exactRequest, external_suite_commit: '0'.repeat(40) }, fetchedAt), {
    status: 'UNKNOWN', reason: 'SUITE_PIN_MISMATCH', truth_promotion: false,
  });
  assert.deepEqual(consume(index, entry, record, recordBytes, { ...exactRequest, goal: 'whole_language_correctness' }, fetchedAt), {
    status: 'UNKNOWN', reason: 'UNSUPPORTED_GOAL', truth_promotion: false,
  });
  assert.deepEqual(consume(index, entry, record, recordBytes, { ...exactRequest, record_id: 'unknown-record' }, fetchedAt), {
    status: 'UNKNOWN', reason: 'RECORD_ID_MISMATCH', truth_promotion: false,
  });
  assert.deepEqual(consume(index, entry, record, recordBytes, { ...exactRequest, version: 2 }, fetchedAt), {
    status: 'UNKNOWN', reason: 'VERSION_MISMATCH', truth_promotion: false,
  });
  const altered = structuredClone(record);
  altered.axes.finite_executable.expected_accept = 32;
  const alteredBytes = Buffer.from(`${JSON.stringify(altered)}\n`);
  assert.equal(consume(index, entry, altered, alteredBytes, exactRequest, fetchedAt).status, 'UNKNOWN');
  const unknownExtension = structuredClone(record);
  unknownExtension.extensions = { 'future.example': { raw: true } };
  assert.deepEqual(consume(index, entry, unknownExtension, recordBytes, exactRequest, fetchedAt), {
    status: 'UNKNOWN', reason: 'UNSUPPORTED_EXTENSION', truth_promotion: false,
  });
  assert.deepEqual(
    consume(index, entry, record, recordBytes, exactRequest, fetchedAt, fetchedAt + 301_000),
    { status: 'UNKNOWN', reason: 'CATALOGUE_CACHE_EXPIRED', truth_promotion: false },
  );
  console.log('INDEPENDENT_STATIC_CONSUMER_GREEN discovery=catalogue exact=WARRANTED_BOUNDED negatives=8xUNKNOWN digest=recomputed');
  const result = await reference.consumeOrigin(origin);
  assert.equal(result.current_applicability, 'UNKNOWN');
  assert.equal(result.freshness, 'NOT_CHECKED');
  assert.equal(result.revocation_or_supersession, 'NOT_CHECKED');
  assert.equal(result.action_authorization, 'NONE');
  assert.equal(result.original_jpl_lean_rerun, false);
  assert.equal(Object.keys(result.historical_resolution).length, 7);
  for (const i of [1, 2, 3]) {
    assert.deepEqual(result.historical_resolution[`openai.original_support.${i}`], { before: 'SOURCE_DOCUMENTED', after: 'STALE', changed: true });
    assert.deepEqual(result.historical_resolution[`openai.theorem.${i}`], { before: 'UNKNOWN', after: 'UNKNOWN', changed: false });
  }
  assert.deepEqual(result.historical_resolution['jpl.l4yaml.finite_parser_acceptance'], { before: 'WARRANTED_BOUNDED', after: 'WARRANTED_BOUNDED', changed: false });
  const cli = await promisify(execFile)(process.execPath, [resolve(clientDirectory, 'consumer.ts'), origin], { cwd: clientDirectory, env: { PATH: process.env.PATH } });
  assert.deepEqual(JSON.parse(cli.stdout), result, 'standalone CLI differs from HTTP integration');
  const resources = Object.fromEntries(await Promise.all(['record.json', 'scenarios.json', 'offline/bundle.json', 'offline/trust-policy.json'].map(async name => [name, Buffer.from(await (await fetch(`${origin}/evidence/${resolveId}/${name}`)).arrayBuffer())])));
  const record002 = reference.parseStrict(resources['record.json']);
  const policy = reference.parseStrict(resources['offline/trust-policy.json']);
  for (const invalid of ['{"x":1,"x":2}', '{"x":{"a":1,"a":2}}', '{"x":NaN}', '{"x":1e999}']) assert.throws(() => reference.parseStrict(Buffer.from(invalid)));
  for (const mutate of [
    r => { r.schema = 'future'; },
    r => { r.resolutions['openai.theorem.1'].after = 'REFUTED'; },
    r => { r.derivation.claims[0].kind = 'universal'; },
    r => { r.derivation.claims[0].scope = 'all mathematics'; },
    r => { r.sources.openai.commit = '0'.repeat(40); },
    r => { r.derivation.routes[0].relation = 'generalization'; },
  ]) {
    const changed = structuredClone(record002); mutate(changed);
    delete changed.snapshot_sha256;
    changed.snapshot_sha256 = sha256(reference.canonical(changed));
    assert.throws(() => reference.replayGraph(changed, policy));
  }
  for (const [key, value] of [['verifier', 'forged'], ['assumptions', ['unverified']], ['scope', 'generalized']]) {
    const changed = structuredClone(policy);
    changed.admissions['mathgraph.l4yaml.48-case-qualification'][key] = value;
    assert.throws(() => reference.replayGraph(record002, changed));
  }
  const cycle = { claims: [{ id: 'a', kind: 'formal', scope: 'test' }, { id: 'b', kind: 'formal', scope: 'test' }], receipts: [], routes: [{ conclusion: 'a', premises: ['b'], evidence: [] }, { conclusion: 'b', premises: ['a'], evidence: [] }], withdrawn_evidence: [] };
  assert.deepEqual(reference.closeGraph(cycle, {}), { a: 'UNKNOWN', b: 'UNKNOWN' });
  const fakeEntry = structuredClone(index); fakeEntry.records.find(e => e.id === resolveId).record_transport_sha256 = '0'.repeat(64);
  assert.throws(() => reference.validateInputs(fakeEntry, resources));
  for (const name of Object.keys(resources)) {
    assert.throws(() => reference.validateInputs(index, { ...resources, [name]: Buffer.concat([resources[name], Buffer.from(' ')]) }));
    overrides.set(`/evidence/${resolveId}/${name}`, { bytes: Buffer.concat([resources[name], Buffer.from(' ')]) });
    await assert.rejects(reference.consumeOrigin(origin), /external transport pin/);
    overrides.clear();
  }
  overrides.set('/records/index.json', { bytes: JSON.stringify(fakeEntry) });
  await assert.rejects(reference.consumeOrigin(origin), /catalogue cannot redefine authority/);
  overrides.clear();
  overrides.set(`/evidence/${resolveId}/record.json`, { status: 302, headers: { location: 'https://example.invalid/untrusted.json' } });
  await assert.rejects(reference.consumeOrigin(origin));
  overrides.clear();
  for (const invalidOrigin of [`${origin}/arbitrary/path`, 'file:///tmp/record.json', 'https://user:secret@example.invalid/']) await assert.rejects(reference.consumeOrigin(invalidOrigin));
  console.log('INDEPENDENT_RESOLVE_HTTP_CONSUMER_GREEN claims=7 authority=external-pins closure=recomputed current=UNKNOWN');
} finally {
  await new Promise((resolveClosed) => server.close(resolveClosed));
  await rm(clientDirectory, { recursive: true, force: true });
}
