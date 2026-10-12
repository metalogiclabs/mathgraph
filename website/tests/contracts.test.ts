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
const sourceCatalogueManifestSha256 = '5974ac4d68b1e090d511964cd61237565b80d39b5e47e9966171d4d8bcd2fe68';
const sourceCatalogueSearchSha256 = 'af346a9d68adfaacddf4103004d97976e6ebc106e2b8b0bc199fb0a5fabeb60b';
const sourceCatalogueConsumerSha256 = '583dcfca46854f56469cdda865b5da62b1068e985bdce411dac9c587e556ca5d';
const sourceCataloguePolicySha256 = 'c3cdec2b2c784728621bb8c25a055a1e73d67d3c1c922b7ab62b09003399e1c9';
const sourceCatalogueReadmeSha256 = '787f1dd6cf9c7b24c1adc7f8d2c31bd44d637c77574f091fc19414761ca1f323';
const sourceCatalogueSnapshotCommit = '8e8f5f529b44852815627206dc5b45062f0c96d6';
const sourceCataloguePublicationCommit = '7519de6a51e524caf70df51d37389ff42d430d43';
const sourceCatalogueWrapperCommit = 'eb3149b70f0cdf39109c775898b19a26574c27e6';
const sourceCatalogueProducerCommit = 'e6643d8e3d207893713da94041ff3822c1190457';
const sourceCatalogueManifestSchemaSha256 = 'efd1f70039e8205f8e0cbf861ce9796604fbc56c224fec0b43834135b68f17cc';
const sourceCatalogueShardSchemaSha256 = '363cf2a199f2c60fe026b74ecbab3c78d7e6d3fc0d3422ae6528c89c871f8683';
const discoveryV3Sha256 = '3bde9969e635a39153f58b7f237979b954302c48878c2266dffe2ab9afd16540';
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

  test('publishes schema-valid V4 discovery, preserves V3 bytes, and links the exact source catalogue', async () => {
    const ajv = new Ajv({ allErrors: true, strict: true });
    const [discovery, historicalV3, index, record, discoverySchema, historicalV3Schema, indexSchema, discoveryV1Bytes] = await Promise.all([
      json('.well-known/mathgraph.json'),
      json('.well-known/mathgraph-v3.json'),
      json('records/index.json'),
      json(`evidence/${recordId}/record.json`),
      json('schemas/discovery-v4.schema.json'),
      json('schemas/discovery-v3.schema.json'),
      json('schemas/record-index-v2.schema.json'),
      readFile(join(dist, 'schemas/discovery-v1.schema.json')),
    ]);

    expect(ajv.validate(discoverySchema, discovery), ajv.errorsText()).toBe(true);
    expect(ajv.validate(historicalV3Schema, historicalV3), ajv.errorsText()).toBe(true);
    expect(ajv.validate(indexSchema, index), ajv.errorsText()).toBe(true);
    expect(createHash('sha256').update(discoveryV1Bytes).digest('hex')).toBe(discoveryV1Sha256);
    expect(createHash('sha256').update(await readFile(join(dist, 'schemas/discovery-v2.schema.json'))).digest('hex')).toBe('827214b81d0c45a36cf3d9fc25d23910c9da19c47553d69411a893b4049941fc');
    expect(createHash('sha256').update(await readFile(join(dist, 'schemas/discovery-v3.schema.json'))).digest('hex')).toBe('dd5361baaff001d17ca82510d64861d59db846a4af0d07e0f4f0c4556aab8099');
    expect(createHash('sha256').update(await readFile(join(dist, '.well-known/mathgraph-v3.json'))).digest('hex')).toBe(discoveryV3Sha256);
    expect(discovery.$schema).toBe('https://mathgraph.org/schemas/discovery-v4.schema.json');
    expect(discovery.schema).toBe('mathgraph.discovery.v4');
    expect(discovery.canonical_origin).toBe('https://mathgraph.org');
    const discoveryGeneratedAt = Date.parse(discovery.generated_at);
    expect(Number.isFinite(discoveryGeneratedAt)).toBe(true);
    expect(discoveryGeneratedAt).toBeLessThanOrEqual(Date.now());
    expect(JSON.stringify(discovery)).not.toContain('vercel.app');
    expect(discovery.authority).toBe('NONE');
    expect(discovery.authorization).toBe('NONE');
    expect(discovery.record_index).toBe('https://mathgraph.org/records/index.json');
    expect(discovery.capabilities).toMatchObject({
      static_records: 'IMPLEMENTED',
      source_catalogue: 'IMPLEMENTED_STATIC_SOURCE_INDEX',
      public_resolver: 'NOT_DEPLOYED',
      mcp: 'NOT_DEPLOYED',
    });
    expect(discovery.interfaces.capabilities.registry).toBe('https://mathgraph.org/capabilities/index-v1.json');
    expect(discovery.interfaces.capabilities.registry_sha256).toBe('7ae45ef09ce492856234872c12adc6999667b14899a008baddc19687934b1358');
    expect(discovery.source_catalogue).toMatchObject({
      catalogue_id: 'mathlib-v4.34.1-foundations-v1',
      catalogue_version: 1,
      publication_root: 'https://mathgraph.org/catalogues/mathlib/v4.34.1/',
      qualification: {
        basis: 'SAME_OWNER_INDEPENDENT_CONSUMER',
        public_bundle: {
          producer_commit: sourceCatalogueProducerCommit,
          wrapper_commit: sourceCatalogueWrapperCommit,
          run_url: 'https://github.com/metalogiclabs/mathgraph/actions/runs/38242539984',
          trust_policy_sha256: sourceCataloguePolicySha256,
        },
        publication_commit: sourceCataloguePublicationCommit,
        later_regeneration: {
          commit: sourceCatalogueSnapshotCommit,
          run_url: 'https://github.com/metalogiclabs/mathgraph/actions/runs/38246586898',
          scope: 'CATALOGUE_PUBLICATION_REGENERATED_WITH_RUN_SPECIFIC_TRUST_POLICY',
          public_trust_policy_replayed: false,
        },
      },
    });
    expect(discovery.source_catalogue.result).toEqual({
      source_status: 'SOURCE_INDEXED',
      independent_verification: 'NOT_CHECKED',
      current_applicability: 'NOT_CHECKED',
      freshness: 'PINNED_HISTORICAL_SOURCE',
      authority: 'NONE',
      authorization: 'NONE',
    });
    expect(discovery.source_catalogue.semantics).toEqual({ logical_implication: false, semantic_equivalence: false });
    const repositoryRoot = `https://github.com/metalogiclabs/mathgraph/blob/${sourceCatalogueSnapshotCommit}`;
    expect(discovery.source_catalogue.artifacts.manifest).toEqual({
      url: 'https://mathgraph.org/catalogues/mathlib/v4.34.1/manifest.json',
      sha256: sourceCatalogueManifestSha256,
      size_bytes: 319664,
      repository_url: `${repositoryRoot}/website/public/catalogues/mathlib/v4.34.1/manifest.json`,
    });
    expect(discovery.source_catalogue.artifacts.search).toEqual({
      url: 'https://mathgraph.org/catalogues/mathlib/v4.34.1/search.json',
      sha256: sourceCatalogueSearchSha256,
      size_bytes: 1624539,
      repository_url: `${repositoryRoot}/website/public/catalogues/mathlib/v4.34.1/search.json`,
    });
    expect(discovery.source_catalogue.artifacts.manifest_schema).toEqual({
      url: 'https://mathgraph.org/schemas/source-catalogue-manifest-v1.schema.json',
      sha256: sourceCatalogueManifestSchemaSha256,
      size_bytes: 14602,
      repository_url: `${repositoryRoot}/website/public/schemas/source-catalogue-manifest-v1.schema.json`,
    });
    expect(discovery.source_catalogue.artifacts.shard_schema).toEqual({
      url: 'https://mathgraph.org/schemas/source-catalogue-shard-v1.schema.json',
      sha256: sourceCatalogueShardSchemaSha256,
      size_bytes: 14816,
      repository_url: `${repositoryRoot}/website/public/schemas/source-catalogue-shard-v1.schema.json`,
    });
    expect(discovery.source_catalogue.artifacts.consumer).toEqual({
      url: 'https://mathgraph.org/artifacts/conformance/source_catalogue_v1/consumer.py',
      sha256: sourceCatalogueConsumerSha256,
      size_bytes: 34582,
      repository_url: `${repositoryRoot}/conformance/source_catalogue_v1/consumer.py`,
    });
    expect(discovery.source_catalogue.artifacts.trust_policy).toEqual({
      url: 'https://mathgraph.org/artifacts/conformance/source_catalogue_v1/trust-policy.json',
      sha256: sourceCataloguePolicySha256,
      size_bytes: 5751,
      repository_url: `${repositoryRoot}/conformance/source_catalogue_v1/trust-policy.json`,
    });
    expect(discovery.source_catalogue.artifacts.readme).toEqual({
      url: 'https://mathgraph.org/artifacts/conformance/source_catalogue_v1/README.md',
      sha256: sourceCatalogueReadmeSha256,
      size_bytes: 3345,
      repository_url: `${repositoryRoot}/conformance/source_catalogue_v1/README.md`,
    });
    for (const artifact of Object.keys(discovery.source_catalogue.artifacts)) {
      const expected = discovery.source_catalogue.artifacts[artifact];
      for (const [field, replacement] of Object.entries({
        url: 'https://mathgraph.org/unrelated.json',
        sha256: '0'.repeat(64),
        size_bytes: 1,
        repository_url: `${repositoryRoot}/unrelated.json`,
      })) {
        expect(expected[field]).not.toEqual(replacement);
        const changed = structuredClone(discovery);
        changed.source_catalogue.artifacts[artifact][field] = replacement;
        expect(ajv.validate(discoverySchema, changed), `${artifact}.${field} mutation must fail closed`).toBe(false);
      }
    }
    expect(discovery.source_catalogue.source).toEqual({
      repository: 'https://github.com/leanprover-community/mathlib4',
      commit: 'd13f23b723b8a846827a245b89c10fc7d3f11612',
      tree: 'efa132418a56d0e38c56cc412a06df22178dac5c',
      lean_toolchain: 'leanprover/lean4:v4.34.1',
    });
    expect(discovery.source_catalogue.relation_types).toEqual(['DECLARES', 'IMPORTS_MODULE', 'TYPE_REFERENCES']);
    expect(discovery.source_catalogue.repository_snapshot_commit).toBe(sourceCatalogueSnapshotCommit);
    expect(discovery.source_catalogue.repository_snapshot).toBe(`https://github.com/metalogiclabs/mathgraph/tree/${sourceCatalogueSnapshotCommit}`);
    expect(discovery.source_catalogue.repository_authentication).toBe('CHOSEN_TRUST_POLICY_NOT_MATHEMATICAL_TRUTH');
    expect(discovery.historical_discovery).toEqual({
      v3_manifest: 'https://mathgraph.org/.well-known/mathgraph-v3.json',
      v3_manifest_sha256: discoveryV3Sha256,
      v3_schema: 'https://mathgraph.org/schemas/discovery-v3.schema.json',
    });
    expect(discovery.integrity_notice).toMatch(/integrity.*not.*authenticity/i);
    expect(discovery.repository_provenance.authentication_status).toBe('UNSIGNED_PROVENANCE_ONLY');
    expect(discovery.repository_provenance.record_catalogue_source).toBe('https://github.com/metalogiclabs/mathgraph/blob/1a38f63f01b08f62854d289e4a64f8669b79e59f/website/src/data/record-index.json');

    const generatedAt = Date.parse(index.generated_at);
    expect(Number.isFinite(generatedAt)).toBe(true);
    expect(generatedAt).toBeLessThanOrEqual(Date.now());
    expect(index.lifecycle_freshness).toEqual({
      basis: 'CLIENT_FETCH_TIME',
      max_age_seconds: 300,
      meaning: 'generated_at is publication time; set fetched_at when received and re-fetch before max_age_seconds elapse.',
      records_are_immutable: true,
    });
    expect(index.records).toHaveLength(2);
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
      'https://mathgraph.org/.well-known/mathgraph-v3.json',
      'https://mathgraph.org/schemas/discovery-v4.schema.json',
      'https://mathgraph.org/catalogues/mathlib/v4.34.1/manifest.json',
      'https://mathgraph.org/catalogues/mathlib/v4.34.1/search.json',
      'https://mathgraph.org/artifacts/conformance/source_catalogue_v1/consumer.py',
      'https://mathgraph.org/artifacts/conformance/source_catalogue_v1/trust-policy.json',
      'https://mathgraph.org/artifacts/conformance/source_catalogue_v1/README.md',
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
      sourceCatalogueManifestSha256,
      sourceCatalogueSearchSha256,
      sourceCatalogueConsumerSha256,
      sourceCataloguePolicySha256,
      sourceCatalogueReadmeSha256,
      sourceCatalogueSnapshotCommit,
      sourceCataloguePublicationCommit,
      sourceCatalogueWrapperCommit,
      'SOURCE_INDEXED',
      'PINNED_HISTORICAL_SOURCE',
    ]) expect(llms).toContain(value);
    expect(llms).toMatch(/exact record ID, version, source pin, suite pin, and supported goal/i);
    expect(llms).toMatch(/mismatch.*UNKNOWN/i);
    expect(llms).toMatch(/digest.*integrity.*not.*authenticity/i);
    expect(llms).toMatch(/current applicability.*UNKNOWN/i);
    expect(llms).toMatch(/freshness.*NOT_CHECKED/i);
    expect(llms).toMatch(/public resolver.*NOT_DEPLOYED/i);
    expect(llms).toMatch(/MCP.*NOT_DEPLOYED/i);
    expect(llms).toMatch(/source catalogue[\s\S]*NOT_CHECKED/i);
    expect(llms).toMatch(/structural.*not.*implication.*equivalence/i);
    expect(llms).toMatch(/authority.*NONE/i);
    expect(Buffer.byteLength(llms)).toBeLessThan(12 * 1024);
    expect(llms).toContain('https://mathgraph.org/about/');
    expect(llms).toContain('https://mathgraph.org/contact/');
    expect(llms).toMatch(/resolve-consumer-v1\.ts.*text\/plain; charset=utf-8/i);
    expect(llms).toMatch(/browser.*presentation.*authority.*NONE/i);
    expect(llms).not.toContain('vercel.app');
  });

  test('keeps discovery V3 byte-identical and applies narrow public content/cache policies in both Vercel configs', async () => {
    const repository = join(website, '..');
    const [rootConfigBytes, websiteConfigBytes, discoveryBytes, sourceConsumer, builtConsumer] = await Promise.all([
      readFile(join(repository, 'vercel.json')),
      readFile(join(website, 'vercel.json')),
      readFile(join(website, 'public/.well-known/mathgraph-v3.json')),
      readFile(join(website, 'public/examples/resolve-consumer-v1.ts')),
      readFile(join(dist, 'examples/resolve-consumer-v1.ts')),
    ]);
    const rootConfig = JSON.parse(rootConfigBytes.toString('utf8'));
    const websiteConfig = JSON.parse(websiteConfigBytes.toString('utf8'));
    for (const key of ['cleanUrls', 'redirects', 'headers']) expect(rootConfig[key]).toEqual(websiteConfig[key]);
    const contentTypeRules = websiteConfig.headers.filter((rule: any) =>
      rule.headers?.some((header: any) => header.key.toLowerCase() === 'content-type'));
    expect(contentTypeRules).toEqual([
      {
        source: '/catalogues/(.*)',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
          { key: 'Content-Type', value: 'application/json; charset=utf-8' },
        ],
      },
      {
        source: '/examples/resolve-consumer-v1.ts',
        headers: [{ key: 'Content-Type', value: 'text/plain; charset=utf-8' }],
      },
      {
        source: '/artifacts/conformance/source_catalogue_v1/consumer.py',
        headers: [{ key: 'Content-Type', value: 'text/plain; charset=utf-8' }],
      },
      {
        source: '/artifacts/conformance/source_catalogue_v1/trust-policy.json',
        headers: [{ key: 'Content-Type', value: 'application/json; charset=utf-8' }],
      },
      {
        source: '/artifacts/conformance/source_catalogue_v1/README.md',
        headers: [{ key: 'Content-Type', value: 'text/markdown; charset=utf-8' }],
      },
    ]);
    const narrowRuleIndex = websiteConfig.headers.findIndex((rule: any) => rule.source === '/examples/resolve-consumer-v1.ts');
    const catchAllIndex = websiteConfig.headers.findIndex((rule: any) => rule.source === '/(.*)');
    expect(narrowRuleIndex).toBeGreaterThanOrEqual(0);
    expect(narrowRuleIndex).toBeLessThan(catchAllIndex);
    expect(websiteConfig.headers[catchAllIndex].headers).toContainEqual({ key: 'X-Content-Type-Options', value: 'nosniff' });
    expect(createHash('sha256').update(sourceConsumer).digest('hex')).toBe(typescriptConsumerSha256);
    expect(builtConsumer).toEqual(sourceConsumer);
    expect(createHash('sha256').update(discoveryBytes).digest('hex')).toBe(discoveryV3Sha256);
    const cacheHeaders = new Map(websiteConfig.headers.map((rule: any) => [
      rule.source,
      rule.headers?.find((header: any) => header.key.toLowerCase() === 'cache-control')?.value,
    ]));
    expect(cacheHeaders.get('/catalogues/(.*)')).toBe('public, max-age=31536000, immutable');
    expect(cacheHeaders.get('/.well-known/mathgraph.json')).toBe('public, max-age=0, s-maxage=300, stale-while-revalidate=60');
  });

  test('publishes only the three source-catalogue consumer artifacts with exact repository bytes', async () => {
    const allowed = [
      ['conformance/source_catalogue_v1/consumer.py', sourceCatalogueConsumerSha256],
      ['conformance/source_catalogue_v1/trust-policy.json', sourceCataloguePolicySha256],
      ['conformance/source_catalogue_v1/README.md', sourceCatalogueReadmeSha256],
    ] as const;
    for (const [path, digest] of allowed) {
      const [repositoryBytes, builtBytes] = await Promise.all([
        readFile(join(website, '..', path)),
        readFile(join(dist, 'artifacts', path)),
      ]);
      expect(createHash('sha256').update(repositoryBytes).digest('hex')).toBe(digest);
      expect(builtBytes).toEqual(repositoryBytes);
    }
    for (const path of [
      'conformance/source_catalogue_v1/run_isolated.py',
      'conformance/source_catalogue_v1/test_consumer.py',
      'pyproject.toml',
    ]) {
      await expect(readFile(join(dist, 'artifacts', path))).rejects.toThrow();
    }
  });

  test('advertises the Resolve transport schemas consistently without adding authentication', async () => {
    const [discovery, discoverySchema, llms, developers] = await Promise.all([
      json('.well-known/mathgraph.json'),
      json('schemas/discovery-v4.schema.json'),
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
