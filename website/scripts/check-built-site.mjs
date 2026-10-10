import assert from 'node:assert/strict';
import { readdir, readFile, stat } from 'node:fs/promises';
import { extname, join } from 'node:path';

const root = new URL('..', import.meta.url).pathname;
const dist = join(root, 'dist');
const recordId = 'mg-l4yaml-source-check-20261010';
const sourceRecordPath = join(root, 'src/data/l4yaml-record.json');
const publicRecordPath = join(root, `public/evidence/${recordId}/record.json`);
const builtRecordPath = join(dist, `evidence/${recordId}/record.json`);
const [sourceBytes, publicBytes, builtBytes] = await Promise.all([
  readFile(sourceRecordPath),
  readFile(publicRecordPath),
  readFile(builtRecordPath),
]);
const deployment = JSON.parse(await readFile(join(root, 'vercel.json'), 'utf8'));

assert.deepEqual(publicBytes, sourceBytes, 'public record must be the exact frozen record');
assert.deepEqual(builtBytes, sourceBytes, 'built record must be the exact frozen record');
const record = JSON.parse(sourceBytes);
const recordHtml = await readFile(join(dist, `records/${recordId}/index.html`), 'utf8');
const homeHtml = await readFile(join(dist, 'index.html'), 'utf8');
const allHtml = [];
let clientBytes = 0;

async function collect(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) await collect(path);
    else if (extname(entry.name) === '.html') allHtml.push(await readFile(path, 'utf8'));
    else if (['.js', '.css'].includes(extname(entry.name))) clientBytes += (await stat(path)).size;
  }
}

await collect(dist);
for (const value of [
  record.id,
  record.content_sha256,
  record.source.commit,
  record.source.external_suite_commit,
  record.evidence.v1_compiled_parser.archive_sha256,
  record.evidence.v2_normalized_native_parser.archive_sha256,
]) {
  assert(recordHtml.includes(value), `record page missing machine-readable value ${value}`);
}
for (const value of ['48/48', '31', '17', '52/52', 'UNKNOWN', 'NOT_CHECKED_AFTER_SNAPSHOT']) {
  assert(recordHtml.includes(value), `record page missing qualified observation ${value}`);
}
assert(homeHtml.includes(record.id), 'homepage must identify the featured record');
assert.equal(record.axes.global_truth_promotion, false);
assert.equal(record.admission.mathematical_theorem_badge_issued, false);
assert.equal(record.admission.source_fidelity_certified, false);

const rendered = allHtml.join('\n');
for (const prohibited of [
  /verified by (?:NASA|JPL)/i,
  /NASA[- ]verified/i,
  /universally verified/i,
  /quantum[- ]proof/i,
  />\s*VERIFIED\s*</i,
]) {
  assert(!prohibited.test(rendered), `prohibited authority claim matched ${prohibited}`);
}
assert(rendered.includes('No affiliation or endorsement implied'));
assert((await readFile(join(dist, '404.html'), 'utf8')).includes('Evidence not found'));

const expectedRedirects = new Map([
  [`/v1/records/${recordId}`, `/evidence/${recordId}/record.json`],
  [`/v1/records/${recordId}/evidence`, `/evidence/${recordId}/evidence.json`],
  [`/v1/badges/${recordId}.svg`, `/evidence/${recordId}/scoped-status.svg`],
]);
assert.equal(deployment.redirects?.length, expectedRedirects.size, 'unexpected V1 resource redirect count');
for (const redirect of deployment.redirects) {
  assert.equal(redirect.destination, expectedRedirects.get(redirect.source), `unexpected redirect ${redirect.source}`);
  assert.equal(redirect.permanent, true, `resource redirect must be permanent: ${redirect.source}`);
  await stat(join(dist, redirect.destination.slice(1)));
}
const preservedHtml = await readFile(join(dist, `evidence/${recordId}/qualified-release.html`), 'utf8');
for (const source of expectedRedirects.keys()) assert(preservedHtml.includes(`href="${source}"`));
const csp = deployment.headers
  .flatMap((rule) => rule.headers ?? [])
  .find((header) => header.key === 'Content-Security-Policy')?.value;
assert(csp?.includes("default-src 'self'") && csp.includes("object-src 'none'") && csp.includes("frame-ancestors 'none'"));

assert(clientBytes < 100_000, `client JS + CSS exceeds 100 kB (${clientBytes} bytes)`);
console.log(`BUILT_SITE_INTEGRITY_GREEN pages=${allHtml.length} client_bytes=${clientBytes}`);
