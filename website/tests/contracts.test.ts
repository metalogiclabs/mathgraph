import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import Ajv from 'ajv';
import { describe, expect, test } from 'vitest';

const website = join(dirname(fileURLToPath(import.meta.url)), '..');
const dist = join(website, 'dist');
const recordId = 'mg-l4yaml-source-check-20261010';

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
      json('schemas/record-index-v1.schema.json'),
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
    expect(discovery.repository_provenance.catalogue_source).toContain('0992408c4c545536173709fc4781670f11efda96');

    expect(index.generated_at).toMatch(/^2026-10-10T/);
    expect(index.lifecycle_freshness).toEqual({
      max_age_seconds: 300,
      meaning: 'Lifecycle state is current only as of the fetched index response.',
      records_are_immutable: true,
    });
    expect(index.records).toHaveLength(1);
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
      '/protocol/profiles/lean/',
      `/records/${recordId}/`,
      `/records/${recordId}/v1/`,
    ]) {
      expect(sitemap).toContain(`<loc>https://mathgraph.org${route}</loc>`);
    }
  });
});
