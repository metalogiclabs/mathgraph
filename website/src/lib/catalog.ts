import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve, sep } from 'node:path';

import Ajv, { type ValidateFunction } from 'ajv';

import catalogSource from '../data/record-index.json';
import discoverySchema from '../../public/schemas/discovery-v1.schema.json';
import leanProfileSchema from '../../public/schemas/lean-evidence-profile-draft-1.schema.json';
import presentationSchema from '../../public/schemas/presentation-metadata-v1.schema.json';
import publicRecordSchema from '../../public/schemas/public-consequence-record-v1.schema.json';
import recordIndexSchema from '../../public/schemas/record-index-v1.schema.json';
import { validateQualifiedRecord, type QualifiedRecord } from './evidence';
import { canonicalContentDigest, sha256Hex } from './integrity';

export type HistoricStatus = 'WARRANTED_BOUNDED' | 'UNKNOWN' | 'REJECTED';
export type LifecycleStatus = 'CURRENT' | 'SUPERSEDED' | 'REVOKED';

export interface ScopeContract {
  match: 'EXACT';
  source_commit: string;
  external_suite_commit: string;
  supported_goals: string[];
  mismatch_status: 'UNKNOWN';
}

export interface PublishedRecordEntry {
  id: string;
  version: number;
  version_slug: string;
  record_schema: string;
  historic_status: HistoricStatus;
  lifecycle: LifecycleStatus;
  snapshot_date: string;
  record_page_url: string;
  latest_page_url: string;
  record_json_url: string;
  record_content_sha256: string;
  record_transport_sha256: string;
  evidence_json_url: string;
  evidence_transport_sha256: string;
  presentation_json_url: string;
  presentation_schema: 'mathgraph.presentation-metadata.v1';
  presentation_content_sha256: string;
  scope: ScopeContract;
  unknowns: string[];
}

export interface RecordCatalog {
  $schema: 'https://mathgraph.org/schemas/record-index-v1.schema.json';
  schema: 'mathgraph.record-index.v1';
  latest_versions: Record<string, number>;
  records: PublishedRecordEntry[];
}

export interface PresentationMetadata {
  $schema: 'https://mathgraph.org/schemas/presentation-metadata-v1.schema.json';
  schema: 'mathgraph.presentation-metadata.v1';
  record_id: string;
  record_version: number;
  title: string;
  description: string;
  publisher: { name: string; url: 'https://mathgraph.org' };
  citation: { bibtex: string };
  classifications: string[];
  license: { status: 'DECLARED' | 'UNKNOWN'; spdx?: string; url?: string; note: string };
  external_registrations: { status: 'DECLARED' | 'UNKNOWN'; entries: Record<string, unknown>[] };
  metadata_updated_at: string;
  history: Array<{ updated_at: string; change: string; evidence_changed: false }>;
  content_sha256: string;
}

export interface PublishedRecordPackage {
  entry: PublishedRecordEntry;
  record: QualifiedRecord;
  presentation: PresentationMetadata;
}

export interface ScopeRequest {
  record_id: string;
  version: number;
  source_commit: string;
  external_suite_commit: string;
  goal: string;
}

export interface ScopeMatchResult {
  status: 'WARRANTED_BOUNDED' | 'UNKNOWN';
  reason:
    | 'EXACT_SCOPE_MATCH'
    | 'RECORD_ID_MISMATCH'
    | 'VERSION_MISMATCH'
    | 'SOURCE_PIN_MISMATCH'
    | 'SUITE_PIN_MISMATCH'
    | 'UNSUPPORTED_GOAL';
  truth_promotion: false;
}

interface PackageArtifacts {
  recordBytes: Uint8Array;
  evidenceBytes: Uint8Array;
  presentation: unknown;
}

const ajv = new Ajv({ allErrors: true, strict: true });
for (const schema of [recordIndexSchema, presentationSchema, publicRecordSchema, discoverySchema, leanProfileSchema]) {
  if (!ajv.validateSchema(schema)) {
    throw new Error('MATHGRAPH_PUBLIC_SCHEMA_INVALID');
  }
}
const validateIndex = ajv.compile(recordIndexSchema) as ValidateFunction<RecordCatalog>;
const validatePresentation = ajv.compile(presentationSchema) as ValidateFunction<PresentationMetadata>;
const validateRecord = ajv.compile(publicRecordSchema) as ValidateFunction<QualifiedRecord>;

const publicRoot = resolve(fileURLToPath(new URL('../../public/', import.meta.url)));
const forbiddenPresentationFields = new Set([
  'admission',
  'axes',
  'historic_status',
  'lifecycle',
  'record',
  'verification_status',
  'warrant',
  'warrant_status',
]);

function requireCatalog(condition: boolean, code: string): asserts condition {
  if (!condition) throw new Error(code);
}

function publicFile(urlValue: string): string {
  const url = new URL(urlValue);
  requireCatalog(url.origin === 'https://mathgraph.org', 'CATALOG_NON_CANONICAL_URL');
  const target = resolve(publicRoot, `.${decodeURIComponent(url.pathname)}`);
  requireCatalog(target.startsWith(`${publicRoot}${sep}`), 'CATALOG_PATH_ESCAPE');
  return target;
}

export function validateRecordCatalog(value: unknown): RecordCatalog {
  requireCatalog(validateIndex(value), 'RECORD_INDEX_SCHEMA_INVALID');
  const catalog = value as RecordCatalog;
  const versions = new Set<string>();
  for (const entry of catalog.records) {
    const key = `${entry.id}@${entry.version}`;
    requireCatalog(!versions.has(key), 'DUPLICATE_RECORD_VERSION');
    versions.add(key);
    requireCatalog(entry.version_slug === `v${entry.version}`, 'RECORD_VERSION_SLUG_MISMATCH');
  }
  for (const [id, version] of Object.entries(catalog.latest_versions)) {
    requireCatalog(versions.has(`${id}@${version}`), 'LATEST_RECORD_VERSION_MISSING');
  }
  return catalog;
}

export function validatePublicRecordSchema(value: unknown): QualifiedRecord {
  requireCatalog(validateRecord(value), 'PUBLIC_RECORD_SCHEMA_INVALID');
  return value as QualifiedRecord;
}

export function validatePresentationMetadata(value: unknown): PresentationMetadata {
  requireCatalog(value !== null && typeof value === 'object' && !Array.isArray(value), 'PRESENTATION_SCHEMA_INVALID');
  for (const key of Object.keys(value as Record<string, unknown>)) {
    requireCatalog(!forbiddenPresentationFields.has(key), 'PRESENTATION_AUTHORITY_FIELD_FORBIDDEN');
  }
  requireCatalog(validatePresentation(value), 'PRESENTATION_SCHEMA_INVALID');
  const presentation = value as PresentationMetadata;
  requireCatalog(
    presentation.content_sha256 === canonicalContentDigest(presentation as unknown as Record<string, unknown>),
    'PRESENTATION_CONTENT_HASH_INVALID',
  );
  return presentation;
}

export function validatePublishedRecordPackage(
  entry: PublishedRecordEntry,
  artifacts: PackageArtifacts,
): PublishedRecordPackage {
  requireCatalog(entry.record_schema === 'mathgraph.public-consequence-record.v1', 'UNSUPPORTED_RECORD_SCHEMA');
  requireCatalog(sha256Hex(artifacts.recordBytes) === entry.record_transport_sha256, 'CATALOG_RECORD_TRANSPORT_DIGEST_MISMATCH');
  const parsedRecord = JSON.parse(new TextDecoder().decode(artifacts.recordBytes)) as unknown;
  const schemaRecord = validatePublicRecordSchema(parsedRecord);
  requireCatalog(schemaRecord.content_sha256 === entry.record_content_sha256, 'CATALOG_RECORD_DIGEST_MISMATCH');
  const record = validateQualifiedRecord(schemaRecord);
  requireCatalog(sha256Hex(artifacts.evidenceBytes) === entry.evidence_transport_sha256, 'CATALOG_EVIDENCE_DIGEST_MISMATCH');
  const presentation = validatePresentationMetadata(artifacts.presentation);
  requireCatalog(presentation.content_sha256 === entry.presentation_content_sha256, 'PRESENTATION_DIGEST_MISMATCH');
  requireCatalog(presentation.record_id === entry.id && presentation.record_version === entry.version, 'PRESENTATION_RECORD_IDENTITY_MISMATCH');
  requireCatalog(record.id === entry.id && record.schema === entry.record_schema, 'CATALOG_RECORD_IDENTITY_MISMATCH');
  requireCatalog(record.source.commit === entry.scope.source_commit, 'CATALOG_SCOPE_SOURCE_MISMATCH');
  requireCatalog(record.source.external_suite_commit === entry.scope.external_suite_commit, 'CATALOG_SCOPE_SUITE_MISMATCH');
  return { entry, record, presentation };
}

export function matchRecordScope(entry: PublishedRecordEntry, request: ScopeRequest): ScopeMatchResult {
  const unknown = (reason: ScopeMatchResult['reason']): ScopeMatchResult => ({
    status: 'UNKNOWN',
    reason,
    truth_promotion: false,
  });
  if (request.record_id !== entry.id) return unknown('RECORD_ID_MISMATCH');
  if (request.version !== entry.version) return unknown('VERSION_MISMATCH');
  if (request.source_commit !== entry.scope.source_commit) return unknown('SOURCE_PIN_MISMATCH');
  if (request.external_suite_commit !== entry.scope.external_suite_commit) return unknown('SUITE_PIN_MISMATCH');
  if (!entry.scope.supported_goals.includes(request.goal)) return unknown('UNSUPPORTED_GOAL');
  return { status: 'WARRANTED_BOUNDED', reason: 'EXACT_SCOPE_MATCH', truth_promotion: false };
}

export async function loadPublishedRecords(): Promise<PublishedRecordPackage[]> {
  const catalog = validateRecordCatalog(catalogSource);
  return Promise.all(
    catalog.records.map(async (entry) => {
      const [recordBytes, evidenceBytes, presentationBytes] = await Promise.all([
        readFile(publicFile(entry.record_json_url)),
        readFile(publicFile(entry.evidence_json_url)),
        readFile(publicFile(entry.presentation_json_url)),
      ]);
      return validatePublishedRecordPackage(entry, {
        recordBytes,
        evidenceBytes,
        presentation: JSON.parse(presentationBytes.toString('utf8')),
      });
    }),
  );
}

export async function getPublishedRecord(id: string, version?: number): Promise<PublishedRecordPackage> {
  const records = await loadPublishedRecords();
  const record = records.find((candidate) => candidate.entry.id === id && (version === undefined || candidate.entry.version === version));
  requireCatalog(record !== undefined, 'PUBLISHED_RECORD_NOT_FOUND');
  return record;
}

export async function getLatestPublishedRecord(id: string): Promise<PublishedRecordPackage> {
  const catalog = validateRecordCatalog(catalogSource);
  const version = catalog.latest_versions[id];
  requireCatalog(typeof version === 'number', 'PUBLISHED_RECORD_NOT_FOUND');
  return getPublishedRecord(id, version);
}
