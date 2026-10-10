import assert from 'node:assert/strict';
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { createServer } from 'node:http';
import { resolve, sep } from 'node:path';

const RECORD_ID = 'mg-l4yaml-source-check-20261010';
const RECORD_DIGEST = 'f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb';
const SOURCE_COMMIT = '62bf7077910e888a0bc8adfc8e08a5f500ff3ca3';
const SUITE_COMMIT = 'da267a5c4782e7361e82889e76c0dc7df0e1e870';
const SUPPORTED_GOAL = 'pinned_external_case_agreement';
const root = resolve(process.env.MATHGRAPH_CONSUMER_ROOT ?? new URL('../dist', import.meta.url).pathname);

function consume(record, request) {
  const exact =
    record.id === RECORD_ID &&
    record.content_sha256 === RECORD_DIGEST &&
    record.source?.commit === SOURCE_COMMIT &&
    record.source?.external_suite_commit === SUITE_COMMIT &&
    request.record_id === RECORD_ID &&
    request.source_commit === SOURCE_COMMIT &&
    request.external_suite_commit === SUITE_COMMIT &&
    request.goal === SUPPORTED_GOAL &&
    record.axes?.finite_executable?.matched_external_labels === 48 &&
    record.axes?.finite_executable?.extra_controls === 4 &&
    record.axes?.global_truth_promotion === false;

  return exact
    ? {
        status: 'WARRANTED_BOUNDED',
        matched: 48,
        total: 48,
        extra_controls: 4,
        whole_language_validity: record.axes.formal_verification.universal_yaml_correctness,
        truth_promotion: false,
      }
    : { status: 'UNKNOWN', truth_promotion: false };
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
  const url = `http://127.0.0.1:${address.port}/evidence/${RECORD_ID}/record.json`;
  const fetched = await fetch(url);
  assert.equal(fetched.status, 200, `published record returned ${fetched.status}`);
  const record = await fetched.json();
  const exactRequest = {
    record_id: RECORD_ID,
    source_commit: SOURCE_COMMIT,
    external_suite_commit: SUITE_COMMIT,
    goal: SUPPORTED_GOAL,
  };

  const exact = consume(record, exactRequest);
  assert.deepEqual(exact, {
    status: 'WARRANTED_BOUNDED',
    matched: 48,
    total: 48,
    extra_controls: 4,
    whole_language_validity: 'UNKNOWN',
    truth_promotion: false,
  });
  assert.equal(consume(record, { ...exactRequest, source_commit: '0'.repeat(40) }).status, 'UNKNOWN');
  assert.equal(consume(record, { ...exactRequest, goal: 'whole_language_correctness' }).status, 'UNKNOWN');
  assert.equal(consume(record, { ...exactRequest, record_id: 'unknown-record' }).status, 'UNKNOWN');
  console.log('INDEPENDENT_STATIC_CONSUMER_GREEN exact=WARRANTED_BOUNDED negatives=3xUNKNOWN');
} finally {
  await new Promise((resolveClosed) => server.close(resolveClosed));
}
