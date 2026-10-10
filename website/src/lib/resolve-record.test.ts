import { readFile } from 'node:fs/promises';
import { describe, expect, test } from 'vitest';
import catalogSource from '../data/record-index.json';
import { getLatestPublishedRecord, getPublishedRecord, loadPublishedRecords, matchRecordScope, validateRecordCatalog, validatePublishedRecordPackage, validatePresentationMetadata } from './catalog';
import { canonicalContentDigest, canonicalJson, sha256Hex } from './integrity';
import { validateResolveAgreement } from './resolve-record';

const ID = 'mg-living-warrant-openai-jpl-20261010';
const CONTENT = 'b95297a081d513fb0ec145a776cc997eaed18109d6b2af39fa8e61f6d637af41';
async function fixture() {
  const entry = structuredClone(validateRecordCatalog(catalogSource).records.find(entry => entry.id === ID));
  expect(entry, 'record 002 must be registered').toBeDefined();
  const recordBytes = await readFile(new URL(`../../public/evidence/${ID}/record.json`, import.meta.url));
  const scenariosBytes = await readFile(new URL(`../../public/evidence/${ID}/scenarios.json`, import.meta.url));
  const presentation = JSON.parse(await readFile(new URL(`../../public/records/${ID}/v1/metadata.json`, import.meta.url), 'utf8'));
  return { entry: entry!, recordBytes, scenariosBytes, presentation };
}

describe('record 002 immutable admission', () => {
  test('loads two discriminated packages without promoting mixed historic outcomes', async () => {
    const packages = await loadPublishedRecords();
    expect(packages).toHaveLength(2);
    const result = packages.find(item => item.entry.id === ID)!;
    expect(result.entry).toMatchObject({ record_kind: 'RESOLUTION_SNAPSHOT', historical_epistemic_result: 'SCOPED_MIXED', lifecycle: 'CURRENT', research_maturity: 'BOUNDED_QUALIFIED', action_policy: 'READ_ONLY_NO_AUTOMATIC_AUTHORIZATION', current_applicability: 'UNKNOWN', freshness: 'NOT_CHECKED' });
    expect(result.entry).not.toHaveProperty('historic_status');
    expect(result.record).toMatchObject({ id: ID, snapshot_sha256: CONTENT });
    expect(await getLatestPublishedRecord(ID)).toEqual(await getPublishedRecord(ID, 1));
    await expect(getPublishedRecord(ID, 2)).rejects.toThrow('PUBLISHED_RECORD_NOT_FOUND');
    expect(matchRecordScope(result.entry, { record_id: ID, version: 1, source_commit: '', external_suite_commit: '', goal: 'finite_parser_acceptance' })).toEqual({ status: 'UNKNOWN', reason: 'UNSUPPORTED_RECORD_KIND', truth_promotion: false });
  });
  test('checks exact identity and canonical payload independently', async () => {
    const f = await fixture();
    expect(f.recordBytes.length).toBe(5290);
    expect(sha256Hex(f.recordBytes)).toBe('0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87');
    expect(canonicalContentDigest(JSON.parse(f.recordBytes.toString()), 'snapshot_sha256')).toBe(CONTENT);
    expect(sha256Hex(f.scenariosBytes)).toBe('ed458ccbee85e3aa3f49d9d38e7ad5380515d00d707bac09c584cc4955b88181');
    expect(() => validatePublishedRecordPackage(f.entry, f)).not.toThrow();
  });
  test('rejects changed bytes and a same-length internally rehashed status replacement even with forged catalogue pins', async () => {
    const f = await fixture();
    expect(() => validatePublishedRecordPackage(f.entry, { ...f, recordBytes: Buffer.concat([f.recordBytes, Buffer.from(' ')]) })).toThrow();
    const changed = JSON.parse(f.recordBytes.toString());
    changed.resolutions['openai.theorem.1'].after = 'REFUTED';
    changed.snapshot_sha256 = canonicalContentDigest(changed, 'snapshot_sha256');
    const forged = Buffer.from(canonicalJson(changed) + '\n');
    expect(forged.length).toBe(f.recordBytes.length);
    expect(() => validatePublishedRecordPackage({ ...f.entry, record_transport_sha256: sha256Hex(forged), record_content_sha256: changed.snapshot_sha256 }, { ...f, recordBytes: forged })).toThrow();
  });
  test('rejects changed scenarios with a forged catalogue digest', async () => {
    const f = await fixture();
    const value = JSON.parse(f.scenariosBytes.toString());
    value.PUBLISHED_RECORD.scenarios[1].resolutions['openai.theorem.1'].after = 'REFUTED';
    const scenariosBytes = Buffer.from(canonicalJson(value) + '\n');
    expect(() => validatePublishedRecordPackage({ ...f.entry, scenarios_transport_sha256: sha256Hex(scenariosBytes) } as typeof f.entry, { ...f, scenariosBytes })).toThrow();
  });
  test.each(['record_transport_sha256', 'record_content_sha256', 'scenarios_transport_sha256'])('rejects forged catalogue %s', async key => {
    const f = await fixture();
    expect(() => validatePublishedRecordPackage({ ...f.entry, [key]: '0'.repeat(64) }, f)).toThrow();
  });
  test.each([{ record_kind: 'FUTURE' }, { record_schema: 'mathgraph.living-warrant-snapshot.v2' }, { version: 2, version_slug: 'v2' }, { record_kind: 'SOURCE_CHECK' }, { extension: true }])('fails closed on unsupported entry %j', async mutation => {
    const f = await fixture();
    expect(() => validatePublishedRecordPackage({ ...f.entry, ...mutation } as typeof f.entry, f)).toThrow();
    const catalog = structuredClone(catalogSource);
    Object.assign(catalog.records.find(entry => entry.id === ID)!, mutation);
    expect(() => validateRecordCatalog(catalog)).toThrow();
  });
  test.each(['lifecycle', 'warrant', 'admission', 'status', 'authority', 'research_maturity', 'action_policy'])('rejects presentation authority field %s', async key => {
    const f = await fixture();
    const value = { ...f.presentation, [key]: 'CURRENT' };
    value.content_sha256 = canonicalContentDigest(value);
    expect(() => validatePresentationMetadata(value)).toThrow();
  });
  test('preserves non-authoritative metadata and visibly records no evidence change', async () => {
    const f = await fixture();
    expect(f.presentation.title).toBe('MathGraph Resolve — When Mathematical Evidence Changes');
    expect(f.presentation.license.status).toBe('UNKNOWN');
    expect(f.presentation.external_registrations).toEqual({ status: 'UNKNOWN', entries: [] });
    expect(f.presentation.history[0]).toMatchObject({ evidence_changed: false });
    expect(f.presentation.history[0].change).toMatch(/presentation.*without.*evidence/i);
  });
  test('rejects nested presentation authority even in registration entries', async () => {
    const f = await fixture();
    f.presentation.external_registrations.entries = [{ authority: 'AUTHORIZED' }];
    f.presentation.content_sha256 = canonicalContentDigest(f.presentation);
    expect(() => validatePresentationMetadata(f.presentation)).toThrow();
  });
  test('rejects catalogue routes that no longer identify the immutable record', async () => {
    const f = await fixture();
    expect(() => validatePublishedRecordPackage({ ...f.entry, record_page_url: 'https://mathgraph.org/records/unqualified/v9/' }, f)).toThrow();
  });
  test('rejects an unsupported Source Check version without changing its qualification rules', async () => {
    const packages = await loadPublishedRecords();
    const source = packages.find(item => item.record_kind === 'SOURCE_CHECK')!;
    const recordBytes = await readFile(new URL('../../public/evidence/mg-l4yaml-source-check-20261010/record.json', import.meta.url));
    const evidenceBytes = await readFile(new URL('../../public/evidence/mg-l4yaml-source-check-20261010/evidence.json', import.meta.url));
    const presentation = structuredClone(source.presentation);
    presentation.record_version = 2;
    presentation.content_sha256 = canonicalContentDigest(presentation as unknown as Record<string, unknown>);
    expect(() => validatePublishedRecordPackage({ ...source.entry, version: 2, version_slug: 'v2', presentation_content_sha256: presentation.content_sha256 }, { recordBytes, evidenceBytes, presentation })).toThrow();
  });
  test('directly checks scenario agreement behind the transport gate', async () => {
    const f = await fixture();
    const record = JSON.parse(f.recordBytes.toString());
    const scenarios = JSON.parse(f.scenariosBytes.toString());
    expect(() => validateResolveAgreement(record, scenarios)).not.toThrow();
    scenarios.PUBLISHED_RECORD.scenarios[1].resolutions['openai.original_support.1'].after = 'UNKNOWN';
    expect(() => validateResolveAgreement(record, scenarios)).toThrow('RESOLVE_PUBLISHED_SCENARIO_DISAGREEMENT');
  });
  test('retains the immutable v1 catalogue schema and rejects unknown index versions', async () => {
    const bytes = await readFile(new URL('../../public/schemas/record-index-v1.schema.json', import.meta.url));
    expect(sha256Hex(bytes)).toBe('699095f0cebc548565a86dd89c7f5a0854ad7982ed8d6be2cc1c299d7a8381cc');
    expect(() => validateRecordCatalog({ ...catalogSource, schema: 'mathgraph.record-index.v99' })).toThrow('RECORD_INDEX_SCHEMA_INVALID');
    expect(() => validateRecordCatalog({ ...catalogSource, extension: {} })).toThrow('RECORD_INDEX_SCHEMA_INVALID');
    const unknownSourceVersion = structuredClone(catalogSource);
    unknownSourceVersion.records[0].version = 2;
    unknownSourceVersion.records[0].version_slug = 'v2';
    unknownSourceVersion.latest_versions['mg-l4yaml-source-check-20261010'] = 2;
    expect(() => validateRecordCatalog(unknownSourceVersion)).toThrow('RECORD_INDEX_SCHEMA_INVALID');
  });
  test('rejects duplicate JSON keys at the byte gate even when JSON.parse would discard them', async () => {
    const f = await fixture();
    const recordBytes = Buffer.from(f.recordBytes.toString().replace('{', '{"schema":"discarded",'));
    expect(JSON.parse(recordBytes.toString()).schema).toBe('mathgraph.living-warrant-snapshot.v1');
    expect(() => validatePublishedRecordPackage({ ...f.entry, record_transport_sha256: sha256Hex(recordBytes) }, { ...f, recordBytes })).toThrow('RESOLVE_RECORD_TRANSPORT_NOT_AUTHORIZED');
  });
  test('directly rejects rehashed historical outcomes and bad canonical digests', async () => {
    const f = await fixture();
    const record = JSON.parse(f.recordBytes.toString());
    const scenarios = JSON.parse(f.scenariosBytes.toString());
    record.resolutions['openai.original_support.1'].after = 'UNKNOWN';
    expect(() => validateResolveAgreement(record, scenarios)).toThrow('RESOLVE_CANONICAL_DIGEST_INVALID');
    record.snapshot_sha256 = canonicalContentDigest(record, 'snapshot_sha256');
    scenarios.snapshot_sha256 = record.snapshot_sha256;
    expect(() => validateResolveAgreement(record, scenarios)).toThrow('RESOLVE_HISTORICAL_OUTCOME_MISMATCH');
  });
  test.each(['recordExtension', 'claimExtension', 'scenarioExtension', 'schema', 'sourcePin', 'consumerOwnership', 'leanRerun', 'historicalSyntheticMix'])('rejects semantic/schema mutation %s without relying on transport', async mutation => {
    const f = await fixture();
    const record = JSON.parse(f.recordBytes.toString());
    const scenarios = JSON.parse(f.scenariosBytes.toString());
    if (mutation === 'recordExtension') record.extensions = {};
    if (mutation === 'claimExtension') record.derivation.claims[0].extension = true;
    if (mutation === 'scenarioExtension') scenarios.PUBLISHED_RECORD.scenarios[0].extension = true;
    if (mutation === 'schema') scenarios.schema = 'mathgraph.resolve-scenarios.v2';
    if (mutation === 'sourcePin') record.sources.openai.commit = '0'.repeat(40);
    if (mutation === 'consumerOwnership') scenarios.provenance.consumer.same_owner = false;
    if (mutation === 'leanRerun') scenarios.provenance.consumer.reruns_jpl_lean_proof = true;
    if (mutation === 'historicalSyntheticMix') scenarios.SYNTHETIC_CONFORMANCE.scenarios[0].graph.claims[0].scope = 'openai/math';
    record.snapshot_sha256 = canonicalContentDigest(record, 'snapshot_sha256');
    scenarios.snapshot_sha256 = record.snapshot_sha256;
    expect(() => validateResolveAgreement(record, scenarios)).toThrow();
  });
});
