import { readFile } from 'node:fs/promises';

import { describe, expect, test } from 'vitest';

import catalogSource from '../data/record-index.json';
import frozenRecord from '../data/l4yaml-record.json';
import {
  getLatestPublishedRecord,
  loadPublishedRecords,
  matchRecordScope,
  validatePresentationMetadata,
  validatePublicRecordSchema,
  validatePublishedRecordPackage,
  validateRecordCatalog,
  type PresentationMetadata,
  type PublishedRecordEntry,
} from './catalog';

const RECORD_ID = 'mg-l4yaml-source-check-20261010';
const CONTENT_DIGEST = 'f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb';
const SOURCE_COMMIT = '62bf7077910e888a0bc8adfc8e08a5f500ff3ca3';
const SUITE_COMMIT = 'da267a5c4782e7361e82889e76c0dc7df0e1e870';

function clone<T>(value: T): T {
  return structuredClone(value);
}

async function packageFixture() {
  const catalog = validateRecordCatalog(catalogSource);
  const entry = catalog.records[0];
  const recordBytes = await readFile(new URL(`../../public/evidence/${RECORD_ID}/record.json`, import.meta.url));
  const evidenceBytes = await readFile(new URL(`../../public/evidence/${RECORD_ID}/evidence.json`, import.meta.url));
  const presentationBytes = await readFile(new URL(`../../public/records/${RECORD_ID}/v1/metadata.json`, import.meta.url));
  const presentation = JSON.parse(presentationBytes.toString('utf8')) as unknown;
  return { entry, recordBytes, evidenceBytes, presentation, presentationBytes };
}

describe('published record catalogue', () => {
  test('loads the exact qualified package', async () => {
    const records = await loadPublishedRecords();
    const latest = await getLatestPublishedRecord(RECORD_ID);

    expect(records).toHaveLength(1);
    expect(latest.entry.id).toBe(RECORD_ID);
    expect(latest.entry.version).toBe(1);
    expect(latest.entry.version_slug).toBe('v1');
    expect(latest.entry.historic_status).toBe('WARRANTED_BOUNDED');
    expect(latest.entry.lifecycle).toBe('CURRENT');
    expect(latest.record.content_sha256).toBe(CONTENT_DIGEST);
    expect(latest.record.source.commit).toBe(SOURCE_COMMIT);
    expect(latest.record.source.external_suite_commit).toBe(SUITE_COMMIT);
    expect(latest.record.axes.formal_verification.universal_yaml_correctness).toBe('UNKNOWN');
    expect(latest.record.axes.statement_fidelity.status).toBe('UNKNOWN');
    expect(latest.record.axes.generalization.status).toBe('UNKNOWN');
    expect(latest.presentation.metadata_updated_at).toMatch(/^2026-10-10T/);
    expect(latest.presentation.history).toEqual([
      expect.objectContaining({ evidence_changed: false }),
    ]);
  });

  test('matches only the exact structured scope', async () => {
    const { entry } = await packageFixture();
    const request = {
      record_id: RECORD_ID,
      version: 1,
      source_commit: SOURCE_COMMIT,
      external_suite_commit: SUITE_COMMIT,
      goal: 'finite_parser_acceptance',
    };

    expect(matchRecordScope(entry, request)).toEqual({
      status: 'WARRANTED_BOUNDED',
      reason: 'EXACT_SCOPE_MATCH',
      truth_promotion: false,
    });
    expect(matchRecordScope(entry, { ...request, source_commit: '0'.repeat(40) })).toEqual({
      status: 'UNKNOWN',
      reason: 'SOURCE_PIN_MISMATCH',
      truth_promotion: false,
    });
    expect(matchRecordScope(entry, { ...request, goal: 'whole_language_correctness' })).toEqual({
      status: 'UNKNOWN',
      reason: 'UNSUPPORTED_GOAL',
      truth_promotion: false,
    });
    expect(matchRecordScope(entry, { ...request, version: 2 })).toEqual({
      status: 'UNKNOWN',
      reason: 'VERSION_MISMATCH',
      truth_promotion: false,
    });
  });

  test('validates the qualified record against its public schema', () => {
    expect(validatePublicRecordSchema(frozenRecord)).toEqual(frozenRecord);
    expect(() => validatePublicRecordSchema({ ...frozenRecord, id: 42 })).toThrow('PUBLIC_RECORD_SCHEMA_INVALID');
  });

  test('rejects a forged immutable digest', async () => {
    const fixture = await packageFixture();
    const entry = clone(fixture.entry) as PublishedRecordEntry;
    entry.record_content_sha256 = '0'.repeat(64);

    expect(() => validatePublishedRecordPackage(entry, fixture)).toThrow('CATALOG_RECORD_DIGEST_MISMATCH');
  });

  test('rejects a changed presentation digest', async () => {
    const fixture = await packageFixture();
    const entry = clone(fixture.entry) as PublishedRecordEntry;
    entry.presentation_content_sha256 = '0'.repeat(64);

    expect(() => validatePublishedRecordPackage(entry, fixture)).toThrow('PRESENTATION_DIGEST_MISMATCH');
  });

  test('rejects presentation authority fields', async () => {
    const fixture = await packageFixture();
    const presentation = clone(fixture.presentation) as PresentationMetadata & { warrant_status: string };
    presentation.warrant_status = 'WARRANTED';

    expect(() => validatePresentationMetadata(presentation)).toThrow('PRESENTATION_AUTHORITY_FIELD_FORBIDDEN');
  });

  test('rejects duplicate id and version', () => {
    const catalog = clone(catalogSource);
    catalog.records.push(clone(catalog.records[0]));

    expect(() => validateRecordCatalog(catalog)).toThrow('DUPLICATE_RECORD_VERSION');
  });

  test('rejects a missing latest version', () => {
    const catalog = clone(catalogSource);
    catalog.latest_versions[RECORD_ID] = 2;

    expect(() => validateRecordCatalog(catalog)).toThrow('LATEST_RECORD_VERSION_MISSING');
  });

  test('rejects unsupported record schemas', async () => {
    const fixture = await packageFixture();
    const entry = clone(fixture.entry) as PublishedRecordEntry;
    entry.record_schema = 'mathgraph.unqualified-future-record.v99';

    expect(() => validatePublishedRecordPackage(entry, fixture)).toThrow('UNSUPPORTED_RECORD_SCHEMA');
  });
});
