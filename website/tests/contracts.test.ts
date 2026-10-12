import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

import Ajv from 'ajv';
import Ajv2020 from 'ajv/dist/2020.js';
import { describe, expect, test } from 'vitest';
import { recognizeLocalFile, selectQualifiedHandoff } from '../src/scripts/import-workbench';

const website = join(dirname(fileURLToPath(import.meta.url)), '..');
const dist = join(website, 'dist');
const recordId = 'mg-l4yaml-source-check-20261010';
const resolveRecordId = 'mg-living-warrant-openai-jpl-20261010';
const resolveSnapshotSha256 = 'b95297a081d513fb0ec145a776cc997eaed18109d6b2af39fa8e61f6d637af41';
const resolveScenariosSha256 = 'ed458ccbee85e3aa3f49d9d38e7ad5380515d00d707bac09c584cc4955b88181';
const sourceCheckContentSha256 = 'f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb';
const sourceCheckTransportSha256 = '7b59ee76a39995f35a0feb0f4d91a3c6ab1234393143480c4f3e361a79fee703';
const resolveTransportSha256 = '0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87';
const discoveryV1Sha256 = '9b135705cfccf6f162e247e6c1a4380f9b74d8a0ca295072611647c9cd5ada18';
const offlineConsumerSha256 = '27a9be606040cc94a47c9b903dfc1cb24a86cbbc4e05ce71040c6c3d6e8d527b';
const offlineBundleSha256 = '957080db79555f982fd3a314c263cf5177ef506969229e856897f0b19ccc1d62';
const offlinePolicySha256 = '09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a';
const offlineReplaySha256 = '8c7b30e1eb2a24d2960e170d36652ca95aa71b41075f673abe394e154ae66668';
const typescriptConsumerSha256 = 'e7360df24b2fd0900c8ea88ccb1689163cec73a6c2e2347e4ab2b23b4d01bc2e';
const resolvePublicRoot = `https://mathgraph.org/evidence/${resolveRecordId}`;
const resolveOfflineRoot = `${resolvePublicRoot}/offline`;

async function text(path: string): Promise<string> {
  return readFile(join(dist, path), 'utf8');
}

async function json(path: string): Promise<Record<string, any>> {
  return JSON.parse(await text(path)) as Record<string, any>;
}

describe('agent discovery contracts', () => {
  test('mirrors the non-authoritative source catalogue schemas and shares restricted JCS bytes with Python', async () => {
    const repository = join(website, '..');
    const ajv = new Ajv2020({ allErrors: true, strict: true });
    for (const name of ['source-catalogue-manifest-v1.schema.json', 'source-catalogue-shard-v1.schema.json']) {
      const protocol = await readFile(join(repository, 'protocol/schemas', name));
      expect(await readFile(join(website, 'public/schemas', name))).toEqual(protocol);
      expect(await readFile(join(dist, 'schemas', name))).toEqual(protocol);
      expect(ajv.compile(JSON.parse(protocol.toString('utf8')))).toBeTypeOf('function');
    }
    // Independent test-side encoder; the browser adapter belongs to the later projection task.
    function canonical(value: unknown): string {
      if (value === null || typeof value === 'boolean') return JSON.stringify(value);
      if (typeof value === 'number') {
        if (!Number.isSafeInteger(value) || Object.is(value, -0)) throw new Error('unsupported number');
        return JSON.stringify(value);
      }
      if (typeof value === 'string') {
        if (/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(value)) throw new Error('lone surrogate');
        return JSON.stringify(value);
      }
      if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
      if (typeof value === 'object' && Object.getPrototypeOf(value) === Object.prototype) {
        return `{${Object.keys(value).sort().map(key => `${canonical(key)}:${canonical((value as Record<string, unknown>)[key])}`).join(',')}}`;
      }
      throw new Error('unsupported value');
    }
    const vectors = JSON.parse(await readFile(join(repository, 'tests/fixtures/source_catalogue_v1/canonical-vectors.json'), 'utf8'));
    const { stdout } = await promisify(execFile)('python3', ['-c',
      'import json; from pathlib import Path; from mathgraph_protocol.source_catalogue_v1 import canonical_bytes; print(json.dumps([canonical_bytes(v["value"]).hex() for v in json.loads(Path("tests/fixtures/source_catalogue_v1/canonical-vectors.json").read_text())]))',
    ], { cwd: repository });
    const pythonBytes = JSON.parse(stdout);
    vectors.forEach((vector: { value: unknown; canonical: string }, index: number) => {
      const bytes = Buffer.from(canonical(vector.value), 'utf8');
      expect(bytes).toEqual(Buffer.from(vector.canonical, 'utf8'));
      expect(bytes.toString('hex')).toBe(pythonBytes[index]);
    });
    for (const value of [1.5, -0, NaN, Infinity, 9007199254740992, '\uD800']) expect(() => canonical(value)).toThrow();
  });

  test('recognizes only bounded exact local bytes and never accepts browser output as an import result', async () => {
    const bytes = await readFile(join(website, `public/evidence/${recordId}/record.json`));
    const preview = await recognizeLocalFile(new File([bytes], 'record.json', { type: 'application/json' }));
    expect(preview.status).toBe('EXACT_BYTES_RECOGNIZED');
    expect(preview.schema).toBe('mathgraph.browser-recognition.v1');
    expect(preview.processing_mode).toBe('LOCAL_BROWSER_EXACT_BYTE_RECOGNITION');
    expect(preview.authority).toBe('NONE');
    expect(preview.proof_replay).toBe('NOT_PERFORMED');
    expect(preview.kernel_replay).toBe('NOT_PERFORMED');
    expect(preview.source_suite_replay).toBe('NOT_PERFORMED');
    expect(preview.freshness).toBe('UNKNOWN');
    expect(preview.current_applicability).toBe('UNKNOWN');
    expect(preview.authorization).toBe('READ_ONLY_NO_AUTOMATIC_AUTHORIZATION');
    const fixture = JSON.parse(await readFile(join(website, 'tests/fixtures/import-workflow.json'), 'utf8'));
    expect(preview.record).toMatchObject(fixture);
    expect(preview.handoff).toEqual({ status: 'UNKNOWN', reason: 'NOT_SELECTED' });
    const handedOff = selectQualifiedHandoff(preview, 'finite_parser_acceptance');
    expect(handedOff.record).toEqual(preview.record);
    expect(handedOff.handoff).toEqual({
      status: 'QUALIFIED_RECORD_HANDOFF', historical_result: 'WARRANTED_BOUNDED',
      goal: 'finite_parser_acceptance', href: `/records/${recordId}/v1/`,
    });
    const unsupported = selectQualifiedHandoff(handedOff, 'whole_language_correctness');
    expect(unsupported.record).toEqual(preview.record);
    expect(unsupported.handoff).toEqual({ status: 'UNKNOWN', reason: 'UNSUPPORTED_ROUTE' });
    const schema = await json('schemas/import-result-v1.schema.json');
    const ajv = new Ajv2020({ allErrors: true, strict: true });
    expect(ajv.validate(schema, handedOff)).toBe(false);
    // Values that permissive JSON parsers might normalize must never be interpreted.
    for (const candidate of [
      null, 'https://mathgraph.org/record.json',
      new File([bytes, '\n'], 'record.json'),
      new File([bytes.toString('utf8').replace('"expected_accept": 31', '"expected_accept": 32')], 'record.json'),
      new File([bytes.toString('utf8').replace('"admission": {', '"admission": {}, "admission": {')], 'record.json'),
      new File([bytes.toString('utf8').replace('"expected_accept": 31', '"expected_accept": NaN')], 'record.json'),
      new File([new Uint8Array([0xef, 0xbb, 0xbf]), bytes], 'record.json'),
      new File([bytes.toString('utf8').replace(recordId, 'untrusted-producer')], 'record.json'),
      new File(['<script>throw new Error("not JSON")</script>'], 'record.json'),
      new File([new Uint8Array(65537)], 'record.json'),
    ]) {
      const result = await recognizeLocalFile(candidate);
      expect(result.status).toBe('UNKNOWN');
      expect(result.record).toBeNull();
      expect(JSON.stringify(result)).not.toContain('WARRANTED');
      expect(selectQualifiedHandoff(result, 'finite_parser_acceptance').handoff.status).toBe('UNKNOWN');
    }
  });

  test('publishes the independent import result schema without widening historical authority', async () => {
    const repository = join(website, '..');
    const name = 'import-result-v1.schema.json';
    const [schemaBytes, publicBytes, resultBytes, recordBytes] = await Promise.all([
      readFile(join(repository, 'protocol/schemas', name)),
      readFile(join(dist, 'schemas', name)),
      readFile(join(repository, 'conformance/import_v1/fixtures/result.json')),
      readFile(join(repository, 'conformance/import_v1/fixtures/record.json')),
    ]);
    expect(publicBytes).toEqual(schemaBytes);
    expect(recordBytes).toEqual(await readFile(join(dist, `evidence/${recordId}/record.json`)));
    expect(createHash('sha256').update(recordBytes).digest('hex')).toBe(sourceCheckTransportSha256);
    expect(createHash('sha256').update(resultBytes).digest('hex')).toBe('55ff4aa97dcc33deb2d319d41e4d91783492e7eff5c3048697f6a310cbcdab8b');
    const ajv = new Ajv2020({ allErrors: true, strict: true });
    const schema = JSON.parse(schemaBytes.toString('utf8'));
    const result = JSON.parse(resultBytes.toString('utf8'));
    expect(result.processing_mode).toBe('INDEPENDENT_OFFLINE_HISTORICAL_RECORD_POLICY_VALIDATION');
    expect(result.consumer_authority).toEqual({
      boundary: 'EXACT_HISTORICAL_RECEIPT_AND_LOCAL_POLICY_ONLY',
      kernel_replay: 'NOT_PERFORMED', kernel_admission: 'NOT_PERFORMED',
      current_truth: 'NOT_ESTABLISHED',
    });
    expect(result.source_suite_replay).toBe('NOT_PERFORMED');
    expect(result.evidence.authority).toBe('LEAN_GUARDS_AND_COMPILED_TRYPARSE');
    expect(ajv.validate(schema, result), ajv.errorsText()).toBe(true);
    for (const [key, value] of [
      ['epistemic_status', 'VERIFIED_PROOF'], ['lifecycle', 'CURRENT'],
      ['freshness', 'CHECKED'], ['current_applicability', 'APPLICABLE'],
      ['authorization', 'EXECUTE'], ['producer_verdict', 'VERIFIED_PROOF'],
      ['processing_mode', 'KERNEL_VERIFICATION'], ['source_suite_replay', 'PERFORMED'],
    ]) expect(ajv.validate(schema, { ...result, [key]: value })).toBe(false);
    for (const key of ['processing_mode', 'consumer_authority', 'source_suite_replay']) {
      const missing = { ...result };
      delete missing[key];
      expect(ajv.validate(schema, missing)).toBe(false);
    }
    for (const [key, value] of [
      ['boundary', 'SOURCE_SUITE_EXECUTION'], ['kernel_replay', 'PERFORMED'],
      ['kernel_admission', 'PERFORMED'], ['current_truth', 'ESTABLISHED'],
    ]) expect(ajv.validate(schema, {
      ...result, consumer_authority: { ...result.consumer_authority, [key]: value },
    })).toBe(false);
  });

  test('publishes byte-identical Resolve transport schemas that accept the immutable fixtures', async () => {
    const repository = join(website, '..');
    const names = ['resolve-bundle-v1.schema.json', 'resolve-trust-policy-v1.schema.json'];
    const [bundleSchemaBytes, policySchemaBytes, publicBundleSchemaBytes, publicPolicySchemaBytes] = await Promise.all([
      readFile(join(repository, 'protocol/schemas', names[0])),
      readFile(join(repository, 'protocol/schemas', names[1])),
      readFile(join(dist, 'schemas', names[0])),
      readFile(join(dist, 'schemas', names[1])),
    ]);

    expect(publicBundleSchemaBytes).toEqual(bundleSchemaBytes);
    expect(publicPolicySchemaBytes).toEqual(policySchemaBytes);

    const bundleSchema = JSON.parse(bundleSchemaBytes.toString('utf8')) as Record<string, any>;
    const policySchema = JSON.parse(policySchemaBytes.toString('utf8')) as Record<string, any>;
    const [bundle, policy] = await Promise.all([
      json(`evidence/${resolveRecordId}/offline/bundle.json`),
      json(`evidence/${resolveRecordId}/offline/trust-policy.json`),
    ]);
    const ajv = new Ajv2020({ allErrors: true, strict: true });
    ajv.addSchema(bundleSchema);
    expect(ajv.validate(policySchema, policy), ajv.errorsText()).toBe(true);
    expect(ajv.validate(bundleSchema, bundle), ajv.errorsText()).toBe(true);
  });

  test('publishes schema-valid discovery and record index documents', async () => {
    const ajv = new Ajv({ allErrors: true, strict: true });
    const [discovery, index, record, discoverySchema, indexSchema, discoveryV1Bytes] = await Promise.all([
      json('.well-known/mathgraph.json'),
      json('records/index.json'),
      json(`evidence/${recordId}/record.json`),
      json('schemas/discovery-v3.schema.json'),
      json('schemas/record-index-v2.schema.json'),
      readFile(join(dist, 'schemas/discovery-v1.schema.json')),
    ]);

    expect(ajv.validate(discoverySchema, discovery), ajv.errorsText()).toBe(true);
    expect(ajv.validate(indexSchema, index), ajv.errorsText()).toBe(true);
    expect(createHash('sha256').update(discoveryV1Bytes).digest('hex')).toBe(discoveryV1Sha256);
    expect(createHash('sha256').update(await readFile(join(dist, 'schemas/discovery-v2.schema.json'))).digest('hex')).toBe('827214b81d0c45a36cf3d9fc25d23910c9da19c47553d69411a893b4049941fc');
    expect(discovery.$schema).toBe('https://mathgraph.org/schemas/discovery-v3.schema.json');
    expect(discovery.schema).toBe('mathgraph.discovery.v3');
    expect(discovery.canonical_origin).toBe('https://mathgraph.org');
    expect(JSON.stringify(discovery)).not.toContain('vercel.app');
    expect(discovery.capabilities).toEqual({
      static_records: 'IMPLEMENTED',
      resolve_explorer: 'IMPLEMENTED_READ_ONLY',
      offline_resolve_replay: 'BOUNDED_QUALIFIED',
      public_resolver: 'NOT_DEPLOYED',
      discover_interface: 'IMPLEMENTED_LOCAL_ADVISORY',
      develop_interface: 'QUALIFIED_BOUNDED_OFFLINE',
      capabilities_registry: 'STATIC_REGISTRY',
      lean_profile: 'PROPOSED',
      mcp: 'PROPOSED',
    });
    expect(discovery.interfaces.check).toEqual({
      maturity: 'IMPLEMENTED_AT_QUALIFIED_BOUNDARY',
      mode: 'STATIC_RECORD',
      record_id: recordId,
      record_page: `https://mathgraph.org/records/${recordId}/v1/`,
      record_json: `https://mathgraph.org/evidence/${recordId}/record.json`,
    });
    expect(discovery.interfaces.resolve).toEqual({
      maturity: 'BOUNDED_QUALIFIED',
      mode: 'OFFLINE_REPLAY',
      record_id: resolveRecordId,
      explorer: 'https://mathgraph.org/resolve/',
      record_page: `https://mathgraph.org/records/${resolveRecordId}/v1/`,
      record_json: `${resolvePublicRoot}/record.json`,
      scenarios_json: `${resolvePublicRoot}/scenarios.json`,
      offline_consumer: `${resolveOfflineRoot}/consumer.py`,
      offline_consumer_sha256: offlineConsumerSha256,
      offline_bundle: `${resolveOfflineRoot}/bundle.json`,
      offline_bundle_sha256: offlineBundleSha256,
      offline_trust_policy: `${resolveOfflineRoot}/trust-policy.json`,
      offline_trust_policy_sha256: offlinePolicySha256,
      offline_replay_output_sha256: offlineReplaySha256,
      typescript_consumer: 'https://mathgraph.org/examples/resolve-consumer-v1.ts',
      typescript_consumer_sha256: typescriptConsumerSha256,
      current_applicability: 'UNKNOWN',
      freshness: 'NOT_CHECKED',
    });
    expect(discovery.interfaces.discover.public_interface).toBe('NOT_DEPLOYED');
    expect(discovery.interfaces.develop.public_interface).toBe('NOT_DEPLOYED');
    expect(discovery.interfaces.capabilities.qualified_entries).toBe(1);
    expect(discovery.integrity_notice).toMatch(/integrity.*not.*authenticity/i);
    expect(discovery.repository_provenance.authentication_status).toBe('UNSIGNED_PROVENANCE_ONLY');
    expect(discovery.repository_provenance.catalogue_source).toBe('https://github.com/metalogiclabs/mathgraph/blob/1a38f63f01b08f62854d289e4a64f8669b79e59f/website/src/data/record-index.json');

    const generatedAt = Date.parse(index.generated_at);
    expect(Number.isFinite(generatedAt)).toBe(true);
    expect(generatedAt).toBeLessThanOrEqual(Date.now());
    expect(index.lifecycle_freshness).toEqual({
      basis: 'CLIENT_FETCH_TIME',
      max_age_seconds: 300,
      meaning: 'generated_at is publication time; set fetched_at when received and re-fetch before max_age_seconds elapse.',
      records_are_immutable: true,
    });
    expect(discovery.freshness).toEqual({
      basis: 'CLIENT_FETCH_TIME',
      record_index_max_age_seconds: 300,
      lifecycle_meaning: 'generated_at is publication time; set fetched_at when received and re-fetch before max_age_seconds elapse.',
    });
    expect(index.records).toHaveLength(2);
    expect(discovery.schemas.discovery_v1).toBe('https://mathgraph.org/schemas/discovery-v1.schema.json');
    expect(discovery.schemas.discovery_v2).toBe('https://mathgraph.org/schemas/discovery-v2.schema.json');
    expect(discovery.schemas.record_index_v2).toBe('https://mathgraph.org/schemas/record-index-v2.schema.json');
    expect(index.records[0].id).toBe(recordId);
    expect(index.records[0].record_page_url).toBe(`https://mathgraph.org/records/${recordId}/v1/`);
    expect(index.records[0].record_json_url).toBe(`https://mathgraph.org/evidence/${recordId}/record.json`);
    expect(index.records[0].record_content_sha256).toBe(record.content_sha256);
    expect(index.records[0].scope.source_commit).toBe(record.source.commit);
    expect(index.records[0].scope.external_suite_commit).toBe(record.source.external_suite_commit);
    expect(index.records[0].historic_status).toBe('WARRANTED_BOUNDED');
    expect(index.records[0].lifecycle).toBe('CURRENT');
    expect(index.records[0].scope).toEqual({
      match: 'EXACT',
      source_commit: '62bf7077910e888a0bc8adfc8e08a5f500ff3ca3',
      external_suite_commit: 'da267a5c4782e7361e82889e76c0dc7df0e1e870',
      supported_goals: ['finite_parser_acceptance'],
      mismatch_status: 'UNKNOWN',
    });
  });

  test('publishes concise agent instructions with canonical resources and limits', async () => {
    const llms = await text('llms.txt');

    for (const url of [
      'https://mathgraph.org/agents/',
      'https://mathgraph.org/records/index.json',
      'https://mathgraph.org/schemas/record-index-v2.schema.json',
      'https://mathgraph.org/schemas/public-consequence-record-v1.schema.json',
      'https://mathgraph.org/schemas/lean-evidence-profile-draft-1.schema.json',
      `https://mathgraph.org/evidence/${recordId}/record.json`,
      `https://mathgraph.org/records/${recordId}/v1/`,
      `${resolvePublicRoot}/record.json`,
      `${resolvePublicRoot}/scenarios.json`,
      `https://mathgraph.org/records/${resolveRecordId}/v1/`,
      `${resolveOfflineRoot}/consumer.py`,
      `${resolveOfflineRoot}/bundle.json`,
      `${resolveOfflineRoot}/trust-policy.json`,
      'https://mathgraph.org/examples/resolve-consumer-v1.ts',
    ]) {
      expect(llms).toContain(url);
    }
    for (const value of [
      'SOURCE_CHECK',
      'RESOLUTION_SNAPSHOT',
      'mathgraph.public-consequence-record.v1',
      'mathgraph.living-warrant-snapshot.v1',
      sourceCheckContentSha256,
      sourceCheckTransportSha256,
      resolveSnapshotSha256,
      resolveTransportSha256,
      resolveScenariosSha256,
      offlineConsumerSha256,
      offlineBundleSha256,
      offlinePolicySha256,
      offlineReplaySha256,
      typescriptConsumerSha256,
    ]) expect(llms).toContain(value);
    expect(llms).toMatch(/exact record ID, version, source pin, suite pin, and supported goal/i);
    expect(llms).toMatch(/mismatch.*UNKNOWN/i);
    expect(llms).toMatch(/digest.*integrity.*not.*authenticity/i);
    expect(llms).toMatch(/current applicability.*UNKNOWN/i);
    expect(llms).toMatch(/freshness.*NOT_CHECKED/i);
    expect(llms).toMatch(/public resolver.*NOT_DEPLOYED/i);
    expect(llms).toMatch(/MCP.*PROPOSED/i);
    expect(llms).toContain('https://mathgraph.org/about/');
    expect(llms).toContain('https://mathgraph.org/contact/');
    expect(llms).toMatch(/resolve-consumer-v1\.ts.*text\/plain; charset=utf-8/i);
    expect(llms).toMatch(/browser.*presentation.*authority.*NONE/i);
    expect(llms).not.toContain('vercel.app');
  });

  test('keeps discovery V3 byte-identical while narrowing the TypeScript content type in both Vercel configs', async () => {
    const repository = join(website, '..');
    const [rootConfigBytes, websiteConfigBytes, discoveryBytes, sourceConsumer, builtConsumer] = await Promise.all([
      readFile(join(repository, 'vercel.json')),
      readFile(join(website, 'vercel.json')),
      readFile(join(website, 'public/.well-known/mathgraph.json')),
      readFile(join(website, 'public/examples/resolve-consumer-v1.ts')),
      readFile(join(dist, 'examples/resolve-consumer-v1.ts')),
    ]);
    const rootConfig = JSON.parse(rootConfigBytes.toString('utf8'));
    const websiteConfig = JSON.parse(websiteConfigBytes.toString('utf8'));
    for (const key of ['cleanUrls', 'redirects', 'headers']) expect(rootConfig[key]).toEqual(websiteConfig[key]);
    const contentTypeRules = websiteConfig.headers.filter((rule: any) =>
      rule.headers?.some((header: any) => header.key.toLowerCase() === 'content-type'));
    expect(contentTypeRules).toEqual([{
      source: '/examples/resolve-consumer-v1.ts',
      headers: [{ key: 'Content-Type', value: 'text/plain; charset=utf-8' }],
    }]);
    const narrowRuleIndex = websiteConfig.headers.findIndex((rule: any) => rule.source === '/examples/resolve-consumer-v1.ts');
    const catchAllIndex = websiteConfig.headers.findIndex((rule: any) => rule.source === '/(.*)');
    expect(narrowRuleIndex).toBeGreaterThanOrEqual(0);
    expect(narrowRuleIndex).toBeLessThan(catchAllIndex);
    expect(websiteConfig.headers[catchAllIndex].headers).toContainEqual({ key: 'X-Content-Type-Options', value: 'nosniff' });
    expect(createHash('sha256').update(sourceConsumer).digest('hex')).toBe(typescriptConsumerSha256);
    expect(builtConsumer).toEqual(sourceConsumer);
    expect(createHash('sha256').update(discoveryBytes).digest('hex')).toBe('3bde9969e635a39153f58b7f237979b954302c48878c2266dffe2ab9afd16540');
  });

  test('advertises the Resolve transport schemas consistently without adding authentication', async () => {
    const [discovery, discoverySchema, llms, developers] = await Promise.all([
      json('.well-known/mathgraph.json'),
      json('schemas/discovery-v3.schema.json'),
      text('llms.txt'),
      text('developers/index.html'),
    ]);
    const ajv = new Ajv({ allErrors: true, strict: true });
    for (const [key, name] of [
      ['resolve_bundle_v1', 'resolve-bundle-v1.schema.json'],
      ['resolve_trust_policy_v1', 'resolve-trust-policy-v1.schema.json'],
    ]) {
      const url = `https://mathgraph.org/schemas/${name}`;
      expect(discovery.schemas[key]).toBe(url);
      expect(llms).toContain(url);
      expect(developers).toContain(`href="/schemas/${name}"`);
      expect((await json(`schemas/${name}`)).$id).toBe(url);
      const missing = structuredClone(discovery);
      delete missing.schemas[key];
      expect(ajv.validate(discoverySchema, missing)).toBe(false);
      const substituted = structuredClone(discovery);
      substituted.schemas[key] = 'https://mathgraph.org/schemas/unrelated.schema.json';
      expect(ajv.validate(discoverySchema, substituted)).toBe(false);
    }
    expect(llms).toMatch(/schemas.*do not authenticate.*records/i);
    expect(developers.replace(/<[^>]+>/g, ' ')).toMatch(/schemas.*do not authenticate.*records/i);
  });

  test('includes human and permanent record routes in the generated sitemap', async () => {
    const sitemap = await text('sitemap.xml');
    for (const route of [
      '/agents/',
      '/resolve/',
      '/protocol/profiles/lean/',
      `/records/${recordId}/`,
      `/records/${recordId}/v1/`,
      '/records/mg-living-warrant-openai-jpl-20261010/',
      '/records/mg-living-warrant-openai-jpl-20261010/v1/',
    ]) {
      expect(sitemap).toContain(`<loc>https://mathgraph.org${route}</loc>`);
    }
  });
  test('renders resolution snapshots with separate axes on both routes', async () => {
    for (const suffix of ['', 'v1/']) {
      const html = await text(`records/mg-living-warrant-openai-jpl-20261010/${suffix}index.html`);
      expect(html).toContain('MathGraph Resolve — When Mathematical Evidence Changes');
      for (const value of ['SCOPED_MIXED', 'Catalogue lifecycle', 'BOUNDED_QUALIFIED', 'READ_ONLY_NO_AUTOMATIC_AUTHORIZATION', 'Current applicability', 'NOT_CHECKED']) expect(html).toContain(value);
      expect(html).not.toContain('Warranted — bounded');
      expect(html).toContain('does not rerun the original JPL Lean proof');
    }
  });

  test('binds the Resolve explorer to the exact immutable scenarios artifact', async () => {
    for (const route of ['resolve/index.html', `records/${resolveRecordId}/v1/index.html`]) {
      const html = await text(route);
      expect(html).toContain(`data-record-id="${resolveRecordId}"`);
      expect(html).toContain(`data-snapshot-sha256="${resolveSnapshotSha256}"`);
      expect(html).toContain(`data-scenarios-sha256="${resolveScenariosSha256}"`);
      expect(html).toContain(`data-scenarios-url="/evidence/${resolveRecordId}/scenarios.json"`);
      expect(html).toContain('data-default-classification="PUBLISHED_RECORD"');
      expect(html).toContain('data-default-scenario="published-after"');
      expect(html).not.toContain('<script type="application/json"');
      expect(html).not.toContain('&quot;SYNTHETIC_CONFORMANCE&quot;:');
    }
  });

  test('publishes the exact Resolve JSON resources and exposes their identities from the detail page', async () => {
    const [record, scenarios, html] = await Promise.all([
      json(`evidence/${resolveRecordId}/record.json`),
      json(`evidence/${resolveRecordId}/scenarios.json`),
      text(`records/${resolveRecordId}/v1/index.html`),
    ]);

    expect(record.id).toBe(resolveRecordId);
    expect(record.snapshot_sha256).toBe(resolveSnapshotSha256);
    expect(scenarios.record_id).toBe(resolveRecordId);
    expect(scenarios.snapshot_sha256).toBe(resolveSnapshotSha256);
    expect(scenarios.PUBLISHED_RECORD.default_scenario).toBe('published-after');
    expect(html).toContain(`/evidence/${resolveRecordId}/record.json`);
    expect(html).toContain(`/evidence/${resolveRecordId}/scenarios.json`);
    expect(html).toContain(resolveSnapshotSha256);
    expect(html).toContain(resolveScenariosSha256);
  });
});
