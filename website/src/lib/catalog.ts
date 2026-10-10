import { readFile } from 'node:fs/promises';
import { resolve, sep } from 'node:path';

import Ajv, { type ValidateFunction } from 'ajv';

import catalogSource from '../data/record-index.json';
import discoverySchema from '../../public/schemas/discovery-v1.schema.json';
import leanProfileSchema from '../../public/schemas/lean-evidence-profile-draft-1.schema.json';
import presentationSchema from '../../public/schemas/presentation-metadata-v1.schema.json';
import publicRecordSchema from '../../public/schemas/public-consequence-record-v1.schema.json';
import recordIndexSchema from '../../public/schemas/record-index-v2.schema.json';
import { validateQualifiedRecord, type QualifiedRecord } from './evidence';
import { canonicalContentDigest, sha256Hex } from './integrity';
import { validateResolveArtifacts, type ResolveSnapshot, type ResolveScenarios } from './resolve-record';

export type HistoricStatus = 'WARRANTED_BOUNDED' | 'UNKNOWN' | 'REJECTED';
export type LifecycleStatus = 'CURRENT' | 'SUPERSEDED' | 'REVOKED';

export interface ScopeContract {
  match: 'EXACT';
  source_commit: string;
  external_suite_commit: string;
  supported_goals: string[];
  mismatch_status: 'UNKNOWN';
}

interface CommonRecordEntry {
  id: string;
  version: number;
  version_slug: string;
  record_schema: string;
  lifecycle: LifecycleStatus;
  snapshot_date: string;
  record_page_url: string;
  latest_page_url: string;
  record_json_url: string;
  record_content_sha256: string;
  record_transport_sha256: string;
  presentation_json_url: string;
  presentation_schema: 'mathgraph.presentation-metadata.v1';
  presentation_content_sha256: string;
  unknowns: string[];
}

export interface SourceCheckEntry extends CommonRecordEntry {
  record_kind: 'SOURCE_CHECK';
  historic_status: HistoricStatus;
  evidence_json_url: string;
  evidence_transport_sha256: string;
  scope: ScopeContract;
}

export interface ResolutionSnapshotEntry extends CommonRecordEntry {
  record_kind: 'RESOLUTION_SNAPSHOT';
  historical_epistemic_result: 'SCOPED_MIXED';
  research_maturity: 'BOUNDED_QUALIFIED';
  action_policy: 'READ_ONLY_NO_AUTOMATIC_AUTHORIZATION';
  current_applicability: 'UNKNOWN';
  freshness: 'NOT_CHECKED';
  scenarios_schema: 'mathgraph.resolve-scenarios.v1';
  scenarios_json_url: string;
  scenarios_transport_sha256: string;
  independent_replay_ci_run: '38086245988';
}

export type PublishedRecordEntry = SourceCheckEntry | ResolutionSnapshotEntry;

export interface RecordCatalog {
  $schema: 'https://mathgraph.org/schemas/record-index-v2.schema.json';
  schema: 'mathgraph.record-index.v2';
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

export interface SourceCheckPackage {
  record_kind: 'SOURCE_CHECK';
  entry: SourceCheckEntry;
  record: QualifiedRecord;
  presentation: PresentationMetadata;
}

export interface ResolutionSnapshotPackage {
  record_kind: 'RESOLUTION_SNAPSHOT';
  entry: ResolutionSnapshotEntry;
  record: ResolveSnapshot;
  scenarios: ResolveScenarios;
  presentation: PresentationMetadata;
}

export type PublishedRecordPackage = SourceCheckPackage | ResolutionSnapshotPackage;

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
    | 'UNSUPPORTED_GOAL'
    | 'LIFECYCLE_NOT_CURRENT'
    | 'HISTORIC_STATUS_NOT_WARRANTED'
    | 'UNSUPPORTED_RECORD_KIND';
  truth_promotion: false;
}

interface PackageArtifacts {
  recordBytes: Uint8Array;
  evidenceBytes?: Uint8Array;
  scenariosBytes?: Uint8Array;
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

const publicRoot = resolve(process.cwd(), 'public');
const forbiddenPresentationFields = new Set([
  'admission',
  'axes',
  'historic_status',
  'lifecycle',
  'record',
  'verification_status',
  'warrant',
  'warrant_status',
  'status',
  'authority',
  'research_maturity',
  'action_policy',
  'historical_epistemic_result',
  'current_applicability',
  'freshness',
]);

const qualifiedPublicConsequenceAuthority = {
  historicStatus: 'WARRANTED_BOUNDED' as const,
  supportedGoals: ['finite_parser_acceptance'] as const,
};

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
    requireCatalog(Object.hasOwn(catalog.latest_versions, entry.id), 'LATEST_RECORD_MAPPING_MISSING');
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
  const inspectFields = (child: unknown, path = ''): void => {
    if (child === null || typeof child !== 'object') return;
    for (const [key, nested] of Object.entries(child)) {
      const metadataStatus = key === 'status' && (path === 'license' || path === 'external_registrations');
      requireCatalog(metadataStatus || !forbiddenPresentationFields.has(key), 'PRESENTATION_AUTHORITY_FIELD_FORBIDDEN');
      inspectFields(nested, path ? `${path}.${key}` : key);
    }
  };
  inspectFields(value);
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
  requireCatalog(entry.record_kind === 'SOURCE_CHECK' || entry.record_kind === 'RESOLUTION_SNAPSHOT', 'UNSUPPORTED_RECORD_KIND');
  if (entry.record_kind === 'RESOLUTION_SNAPSHOT') {
    validateRecordCatalog({ $schema: recordIndexSchema.$id, schema: 'mathgraph.record-index.v2', latest_versions: { [entry.id]: entry.version }, records: [entry] });
    const origin = 'https://mathgraph.org';
    requireCatalog(
      entry.record_page_url === `${origin}/records/${entry.id}/v1/` &&
      entry.latest_page_url === `${origin}/records/${entry.id}/` &&
      entry.record_json_url === `${origin}/evidence/${entry.id}/record.json` &&
      entry.scenarios_json_url === `${origin}/evidence/${entry.id}/scenarios.json` &&
      entry.presentation_json_url === `${origin}/records/${entry.id}/v1/metadata.json`,
      'RESOLVE_CATALOG_URL_IDENTITY_MISMATCH',
    );
    const { record, scenarios } = validateResolveArtifacts(entry, artifacts);
    const presentation = validatePresentationMetadata(artifacts.presentation);
    requireCatalog(presentation.content_sha256 === entry.presentation_content_sha256, 'PRESENTATION_DIGEST_MISMATCH');
    requireCatalog(presentation.record_id === entry.id && presentation.record_version === entry.version, 'PRESENTATION_RECORD_IDENTITY_MISMATCH');
    return { record_kind: 'RESOLUTION_SNAPSHOT', entry, record, scenarios, presentation };
  }
  requireCatalog(entry.record_schema === 'mathgraph.public-consequence-record.v1', 'UNSUPPORTED_RECORD_SCHEMA');
  requireCatalog(entry.version === 1, 'UNSUPPORTED_RECORD_VERSION');
  requireCatalog(sha256Hex(artifacts.recordBytes) === entry.record_transport_sha256, 'CATALOG_RECORD_TRANSPORT_DIGEST_MISMATCH');
  const parsedRecord = JSON.parse(new TextDecoder().decode(artifacts.recordBytes)) as unknown;
  const schemaRecord = validatePublicRecordSchema(parsedRecord);
  requireCatalog(schemaRecord.content_sha256 === entry.record_content_sha256, 'CATALOG_RECORD_DIGEST_MISMATCH');
  const record = validateQualifiedRecord(schemaRecord);
  requireCatalog(artifacts.evidenceBytes !== undefined && sha256Hex(artifacts.evidenceBytes) === entry.evidence_transport_sha256, 'CATALOG_EVIDENCE_DIGEST_MISMATCH');
  const presentation = validatePresentationMetadata(artifacts.presentation);
  requireCatalog(presentation.content_sha256 === entry.presentation_content_sha256, 'PRESENTATION_DIGEST_MISMATCH');
  requireCatalog(presentation.record_id === entry.id && presentation.record_version === entry.version, 'PRESENTATION_RECORD_IDENTITY_MISMATCH');
  requireCatalog(record.id === entry.id && record.schema === entry.record_schema, 'CATALOG_RECORD_IDENTITY_MISMATCH');
  requireCatalog(record.source.commit === entry.scope.source_commit, 'CATALOG_SCOPE_SOURCE_MISMATCH');
  requireCatalog(record.source.external_suite_commit === entry.scope.external_suite_commit, 'CATALOG_SCOPE_SUITE_MISMATCH');
  requireCatalog(
    entry.historic_status === qualifiedPublicConsequenceAuthority.historicStatus,
    'CATALOG_HISTORIC_STATUS_MISMATCH',
  );
  requireCatalog(
    entry.scope.supported_goals.length === qualifiedPublicConsequenceAuthority.supportedGoals.length &&
      qualifiedPublicConsequenceAuthority.supportedGoals.every((goal) => entry.scope.supported_goals.includes(goal)),
    'CATALOG_UNQUALIFIED_SUPPORTED_GOAL',
  );
  validateRecordCatalog({ $schema: recordIndexSchema.$id, schema: 'mathgraph.record-index.v2', latest_versions: { [entry.id]: entry.version }, records: [entry] });
  return { record_kind: 'SOURCE_CHECK', entry, record, presentation };
}

export function matchRecordScope(entry: PublishedRecordEntry, request: ScopeRequest): ScopeMatchResult {
  const unknown = (reason: ScopeMatchResult['reason']): ScopeMatchResult => ({
    status: 'UNKNOWN',
    reason,
    truth_promotion: false,
  });
  if (entry.record_kind !== 'SOURCE_CHECK') return unknown('UNSUPPORTED_RECORD_KIND');
  if (request.record_id !== entry.id) return unknown('RECORD_ID_MISMATCH');
  if (request.version !== entry.version) return unknown('VERSION_MISMATCH');
  if (entry.lifecycle !== 'CURRENT') return unknown('LIFECYCLE_NOT_CURRENT');
  if (entry.historic_status !== 'WARRANTED_BOUNDED') return unknown('HISTORIC_STATUS_NOT_WARRANTED');
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
        readFile(publicFile(entry.record_kind === 'SOURCE_CHECK' ? entry.evidence_json_url : entry.scenarios_json_url)),
        readFile(publicFile(entry.presentation_json_url)),
      ]);
      return validatePublishedRecordPackage(entry, {
        recordBytes,
        ...(entry.record_kind === 'SOURCE_CHECK' ? { evidenceBytes } : { scenariosBytes: evidenceBytes }),
        presentation: JSON.parse(presentationBytes.toString('utf8')),
      });
    }),
  );
}

export function getPublishedRecord(id: 'mg-l4yaml-source-check-20261010', version?: number): Promise<SourceCheckPackage>;
export function getPublishedRecord(id: 'mg-living-warrant-openai-jpl-20261010', version?: number): Promise<ResolutionSnapshotPackage>;
export function getPublishedRecord(id: string, version?: number): Promise<PublishedRecordPackage>;
export async function getPublishedRecord(id: string, version?: number): Promise<PublishedRecordPackage> {
  const records = await loadPublishedRecords();
  const record = records.find((candidate) => candidate.entry.id === id && (version === undefined || candidate.entry.version === version));
  requireCatalog(record !== undefined, 'PUBLISHED_RECORD_NOT_FOUND');
  return record;
}

export function getLatestPublishedRecord(id: 'mg-l4yaml-source-check-20261010'): Promise<SourceCheckPackage>;
export function getLatestPublishedRecord(id: 'mg-living-warrant-openai-jpl-20261010'): Promise<ResolutionSnapshotPackage>;
export function getLatestPublishedRecord(id: string): Promise<PublishedRecordPackage>;
export async function getLatestPublishedRecord(id: string): Promise<PublishedRecordPackage> {
  const catalog = validateRecordCatalog(catalogSource);
  const version = catalog.latest_versions[id];
  requireCatalog(typeof version === 'number', 'PUBLISHED_RECORD_NOT_FOUND');
  return getPublishedRecord(id, version);
}

export function selectLatestPublishedRecords(
  catalogValue: unknown,
  records: PublishedRecordPackage[],
): PublishedRecordPackage[] {
  const catalog = validateRecordCatalog(catalogValue);
  return Object.entries(catalog.latest_versions).map(([id, version]) => {
    const record = records.find((candidate) => candidate.entry.id === id && candidate.entry.version === version);
    requireCatalog(record !== undefined, 'PUBLISHED_RECORD_NOT_FOUND');
    return record;
  });
}

export async function loadLatestPublishedRecords(): Promise<PublishedRecordPackage[]> {
  const records = await loadPublishedRecords();
  return selectLatestPublishedRecords(catalogSource, records);
}
