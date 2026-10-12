import { canonicalJson } from './integrity';
import { objectSlug } from './object-locators';
import type { ObjectProjection, ProjectionCollection } from './object-projections';
import type { SourceCatalogueSearchEntryV1 } from './source-catalogue';

export const exploreCategories = ['SOURCE_INDEXED', 'EVIDENCE_RECORD', 'QUALIFIED_CAPABILITY'] as const;
export type ExploreCategory = typeof exploreCategories[number];

export interface ExploreEntry {
  id: string;
  sourceId: string;
  title: string;
  finalName: string;
  kind: ObjectProjection['kind'];
  category: ExploreCategory;
  project: 'Mathlib' | 'MathGraph';
  module: string;
  status: string;
  sourceStatus?: string;
  independentVerification?: string;
  actionAuthorization: string;
  href: string;
  /** Search-only source metadata. Status fields are deliberately excluded. */
  metadata: string;
}

export interface ExploreFilters {
  project?: string;
  kind?: string;
  module?: string;
  status?: string;
}

interface BuildOptions { sourceSearch?: SourceCatalogueSearchEntryV1[] }

function requireExplore(condition: boolean, code: string): asserts condition {
  if (!condition) throw new Error(code);
}

function normalize(value: string): string {
  return value.normalize('NFKC').toLocaleLowerCase('en-US').trim();
}

function tokens(value: string): string[] {
  return normalize(value).match(/[\p{L}\p{N}]+/gu) ?? [];
}

function finalName(title: string): string {
  return title.split(/[.:/#]/u).filter(Boolean).at(-1) ?? title;
}

function sourceModule(object: ObjectProjection): string {
  if (object.kind === 'SOURCE_MODULE') return String(object.details.module ?? '');
  if (object.kind === 'SOURCE_DECLARATION') {
    const source = object.details.source as { module?: unknown } | undefined;
    return typeof source?.module === 'string' ? source.module : '';
  }
  return object.kind === 'FINITE_CAPABILITY' ? 'Capabilities' : 'Evidence records';
}

function category(object: ObjectProjection): ExploreCategory | null {
  if (object.kind === 'SOURCE_MODULE' || object.kind === 'SOURCE_DECLARATION') return 'SOURCE_INDEXED';
  if (object.kind === 'FINITE_CAPABILITY') return object.axes.historical_result === 'QUALIFIED_BOUNDED' ? 'QUALIFIED_CAPABILITY' : null;
  return 'EVIDENCE_RECORD';
}

function entryFor(object: ObjectProjection): ExploreEntry | null {
  requireExplore(object.authority === 'NONE', 'EXPLORE_AUTHORITY_ESCALATION');
  const objectCategory = category(object);
  if (objectCategory === null) return null;
  if (objectCategory === 'SOURCE_INDEXED') {
    requireExplore(object.axes.source_status === 'SOURCE_INDEXED'
      && object.axes.independent_verification === 'NOT_CHECKED'
      && object.axes.historical_result === 'UNKNOWN'
      && object.axes.action_authorization === 'NONE', 'SOURCE_STATUS_MISMATCH');
  }
  const module = sourceModule(object);
  requireExplore(module.length > 0, 'EXPLORE_SOURCE_MISMATCH');
  const status = objectCategory === 'SOURCE_INDEXED' ? 'SOURCE_INDEXED' : object.axes.historical_result;
  const searchableDetails = object.kind === 'SOURCE_DECLARATION'
    ? {
        qualified_name: object.details.qualified_name,
        declaration_kind: object.details.declaration_kind,
        statement: object.details.statement,
        source: object.details.source,
      }
    : object.kind === 'SOURCE_MODULE'
      ? { module: object.details.module, path: object.details.path, source: object.details.source }
      : object.details;
  return {
    id: object.id,
    sourceId: object.source_id,
    title: object.title,
    finalName: finalName(object.title),
    kind: object.kind,
    category: objectCategory,
    project: objectCategory === 'SOURCE_INDEXED' ? 'Mathlib' : 'MathGraph',
    module,
    status,
    ...(object.axes.source_status === undefined ? {} : { sourceStatus: object.axes.source_status }),
    ...(object.axes.independent_verification === undefined ? {} : { independentVerification: object.axes.independent_verification }),
    actionAuthorization: object.axes.action_authorization,
    href: `/objects/${objectSlug(object.id)}/`,
    metadata: `${object.title} ${object.source_id} ${object.kind} ${module} ${canonicalJson(searchableDetails)}`,
  };
}

export function validateExploreEntries(entries: ExploreEntry[], collection: ProjectionCollection): void {
  const expected = new Map<string, ExploreEntry>();
  for (const object of collection.objects) {
    const entry = entryFor(object);
    if (entry !== null) {
      requireExplore(!expected.has(entry.id), 'EXPLORE_ID_COLLISION');
      expected.set(entry.id, entry);
    }
  }
  requireExplore(entries.length === expected.size, 'EXPLORE_COUNT_MISMATCH');
  const ids = new Set<string>();
  const hrefs = new Set<string>();
  for (const entry of entries) {
    requireExplore(!ids.has(entry.id), 'EXPLORE_ID_COLLISION');
    requireExplore(!hrefs.has(entry.href), 'EXPLORE_URL_COLLISION');
    ids.add(entry.id); hrefs.add(entry.href);
    const match = expected.get(entry.id);
    requireExplore(match !== undefined, 'EXPLORE_SOURCE_MISMATCH');
    requireExplore(entry.href === `/objects/${objectSlug(entry.id)}/`, 'EXPLORE_URL_MISMATCH');
    requireExplore(canonicalJson(entry) === canonicalJson(match), 'EXPLORE_STATUS_MISMATCH');
  }
}

function validateSearch(search: SourceCatalogueSearchEntryV1[], collection: ProjectionCollection): void {
  const declarations = new Map(collection.objects
    .filter(object => object.kind === 'SOURCE_DECLARATION')
    .map(object => [object.source_id, object]));
  requireExplore(search.length === declarations.size, 'SOURCE_SEARCH_MISMATCH');
  const seen = new Set<string>();
  for (const value of search) {
    requireExplore(!seen.has(value.object_id), 'SOURCE_SEARCH_MISMATCH');
    seen.add(value.object_id);
    const object = declarations.get(value.object_id);
    const source = object?.details.source as { module?: unknown } | undefined;
    requireExplore(object !== undefined
      && object.title === value.qualified_name
      && object.details.qualified_name === value.qualified_name
      && object.details.declaration_kind === value.kind
      && object.details.statement === value.statement
      && source?.module === value.module, 'SOURCE_SEARCH_MISMATCH');
  }
}

export function buildExploreEntries(collection: ProjectionCollection, options: BuildOptions = {}): ExploreEntry[] {
  if (options.sourceSearch !== undefined) validateSearch(options.sourceSearch, collection);
  const entries: ExploreEntry[] = [];
  const ids = new Set<string>();
  for (const object of collection.objects) {
    const entry = entryFor(object);
    if (entry === null) continue;
    requireExplore(!ids.has(entry.id), 'EXPLORE_ID_COLLISION');
    ids.add(entry.id);
    entries.push(entry);
  }
  entries.sort((left, right) => left.id < right.id ? -1 : left.id > right.id ? 1 : 0);
  validateExploreEntries(entries, collection);
  return structuredClone(entries);
}

function orderedSubsequence(query: string[], value: string[]): boolean {
  let index = 0;
  for (const token of value) if (token === query[index]) index += 1;
  return index === query.length;
}

function relevance(entry: ExploreEntry, query: string): number | null {
  const needle = normalize(query);
  if (!needle) return 5;
  const title = normalize(entry.title);
  if (title === needle) return 0;
  if (normalize(entry.finalName) === needle) return 1;
  const queryTokens = tokens(query);
  if (queryTokens.length > 0 && orderedSubsequence(queryTokens, tokens(entry.title))) return 2;
  if (title.includes(needle)) return 3;
  const metadata = normalize(entry.metadata);
  if (queryTokens.length > 0 && queryTokens.every(token => metadata.includes(token))) return 4;
  return metadata.includes(needle) ? 4 : null;
}

export function rankExploreEntries(entries: ExploreEntry[], query: string, filters: ExploreFilters): ExploreEntry[] {
  return entries
    .map(entry => ({ entry, score: relevance(entry, query) }))
    .filter((candidate): candidate is { entry: ExploreEntry; score: number } => candidate.score !== null)
    .filter(({ entry }) => (!filters.project || entry.project === filters.project)
      && (!filters.kind || entry.kind === filters.kind)
      && (!filters.module || entry.module === filters.module)
      && (!filters.status || entry.status === filters.status))
    .sort((left, right) => left.score - right.score
      || (left.entry.id < right.entry.id ? -1 : left.entry.id > right.entry.id ? 1 : 0))
    .map(({ entry }) => entry);
}
