import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readdir, readFile, stat } from 'node:fs/promises';
import { extname, join } from 'node:path';

import sharp from 'sharp';

const root = new URL('..', import.meta.url).pathname;
const repositoryRoot = new URL('../..', import.meta.url).pathname;
const dist = join(root, 'dist');
const recordId = 'mg-l4yaml-source-check-20261010';
const sourceRecordPath = join(root, 'src/data/l4yaml-record.json');
const publicRecordPath = join(root, `public/evidence/${recordId}/record.json`);
const builtRecordPath = join(dist, `evidence/${recordId}/record.json`);
const builtEvidencePath = join(dist, `evidence/${recordId}/evidence.json`);
const presentationPath = join(dist, `records/${recordId}/v1/metadata.json`);
const [sourceBytes, publicBytes, builtBytes] = await Promise.all([
  readFile(sourceRecordPath),
  readFile(publicRecordPath),
  readFile(builtRecordPath),
]);
const deployment = JSON.parse(await readFile(join(root, 'vercel.json'), 'utf8'));
const repositoryDeployment = JSON.parse(await readFile(join(repositoryRoot, 'vercel.json'), 'utf8'));

assert.equal(repositoryDeployment.installCommand, 'cd website && npm ci --ignore-scripts');
assert.equal(repositoryDeployment.buildCommand, 'cd website && npm run build');
assert.equal(repositoryDeployment.outputDirectory, 'website/dist');
for (const key of ['cleanUrls', 'redirects', 'headers']) {
  assert.deepEqual(repositoryDeployment[key], deployment[key], `root Vercel ${key} must match website policy`);
}

assert.deepEqual(publicBytes, sourceBytes, 'public record must be the exact frozen record');
assert.deepEqual(builtBytes, sourceBytes, 'built record must be the exact frozen record');
const record = JSON.parse(sourceBytes);
const recordHtml = await readFile(join(dist, `records/${recordId}/index.html`), 'utf8');
const versionedRecordHtml = await readFile(join(dist, `records/${recordId}/v1/index.html`), 'utf8');
const homeHtml = await readFile(join(dist, 'index.html'), 'utf8');
const developersHtml = await readFile(join(dist, 'developers/index.html'), 'utf8');
const discovery = JSON.parse(await readFile(join(dist, '.well-known/mathgraph.json'), 'utf8'));
const index = JSON.parse(await readFile(join(dist, 'records/index.json'), 'utf8'));
const presentation = JSON.parse(await readFile(presentationPath, 'utf8'));
const entry = index.records.find((candidate) => candidate.id === recordId && candidate.version === 1);
assert(entry, 'machine catalogue must expose the qualified V1 record');
const allHtml = [];
let clientBytes = 0;

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function canonicalJson(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  return `{${Object.entries(value)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, child]) => `${JSON.stringify(key)}:${canonicalJson(child)}`)
    .join(',')}}`;
}

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
assert(homeHtml.includes('EXACT_SCOPE_MATCH') && homeHtml.includes('SOURCE_PIN_MISMATCH') && homeHtml.includes('UNSUPPORTED_GOAL'));
assert.equal(entry.record_content_sha256, record.content_sha256);
assert.equal(entry.scope.source_commit, record.source.commit);
assert.equal(entry.scope.external_suite_commit, record.source.external_suite_commit);
assert.equal(entry.historic_status, 'WARRANTED_BOUNDED');
assert.equal(entry.lifecycle, 'CURRENT');
assert.equal(entry.scope.mismatch_status, 'UNKNOWN');
assert.equal(discovery.record_index, 'https://mathgraph.org/records/index.json');
assert.equal(discovery.freshness.record_index_max_age_seconds, index.lifecycle_freshness.max_age_seconds);
assert.equal(discovery.repository_provenance.authentication_status, 'UNSIGNED_PROVENANCE_ONLY');
assert.equal(entry.record_page_url, `https://mathgraph.org/records/${recordId}/v1/`);
for (const html of [recordHtml, versionedRecordHtml]) {
  assert(html.includes(`<link rel="canonical" href="${entry.record_page_url}">`));
  assert(html.includes(record.content_sha256));
  assert(html.includes('Warranted — bounded'));
  assert(html.includes('Current'));
}
assert(developersHtml.includes(`/v1/badges/${recordId}.svg`));
assert(developersHtml.includes(`/records/${recordId}/v1/`));
assert(/not a universal truth badge/i.test(developersHtml));
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

assert.equal(sha256(sourceBytes), entry.record_transport_sha256);
assert.equal(sha256(await readFile(builtEvidencePath)), entry.evidence_transport_sha256);
const unsignedPresentation = structuredClone(presentation);
delete unsignedPresentation.content_sha256;
assert.equal(sha256(canonicalJson(unsignedPresentation)), entry.presentation_content_sha256);
assert.equal(presentation.content_sha256, entry.presentation_content_sha256);

for (const filename of ['record.json', 'evidence.json', 'qualified-release.html', 'scoped-status.svg', 'openapi.preview.json']) {
  const [published, built] = await Promise.all([
    readFile(join(root, `public/evidence/${recordId}`, filename)),
    readFile(join(dist, `evidence/${recordId}`, filename)),
  ]);
  assert.deepEqual(built, published, `qualified publisher asset changed during build: ${filename}`);
}

const socialPath = join(dist, `social/records/${recordId}-v1.png`);
const social = await sharp(socialPath).metadata();
assert.equal(social.width, 1200);
assert.equal(social.height, 630);
assert(versionedRecordHtml.includes(`https://mathgraph.org/social/records/${recordId}-v1.png`));

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

const cacheHeaders = new Map(
  deployment.headers.map((rule) => [
    rule.source,
    rule.headers?.find((header) => header.key.toLowerCase() === 'cache-control')?.value,
  ]),
);
for (const source of ['/evidence/(.*)', '/schemas/(.*)', '/social/(.*)']) {
  assert.equal(cacheHeaders.get(source), 'public, max-age=31536000, immutable', `immutable cache policy missing for ${source}`);
}
for (const source of ['/records/index.json', '/llms.txt', '/.well-known/mathgraph.json', '/records/(.*)/v(.*)/metadata.json', '/records/(.*)/v(.*)']) {
  assert.equal(cacheHeaders.get(source), 'public, max-age=0, s-maxage=300, stale-while-revalidate=60', `fresh catalogue policy missing for ${source}`);
}

assert(clientBytes < 100_000, `client JS + CSS exceeds 100 kB (${clientBytes} bytes)`);
console.log(`BUILT_SITE_INTEGRITY_GREEN pages=${allHtml.length} client_bytes=${clientBytes} catalogue=V1 social=1200x630`);
