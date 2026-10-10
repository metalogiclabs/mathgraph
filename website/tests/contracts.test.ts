import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import Ajv from 'ajv';
import { describe, expect, test } from 'vitest';

const website = join(dirname(fileURLToPath(import.meta.url)), '..');
const dist = join(website, 'dist');
const recordId = 'mg-l4yaml-source-check-20261010';
const resolveRecordId = 'mg-living-warrant-openai-jpl-20261010';
const resolveSnapshotSha256 = 'b95297a081d513fb0ec145a776cc997eaed18109d6b2af39fa8e61f6d637af41';
const resolveScenariosSha256 = 'ed458ccbee85e3aa3f49d9d38e7ad5380515d00d707bac09c584cc4955b88181';

async function text(path: string): Promise<string> {
  return readFile(join(dist, path), 'utf8');
}

async function json(path: string): Promise<Record<string, any>> {
  return JSON.parse(await text(path)) as Record<string, any>;
}

describe('agent discovery contracts', () => {
  test('publishes schema-valid discovery and record index documents', async () => {
    const ajv = new Ajv({ allErrors: true, strict: true });
    const [discovery, index, record, discoverySchema, indexSchema] = await Promise.all([
      json('.well-known/mathgraph.json'),
      json('records/index.json'),
      json(`evidence/${recordId}/record.json`),
      json('schemas/discovery-v1.schema.json'),
      json('schemas/record-index-v2.schema.json'),
    ]);

    expect(ajv.validate(discoverySchema, discovery), ajv.errorsText()).toBe(true);
    expect(ajv.validate(indexSchema, index), ajv.errorsText()).toBe(true);
    expect(discovery.canonical_origin).toBe('https://mathgraph.org');
    expect(JSON.stringify(discovery)).not.toContain('vercel.app');
    expect(discovery.capabilities).toEqual({
      static_records: 'IMPLEMENTED',
      public_resolver: 'NOT_DEPLOYED',
      lean_profile: 'PROPOSED',
      mcp: 'PROPOSED',
    });
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
    ]) {
      expect(llms).toContain(url);
    }
    expect(llms).toMatch(/exact record ID, version, source pin, suite pin, and supported goal/i);
    expect(llms).toMatch(/mismatch.*UNKNOWN/i);
    expect(llms).toMatch(/digest.*integrity.*not.*authenticity/i);
    expect(llms).not.toContain('vercel.app');
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
