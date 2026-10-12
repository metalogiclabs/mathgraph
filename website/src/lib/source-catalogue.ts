import { gzipSync } from 'node:zlib';
import { lstat, readFile, readdir, realpath } from 'node:fs/promises';
import { dirname, relative, resolve, sep } from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
import { sha256Hex } from './integrity';

export const SOURCE_CATALOGUE_MANIFEST_SHA256 = '5974ac4d68b1e090d511964cd61237565b80d39b5e47e9966171d4d8bcd2fe68';
const MAX_MANIFEST_BYTES = 1024 * 1024;
const MAX_SHARD_BYTES = 2 * 1024 * 1024;
const MAX_SEARCH_BYTES = 2 * 1024 * 1024;
const MAX_PUBLICATION_BYTES = 12 * 1024 * 1024;
const MAX_PUBLICATION_FILE_GZIP_BYTES = 256 * 1024;
const MAX_PUBLICATION_GZIP_BYTES = 1536 * 1024;
// Astro relocates server modules while prerendering. The package build root remains stable.
const defaultRoot = resolve(process.cwd(), 'public/catalogues/mathlib/v4.34.1');
const schemaRoot = resolve(process.cwd(), 'public/schemas');
const expectedSource = {
  repository: 'https://github.com/leanprover-community/mathlib4',
  commit: 'd13f23b723b8a846827a245b89c10fc7d3f11612',
  tree: 'efa132418a56d0e38c56cc412a06df22178dac5c',
  lean_toolchain: 'leanprover/lean4:v4.34.1',
};
const expectedSelectionPolicy = {
  modules: 'EXPLICIT_MODULE_LIST',
  declarations: 'USER_ORIGIN_SUPPORTED_WITH_RANGE',
  ordering: 'UTF16_LEXICOGRAPHIC',
  type_references: 'DIRECT_EXPR_CONST',
  imports: 'DIRECT_ONLY',
  omissions: 'NAMED_COUNTED',
};
const expectedLimits = {
  max_declarations: 2500,
  max_relations: 25000,
  max_search_bytes: MAX_SEARCH_BYTES,
  max_shard_bytes: MAX_SHARD_BYTES,
  max_manifest_bytes: MAX_MANIFEST_BYTES,
  max_projection_nodes: 50,
  max_projection_edges: 100,
};
const relationKinds = {
  DECLARES: ['SOURCE_MODULE', 'SOURCE_DECLARATION'],
  IMPORTS_MODULE: ['SOURCE_MODULE', 'SOURCE_MODULE'],
  TYPE_REFERENCES: ['SOURCE_DECLARATION', 'SOURCE_DECLARATION'],
} as const;

export interface SourceCatalogueExtensionV1 {
  id: string;
  version: number;
  critical: boolean;
  payload: unknown;
}
export interface SourceCatalogueAxesV1 {
  source_status: 'SOURCE_INDEXED';
  verification_status: 'NOT_CHECKED';
  current_applicability: 'NOT_CHECKED';
  freshness: 'PINNED_HISTORICAL_SOURCE';
  authorization: 'NONE';
  authority: 'NONE';
}
export interface SourcePointV1 { line: number; column: number; byte: number }
export interface SourceRangeV1 { start: SourcePointV1; end: SourcePointV1 }
export interface SourceOccurrenceV1 extends SourceCatalogueAxesV1 {
  object_id: string;
  object_contract_version: 1;
  source: { repository: string; commit: string; tree: string; module: string; path: string; range: SourceRangeV1 };
  qualified_name: string;
  kind: 'theorem' | 'definition' | 'opaque' | 'axiom' | 'inductive' | 'constructor';
  statement: string;
  statement_sha256: string;
  extensions: SourceCatalogueExtensionV1[];
}
export interface SourceModuleV1 extends SourceCatalogueAxesV1 {
  module_id: string;
  module: string;
  path: string;
  sha256: string;
  size_bytes: number;
  repository: string;
  commit: string;
  tree: string;
}
export interface SourceRelationV1 {
  relation_id: string;
  type: keyof typeof relationKinds;
  source_id: string;
  target_id: string;
  source_kind: 'SOURCE_MODULE' | 'SOURCE_DECLARATION';
  target_kind: 'SOURCE_MODULE' | 'SOURCE_DECLARATION';
  authority: 'NONE';
  logical_implication: false;
  semantic_equivalence: false;
  extensions: SourceCatalogueExtensionV1[];
}
export interface SourceCatalogueShardV1 extends SourceCatalogueAxesV1 {
  schema: 'mathgraph.source-catalogue-shard.v1';
  catalogue_version: 1;
  catalogue_id: string;
  module: SourceModuleV1;
  objects: SourceOccurrenceV1[];
  relations: SourceRelationV1[];
  omissions: {
    type_references: Array<{ source_id: string; target_name: string }>;
    imports: string[];
    declarations: Array<{ qualified_name: string; kind: string; reason: 'GENERATED' | 'MISSING_RANGE' | 'UNSUPPORTED_KIND' }>;
  };
  extensions: SourceCatalogueExtensionV1[];
}
interface ManifestModuleV1 {
  module_id: string;
  module: string;
  path: string;
  sha256: string;
  size_bytes: number;
  objects: Array<{ object_id: string; qualified_name: string }>;
}
interface ShardMetadataV1 {
  module_id: string;
  path: string;
  sha256: string;
  size_bytes: number;
  object_count: number;
  relation_count: number;
  omitted_type_references: number;
  omitted_imports: number;
  omitted_declarations: number;
}
export interface SourceCatalogueManifestV1 extends SourceCatalogueAxesV1 {
  schema: 'mathgraph.source-catalogue-manifest.v1';
  catalogue_version: 1;
  catalogue_id: string;
  source: {
    repository: string;
    commit: string;
    tree: string;
    tag: string;
    license: { path: string; sha256: string };
    citation: { path: string; sha256: string };
    lean_toolchain: { path: string; sha256: string; value: string };
    lake_manifest: { path: string; sha256: string };
    root_module: { path: string; sha256: string };
    dependency_inventory_sha256: string;
  };
  extractor: { source_commit: string; contract_version: number; sources: Array<{ path: string; sha256: string }> };
  selection_policy: typeof expectedSelectionPolicy;
  modules: ManifestModuleV1[];
  counts: {
    modules: number;
    objects: number;
    relations: number;
    omitted_type_references: number;
    omitted_imports: number;
    omitted_declarations: number;
  };
  limits: typeof expectedLimits;
  truncation: { occurred: false; reason: null };
  reproduce_command: string;
  search: { path: 'search.json'; sha256: string; size_bytes: number; object_count: number };
  shards: ShardMetadataV1[];
  extensions: SourceCatalogueExtensionV1[];
}
export interface SourceCatalogueSearchEntryV1 {
  object_id: string;
  qualified_name: string;
  module: string;
  kind: SourceOccurrenceV1['kind'];
  statement: string;
}
export interface ValidatedSourceCatalogueV1 {
  manifest: SourceCatalogueManifestV1;
  manifest_sha256: string;
  shards: SourceCatalogueShardV1[];
  search: SourceCatalogueSearchEntryV1[];
  result: {
    source_status: 'SOURCE_INDEXED';
    independent_verification: 'NOT_CHECKED';
    current_applicability: 'NOT_CHECKED';
    freshness: 'PINNED_HISTORICAL_SOURCE';
    authorization: 'NONE';
    authority: 'NONE';
  };
}
export interface SourceCatalogueLoadOptions { root?: string; expectedManifestSha256?: string }

export class SourceCatalogueError extends Error {
  constructor(public readonly code: string, message = code) {
    super(`${code}: ${message}`);
    this.name = 'SourceCatalogueError';
  }
}
function requireCatalogue(condition: boolean, code: string, message = code): asserts condition {
  if (!condition) throw new SourceCatalogueError(code, message);
}
function scalarText(value: string): void {
  requireCatalogue(!/[\uD800-\uDFFF]/u.test(value), 'UNSUPPORTED_JSON_VALUE', 'lone surrogate is not scalar Unicode');
}
function encodeCanonical(value: unknown, active = new Set<object>()): string {
  if (value === null) return 'null';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'number') {
    requireCatalogue(Number.isSafeInteger(value) && !Object.is(value, -0), 'UNSUPPORTED_JSON_VALUE', 'only safe nonnegative-zero integers are admitted');
    return JSON.stringify(value);
  }
  if (typeof value === 'string') {
    scalarText(value);
    return JSON.stringify(value);
  }
  requireCatalogue(Array.isArray(value) || (typeof value === 'object' && Object.getPrototypeOf(value) === Object.prototype), 'UNSUPPORTED_JSON_VALUE');
  requireCatalogue(!active.has(value), 'UNSUPPORTED_JSON_VALUE', 'cyclic value');
  active.add(value);
  try {
    if (Array.isArray(value)) return `[${value.map(item => encodeCanonical(item, active)).join(',')}]`;
    const object = value as Record<string, unknown>;
    for (const key of Object.keys(object)) scalarText(key);
    return `{${Object.keys(object).sort().map(key => `${encodeCanonical(key, active)}:${encodeCanonical(object[key], active)}`).join(',')}}`;
  } finally {
    active.delete(value);
  }
}
export function parseCanonicalSourceJson(raw: Uint8Array, maximum: number): unknown {
  requireCatalogue(raw.byteLength <= maximum, 'INPUT_TOO_LARGE');
  let text: string;
  try {
    text = new TextDecoder('utf-8', { fatal: true }).decode(raw);
  } catch {
    throw new SourceCatalogueError('INVALID_UTF8');
  }
  requireCatalogue(!text.startsWith('\uFEFF'), 'INVALID_UTF8', 'UTF-8 BOM is not admitted');
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    throw new SourceCatalogueError('INVALID_JSON');
  }
  const canonical = encodeCanonical(value);
  requireCatalogue(text === canonical, 'NONCANONICAL_JSON');
  return value;
}
function canonical(value: unknown): string { return encodeCanonical(value); }
function axes(value: SourceCatalogueAxesV1): void {
  requireCatalogue(value.source_status === 'SOURCE_INDEXED'
    && value.verification_status === 'NOT_CHECKED'
    && value.current_applicability === 'NOT_CHECKED'
    && value.freshness === 'PINNED_HISTORICAL_SOURCE'
    && value.authorization === 'NONE'
    && value.authority === 'NONE', 'AUTHORITY_ESCALATION');
}
function extensions(values: SourceCatalogueExtensionV1[]): void {
  const seen = new Set<string>();
  for (const extension of values) {
    const identity = `${extension.id}@${extension.version}`;
    requireCatalogue(!seen.has(identity), 'DUPLICATE_EXTENSION');
    seen.add(identity);
    requireCatalogue(extension.critical === false, 'UNKNOWN_CRITICAL_EXTENSION');
    encodeCanonical(extension.payload);
  }
}
function safeRelativePath(value: string): void {
  requireCatalogue(Boolean(value) && !value.startsWith('/') && !value.includes('\\') && !value.includes(':')
    && value.split('/').every(part => part !== '' && part !== '.' && part !== '..')
    && ![...value].some(char => char.charCodeAt(0) < 32 || char.charCodeAt(0) === 127), 'INVALID_PATH');
}
async function safeFile(root: string, path: string): Promise<string> {
  safeRelativePath(path);
  const rootStat = await lstat(root).catch(() => null);
  requireCatalogue(rootStat?.isDirectory() === true && !rootStat.isSymbolicLink(), 'UNSAFE_INPUT');
  const resolvedRoot = await realpath(root);
  const absolute = resolve(resolvedRoot, ...path.split('/'));
  const relativePath = relative(resolvedRoot, absolute);
  requireCatalogue(relativePath !== '..' && !relativePath.startsWith(`..${sep}`) && !resolve(absolute).startsWith(`${resolvedRoot}${sep}..`), 'INVALID_PATH');
  let parent = dirname(absolute);
  while (parent !== resolvedRoot) {
    const stat = await lstat(parent).catch(() => null);
    requireCatalogue(stat?.isDirectory() === true && !stat.isSymbolicLink(), 'UNSAFE_INPUT');
    parent = dirname(parent);
  }
  const stat = await lstat(absolute).catch(() => null);
  requireCatalogue(stat?.isFile() === true && !stat.isSymbolicLink(), 'MISSING_PUBLICATION_FILE');
  requireCatalogue(await realpath(absolute) === absolute, 'UNSAFE_INPUT');
  return absolute;
}
async function publicationFiles(root: string): Promise<string[]> {
  const rootReal = await realpath(root);
  const files: string[] = [];
  async function visit(directory: string): Promise<void> {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const path = resolve(directory, entry.name);
      requireCatalogue(!entry.isSymbolicLink(), 'UNSAFE_INPUT');
      if (entry.isDirectory()) await visit(path);
      else if (entry.isFile()) files.push(relative(rootReal, path).split(sep).join('/'));
      else throw new SourceCatalogueError('UNSAFE_INPUT');
    }
  }
  await visit(rootReal);
  return files.sort();
}
async function validators() {
  const ajv = new Ajv2020({ allErrors: true, strict: true });
  const [manifestSchema, shardSchema] = await Promise.all([
    readFile(resolve(schemaRoot, 'source-catalogue-manifest-v1.schema.json'), 'utf8'),
    readFile(resolve(schemaRoot, 'source-catalogue-shard-v1.schema.json'), 'utf8'),
  ]);
  return {
    manifest: ajv.compile(JSON.parse(manifestSchema)),
    shard: ajv.compile(JSON.parse(shardSchema)),
  };
}
function identity(prefix: string, payload: Record<string, unknown>): string {
  return `${prefix}${sha256Hex(canonical(payload))}`;
}
function moduleId(repository: string, commit: string, module: string, path: string): string {
  return identity('module-', { repository, commit, module, path });
}
function occurrenceId(source: SourceOccurrenceV1['source'], qualifiedName: string, version = 1): string {
  return identity('object-', {
    repository: source.repository, commit: source.commit, module: source.module, path: source.path,
    qualified_name: qualifiedName, object_contract_version: version,
  });
}
function relationId(catalogueId: string, type: string, sourceId: string, targetId: string): string {
  return identity('relation-', { catalogue_id: catalogueId, relation_type: type, source_id: sourceId, target_id: targetId });
}
function ordered(values: string[]): void {
  requireCatalogue(values.every((value, index) => index === 0 || values[index - 1] < value), 'INVALID_ORDER');
}
function rangeValid(value: SourceRangeV1, maximum: number): void {
  for (const point of [value.start, value.end]) {
    requireCatalogue(Number.isSafeInteger(point.line) && point.line >= 1
      && Number.isSafeInteger(point.column) && point.column >= 0
      && Number.isSafeInteger(point.byte) && point.byte >= 0 && point.byte <= maximum
      && point.column <= point.byte && point.byte >= point.column + point.line - 1, 'INVALID_RANGE');
    if (point.line === 1) requireCatalogue(point.byte === point.column, 'INVALID_RANGE');
  }
  const { start, end } = value;
  requireCatalogue(start.byte < end.byte && (start.line < end.line || (start.line === end.line && start.column < end.column)), 'INVALID_RANGE');
  if (start.line === end.line) requireCatalogue(end.byte - start.byte === end.column - start.column, 'INVALID_RANGE');
  else requireCatalogue(end.byte - start.byte >= end.line - start.line + end.column, 'INVALID_RANGE');
}

export async function loadSourceCatalogueV1(options: SourceCatalogueLoadOptions = {}): Promise<ValidatedSourceCatalogueV1> {
  const root = resolve(options.root ?? defaultRoot);
  const expectedManifestSha256 = options.expectedManifestSha256 ?? SOURCE_CATALOGUE_MANIFEST_SHA256;
  requireCatalogue(/^[0-9a-f]{64}$/.test(expectedManifestSha256), 'INVALID_DIGEST');
  const manifestPath = await safeFile(root, 'manifest.json');
  const manifestBytes = await readFile(manifestPath);
  requireCatalogue(sha256Hex(manifestBytes) === expectedManifestSha256, 'MANIFEST_PIN_MISMATCH');
  const manifest = parseCanonicalSourceJson(manifestBytes, MAX_MANIFEST_BYTES) as SourceCatalogueManifestV1;
  const validate = await validators();
  if (Array.isArray(manifest.extensions)) extensions(manifest.extensions);
  requireCatalogue(validate.manifest(manifest), 'INVALID_MANIFEST_SCHEMA', validate.manifest.errors?.map(error => `${error.instancePath}:${error.keyword}`).join(', '));
  requireCatalogue(manifest.schema === 'mathgraph.source-catalogue-manifest.v1' && manifest.catalogue_version === 1
    && manifest.catalogue_id === 'mathlib-v4.34.1-foundations-v1', 'UNSUPPORTED_VERSION');
  axes(manifest);
  requireCatalogue(manifest.source.repository === expectedSource.repository
    && manifest.source.commit === expectedSource.commit
    && manifest.source.tree === expectedSource.tree
    && manifest.source.lean_toolchain.value === expectedSource.lean_toolchain, 'SOURCE_PIN_MISMATCH');
  requireCatalogue(canonical(manifest.selection_policy) === canonical(expectedSelectionPolicy), 'INVALID_POLICY');
  requireCatalogue(canonical(manifest.limits) === canonical(expectedLimits), 'COUNT_LIMIT_EXCEEDED');
  requireCatalogue(manifest.truncation.occurred === false && manifest.truncation.reason === null, 'TRUNCATION_NOT_PERMITTED');

  const moduleIds = new Set<string>();
  const moduleNames = new Set<string>();
  const modulePaths = new Set<string>();
  const objectIds = new Set<string>();
  const qualifiedNames = new Set<string>();
  for (const module of manifest.modules) {
    safeRelativePath(module.path);
    requireCatalogue(module.path === `${module.module.replaceAll('.', '/')}.lean`, 'SOURCE_PIN_MISMATCH');
    requireCatalogue(module.module_id === moduleId(manifest.source.repository, manifest.source.commit, module.module, module.path), 'IDENTITY_MISMATCH');
    requireCatalogue(!moduleIds.has(module.module_id) && !moduleNames.has(module.module) && !modulePaths.has(module.path), 'DUPLICATE_ID');
    moduleIds.add(module.module_id); moduleNames.add(module.module); modulePaths.add(module.path);
    for (const object of module.objects) {
      const source = { repository: manifest.source.repository, commit: manifest.source.commit, tree: manifest.source.tree, module: module.module, path: module.path, range: { start: { line: 1, column: 0, byte: 0 }, end: { line: 1, column: 1, byte: 1 } } };
      requireCatalogue(object.object_id === occurrenceId(source, object.qualified_name), 'IDENTITY_MISMATCH');
      requireCatalogue(!objectIds.has(object.object_id) && !qualifiedNames.has(object.qualified_name), 'DUPLICATE_NAME');
      objectIds.add(object.object_id); qualifiedNames.add(object.qualified_name);
    }
    ordered(module.objects.map(object => object.qualified_name));
  }
  ordered(manifest.modules.map(module => module.module));
  requireCatalogue(manifest.shards.length === manifest.modules.length
    && manifest.shards.every((metadata, index) => metadata.module_id === manifest.modules[index].module_id), 'SHARD_INVENTORY_MISMATCH');
  requireCatalogue(manifest.counts.modules === manifest.modules.length
    && manifest.counts.objects === objectIds.size
    && manifest.counts.relations === manifest.shards.reduce((sum, shard) => sum + shard.relation_count, 0)
    && manifest.counts.omitted_type_references === manifest.shards.reduce((sum, shard) => sum + shard.omitted_type_references, 0)
    && manifest.counts.omitted_imports === manifest.shards.reduce((sum, shard) => sum + shard.omitted_imports, 0)
    && manifest.counts.omitted_declarations === manifest.shards.reduce((sum, shard) => sum + shard.omitted_declarations, 0), 'COUNT_MISMATCH');
  requireCatalogue(manifest.counts.objects <= expectedLimits.max_declarations && manifest.counts.relations <= expectedLimits.max_relations, 'COUNT_LIMIT_EXCEEDED');

  const endpoints = new Map<string, readonly ['SOURCE_MODULE' | 'SOURCE_DECLARATION', string]>();
  for (const module of manifest.modules) {
    endpoints.set(module.module_id, ['SOURCE_MODULE', module.module_id]);
    for (const object of module.objects) endpoints.set(object.object_id, ['SOURCE_DECLARATION', module.module_id]);
  }
  const shards: SourceCatalogueShardV1[] = [];
  const rawFiles = new Map<string, Uint8Array>([['manifest.json', manifestBytes]]);
  const allRelationIds = new Set<string>();
  const expectedSearch: SourceCatalogueSearchEntryV1[] = [];
  for (let shardIndex = 0; shardIndex < manifest.shards.length; shardIndex += 1) {
    const metadata = manifest.shards[shardIndex];
    safeRelativePath(metadata.path);
    requireCatalogue(metadata.path === `shards/${metadata.sha256}.json`, 'CONTENT_ADDRESS_MISMATCH');
    const shardBytes = await readFile(await safeFile(root, metadata.path));
    requireCatalogue(shardBytes.byteLength === metadata.size_bytes && sha256Hex(shardBytes) === metadata.sha256, 'SHARD_INTEGRITY_MISMATCH');
    const shard = parseCanonicalSourceJson(shardBytes, MAX_SHARD_BYTES) as SourceCatalogueShardV1;
    if (Array.isArray(shard.extensions)) extensions(shard.extensions);
    requireCatalogue(validate.shard(shard), 'INVALID_SHARD_SCHEMA', validate.shard.errors?.map(error => `${error.instancePath}:${error.keyword}`).join(', '));
    requireCatalogue(shard.schema === 'mathgraph.source-catalogue-shard.v1' && shard.catalogue_version === 1 && shard.catalogue_id === manifest.catalogue_id, 'UNSUPPORTED_VERSION');
    axes(shard); axes(shard.module);
    const selected = manifest.modules[shardIndex];
    requireCatalogue(['module_id', 'module', 'path', 'sha256', 'size_bytes'].every(key => (shard.module as unknown as Record<string, unknown>)[key] === (selected as unknown as Record<string, unknown>)[key]), 'SOURCE_PIN_MISMATCH');
    requireCatalogue(shard.module.repository === manifest.source.repository && shard.module.commit === manifest.source.commit && shard.module.tree === manifest.source.tree, 'SOURCE_PIN_MISMATCH');
    const localObjectIds = new Set<string>();
    const localNames = new Set<string>();
    for (const object of shard.objects) {
      axes(object); extensions(object.extensions);
      requireCatalogue(object.object_contract_version === 1, 'UNSUPPORTED_VERSION');
      requireCatalogue(object.source.repository === shard.module.repository && object.source.commit === shard.module.commit
        && object.source.tree === shard.module.tree && object.source.module === shard.module.module && object.source.path === shard.module.path, 'SOURCE_PIN_MISMATCH');
      rangeValid(object.source.range, shard.module.size_bytes);
      requireCatalogue(sha256Hex(object.statement) === object.statement_sha256, 'STATEMENT_INTEGRITY_MISMATCH');
      requireCatalogue(object.object_id === occurrenceId(object.source, object.qualified_name), 'IDENTITY_MISMATCH');
      requireCatalogue(!localObjectIds.has(object.object_id) && !localNames.has(object.qualified_name), 'DUPLICATE_NAME');
      localObjectIds.add(object.object_id); localNames.add(object.qualified_name);
      expectedSearch.push({ object_id: object.object_id, qualified_name: object.qualified_name, module: object.source.module, kind: object.kind, statement: object.statement });
    }
    ordered(shard.objects.map(object => object.qualified_name));
    requireCatalogue(canonical(shard.objects.map(object => ({ object_id: object.object_id, qualified_name: object.qualified_name }))) === canonical(selected.objects), 'OBJECT_INVENTORY_MISMATCH');
    const declares = new Set<string>();
    for (const relation of shard.relations) {
      extensions(relation.extensions);
      requireCatalogue(relation.authority === 'NONE' && relation.logical_implication === false && relation.semantic_equivalence === false, 'AUTHORITY_ESCALATION');
      const expectedKinds = relationKinds[relation.type];
      requireCatalogue(expectedKinds !== undefined, 'UNSUPPORTED_RELATION');
      const sourceEndpoint = endpoints.get(relation.source_id);
      const targetEndpoint = endpoints.get(relation.target_id);
      requireCatalogue(sourceEndpoint !== undefined && targetEndpoint !== undefined, 'UNKNOWN_ENDPOINT');
      requireCatalogue(sourceEndpoint[0] === expectedKinds[0] && targetEndpoint[0] === expectedKinds[1]
        && relation.source_kind === expectedKinds[0] && relation.target_kind === expectedKinds[1], 'ENDPOINT_KIND_MISMATCH');
      requireCatalogue(sourceEndpoint[1] === shard.module.module_id, 'RELATION_PROVENANCE_MISMATCH');
      if (relation.type === 'DECLARES') {
        requireCatalogue(targetEndpoint[1] === shard.module.module_id, 'RELATION_PROVENANCE_MISMATCH');
        declares.add(relation.target_id);
      }
      requireCatalogue(relation.relation_id === relationId(manifest.catalogue_id, relation.type, relation.source_id, relation.target_id), 'IDENTITY_MISMATCH');
      requireCatalogue(!allRelationIds.has(relation.relation_id), 'DUPLICATE_ID');
      allRelationIds.add(relation.relation_id);
    }
    ordered(shard.relations.map(relation => relation.relation_id));
    requireCatalogue(declares.size === localObjectIds.size && [...localObjectIds].every(id => declares.has(id)), 'MISSING_DECLARES');
    const typeOmissions = new Set<string>();
    for (const omission of shard.omissions.type_references) {
      requireCatalogue(localObjectIds.has(omission.source_id) && !qualifiedNames.has(omission.target_name), 'INVALID_OMISSION');
      const key = `${omission.source_id}\0${omission.target_name}`;
      requireCatalogue(!typeOmissions.has(key), 'INVALID_OMISSION');
      typeOmissions.add(key);
    }
    ordered(shard.omissions.type_references.map(omission => `${omission.source_id}\0${omission.target_name}`));
    const imports = new Set<string>();
    for (const imported of shard.omissions.imports) {
      requireCatalogue(!moduleNames.has(imported) && !imports.has(imported), 'INVALID_OMISSION');
      imports.add(imported);
    }
    ordered(shard.omissions.imports);
    const declarationOmissions = new Set<string>();
    for (const omission of shard.omissions.declarations) {
      requireCatalogue(!qualifiedNames.has(omission.qualified_name) && !declarationOmissions.has(omission.qualified_name), 'INVALID_OMISSION');
      declarationOmissions.add(omission.qualified_name);
    }
    ordered(shard.omissions.declarations.map(omission => omission.qualified_name));
    requireCatalogue(metadata.object_count === shard.objects.length && metadata.relation_count === shard.relations.length
      && metadata.omitted_type_references === shard.omissions.type_references.length
      && metadata.omitted_imports === shard.omissions.imports.length
      && metadata.omitted_declarations === shard.omissions.declarations.length, 'COUNT_MISMATCH');
    shards.push(shard); rawFiles.set(metadata.path, shardBytes);
  }
  requireCatalogue(allRelationIds.size === manifest.counts.relations, 'COUNT_MISMATCH');
  expectedSearch.sort((left, right) => left.qualified_name < right.qualified_name ? -1 : left.qualified_name > right.qualified_name ? 1 : 0);
  const searchBytes = await readFile(await safeFile(root, manifest.search.path));
  requireCatalogue(searchBytes.byteLength === manifest.search.size_bytes && sha256Hex(searchBytes) === manifest.search.sha256, 'SEARCH_INTEGRITY_MISMATCH');
  const search = parseCanonicalSourceJson(searchBytes, MAX_SEARCH_BYTES) as SourceCatalogueSearchEntryV1[];
  requireCatalogue(canonical(search) === canonical(expectedSearch), 'SEARCH_DERIVATION_MISMATCH');
  rawFiles.set(manifest.search.path, searchBytes);
  const expectedPaths = ['manifest.json', manifest.search.path, ...manifest.shards.map(shard => shard.path)].sort();
  requireCatalogue(canonical(await publicationFiles(root)) === canonical(expectedPaths), 'PUBLICATION_INVENTORY_MISMATCH');
  const raw = [...rawFiles.values()];
  requireCatalogue(raw.reduce((sum, value) => sum + value.byteLength, 0) <= MAX_PUBLICATION_BYTES, 'INPUT_TOO_LARGE');
  const gzipSizes = raw.map(value => gzipSync(value).byteLength);
  requireCatalogue(gzipSizes.every(size => size <= MAX_PUBLICATION_FILE_GZIP_BYTES)
    && gzipSizes.reduce((sum, value) => sum + value, 0) <= MAX_PUBLICATION_GZIP_BYTES, 'INPUT_TOO_LARGE');
  return structuredClone({
    manifest,
    manifest_sha256: expectedManifestSha256,
    shards,
    search,
    result: {
      source_status: 'SOURCE_INDEXED', independent_verification: 'NOT_CHECKED',
      current_applicability: 'NOT_CHECKED', freshness: 'PINNED_HISTORICAL_SOURCE',
      authorization: 'NONE', authority: 'NONE',
    },
  });
}
