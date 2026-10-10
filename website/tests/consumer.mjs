import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { createServer } from 'node:http';
import { resolve, sep } from 'node:path';

const RECORD_ID = 'mg-l4yaml-source-check-20261010';
const RECORD_DIGEST = 'f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb';
const SOURCE_COMMIT = '62bf7077910e888a0bc8adfc8e08a5f500ff3ca3';
const SUITE_COMMIT = 'da267a5c4782e7361e82889e76c0dc7df0e1e870';
const SUPPORTED_GOAL = 'finite_parser_acceptance';
const root = resolve(process.env.MATHGRAPH_CONSUMER_ROOT ?? new URL('../dist', import.meta.url).pathname);

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

function consume(entry, record, recordBytes, request) {
  const unknown = (reason) => ({ status: 'UNKNOWN', reason, truth_promotion: false });
  if (request.record_id !== entry.id) return unknown('RECORD_ID_MISMATCH');
  if (request.version !== entry.version) return unknown('VERSION_MISMATCH');
  if (request.source_commit !== entry.scope?.source_commit) return unknown('SOURCE_PIN_MISMATCH');
  if (request.external_suite_commit !== entry.scope?.external_suite_commit) return unknown('SUITE_PIN_MISMATCH');
  if (!entry.scope?.supported_goals?.includes(request.goal)) return unknown('UNSUPPORTED_GOAL');
  if (entry.historic_status !== 'WARRANTED_BOUNDED' || entry.lifecycle !== 'CURRENT') return unknown('LIFECYCLE_NOT_CURRENT');
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

const server = createServer(async (request, response) => {
  const pathname = decodeURIComponent(new URL(request.url ?? '/', 'http://consumer.invalid').pathname);
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
  const generatedAt = Date.parse(index.generated_at);
  assert(Number.isFinite(generatedAt), 'catalogue generated_at is invalid');
  assert(Date.now() - generatedAt <= index.lifecycle_freshness.max_age_seconds * 1000, 'catalogue lifecycle state is stale');
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

  const exact = consume(entry, record, recordBytes, exactRequest);
  assert.deepEqual(exact, {
    status: 'WARRANTED_BOUNDED',
    reason: 'EXACT_SCOPE_MATCH',
    matched: 48,
    total: 48,
    extra_controls: 4,
    whole_language_validity: 'UNKNOWN',
    truth_promotion: false,
  });
  assert.deepEqual(consume(entry, record, recordBytes, { ...exactRequest, source_commit: '0'.repeat(40) }), {
    status: 'UNKNOWN', reason: 'SOURCE_PIN_MISMATCH', truth_promotion: false,
  });
  assert.deepEqual(consume(entry, record, recordBytes, { ...exactRequest, external_suite_commit: '0'.repeat(40) }), {
    status: 'UNKNOWN', reason: 'SUITE_PIN_MISMATCH', truth_promotion: false,
  });
  assert.deepEqual(consume(entry, record, recordBytes, { ...exactRequest, goal: 'whole_language_correctness' }), {
    status: 'UNKNOWN', reason: 'UNSUPPORTED_GOAL', truth_promotion: false,
  });
  assert.deepEqual(consume(entry, record, recordBytes, { ...exactRequest, record_id: 'unknown-record' }), {
    status: 'UNKNOWN', reason: 'RECORD_ID_MISMATCH', truth_promotion: false,
  });
  assert.deepEqual(consume(entry, record, recordBytes, { ...exactRequest, version: 2 }), {
    status: 'UNKNOWN', reason: 'VERSION_MISMATCH', truth_promotion: false,
  });
  const altered = structuredClone(record);
  altered.axes.finite_executable.expected_accept = 32;
  const alteredBytes = Buffer.from(`${JSON.stringify(altered)}\n`);
  assert.equal(consume(entry, altered, alteredBytes, exactRequest).status, 'UNKNOWN');
  const unknownExtension = structuredClone(record);
  unknownExtension.extensions = { 'future.example': { raw: true } };
  assert.deepEqual(consume(entry, unknownExtension, recordBytes, exactRequest), {
    status: 'UNKNOWN', reason: 'UNSUPPORTED_EXTENSION', truth_promotion: false,
  });
  console.log('INDEPENDENT_STATIC_CONSUMER_GREEN discovery=catalogue exact=WARRANTED_BOUNDED negatives=7xUNKNOWN digest=recomputed');
} finally {
  await new Promise((resolveClosed) => server.close(resolveClosed));
}
