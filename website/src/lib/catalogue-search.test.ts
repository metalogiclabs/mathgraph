import { beforeAll, describe, expect, test } from 'vitest';

import { loadObjectProjections } from '../data/object-projections';
import { loadSourceCatalogueProjections } from '../data/source-catalogue';
import { mergeProjectionCollections, type ProjectionCollection } from './object-projections';
import { objectSlug } from './object-locators';
import { loadSourceCatalogueV1, type ValidatedSourceCatalogueV1 } from './source-catalogue';
import {
  buildExploreEntries,
  rankExploreEntries,
  validateExploreEntries,
  type ExploreEntry,
} from './catalogue-search';

let source: ValidatedSourceCatalogueV1;
let projections: ProjectionCollection;
let entries: ExploreEntry[];

beforeAll(async () => {
  source = await loadSourceCatalogueV1();
  projections = mergeProjectionCollections([
    await loadObjectProjections(),
    await loadSourceCatalogueProjections(),
  ]);
  entries = buildExploreEntries(projections, { sourceSearch: source.search });
});

describe('deterministic living-network catalogue search', () => {
  test('builds the complete validated source, evidence and qualified-capability catalogue', () => {
    expect(entries).toHaveLength(2372);
    expect(entries.filter(entry => entry.category === 'SOURCE_INDEXED')).toHaveLength(2358);
    expect(entries.filter(entry => entry.category === 'QUALIFIED_CAPABILITY')).toHaveLength(1);
    expect(entries.filter(entry => entry.kind === 'SOURCE_DECLARATION')).toHaveLength(2345);
    expect(entries.every(entry => {
      const object = projections.objects.find(value => value.id === entry.id)!;
      return entry.href === `/objects/${objectSlug(object)}/`;
    })).toBe(true);
    expect(entries.filter(entry => entry.category !== 'EVIDENCE_RECORD')
      .every(entry => entry.actionAuthorization === 'NONE')).toBe(true);
    expect(entries.every(entry => entry.actionAuthorization !== 'PERMIT')).toBe(true);
    expect(new Set(entries.map(entry => entry.id)).size).toBe(entries.length);
  });

  test('ranks exact qualified names, exact final names and ordered name tokens before metadata', () => {
    expect(rankExploreEntries(entries, 'Real.rpow', {})[0].title).toBe('Real.rpow');
    expect(rankExploreEntries(entries, 'rpow', {})[0].title).toBe('Real.rpow');
    expect(rankExploreEntries(entries, 'Real add natCast', {})[0].title).toContain('Real.rpow_add_natCast');
    expect(rankExploreEntries(entries, 'EmptyCollection emptyCollection False', {})[0].title).toBe('Set.exists_mem_empty');

    const sample = (id: string, title: string, status: string, metadata: string): ExploreEntry => ({
      id, sourceId: id, title, finalName: title.split('.').at(-1)!, kind: 'SOURCE_DECLARATION',
      category: 'SOURCE_INDEXED', project: 'Mathlib', module: 'Mathlib.Test', status,
      sourceStatus: 'SOURCE_INDEXED', independentVerification: 'NOT_CHECKED',
      actionAuthorization: 'NONE', href: `/objects/${objectSlug(id)}/`, metadata,
    });
    const tied = [
      sample('b', 'Example.alpha', 'WARRANTED_BOUNDED', 'needle'),
      sample('a', 'Example.beta', 'UNKNOWN', 'needle'),
    ];
    expect(rankExploreEntries(tied, 'needle', {}).map(entry => entry.id)).toEqual(['a', 'b']);
  });

  test('applies project, kind, module and status filters without status-based relevance', () => {
    const filtered = rankExploreEntries(entries, 'rpow', {
      project: 'Mathlib', kind: 'SOURCE_DECLARATION', module: 'Mathlib.Analysis.SpecialFunctions.Pow.Real', status: 'SOURCE_INDEXED',
    });
    expect(filtered.length).toBeGreaterThan(1);
    expect(filtered.every(entry => entry.project === 'Mathlib'
      && entry.kind === 'SOURCE_DECLARATION'
      && entry.module === 'Mathlib.Analysis.SpecialFunctions.Pow.Real'
      && entry.status === 'SOURCE_INDEXED')).toBe(true);
    expect(rankExploreEntries(entries, 'a-query-that-cannot-match-any-entry', {})).toEqual([]);
  });

  test('rejects corrupted search entries, duplicate identities, wrong URLs and status promotion', () => {
    const corruptedSearch = structuredClone(source.search);
    corruptedSearch[0].statement = 'False';
    expect(() => buildExploreEntries(projections, { sourceSearch: corruptedSearch })).toThrow('SOURCE_SEARCH_MISMATCH');

    const duplicate = structuredClone(projections);
    duplicate.objects.push(structuredClone(duplicate.objects[0]));
    expect(() => buildExploreEntries(duplicate, { sourceSearch: source.search })).toThrow('EXPLORE_ID_COLLISION');

    const wrongUrl = structuredClone(entries);
    wrongUrl[0].href = '/objects/not-the-object/';
    expect(() => validateExploreEntries(wrongUrl, projections)).toThrow('EXPLORE_URL_MISMATCH');

    const promoted = structuredClone(projections);
    const declaration = promoted.objects.find(object => object.kind === 'SOURCE_DECLARATION')!;
    declaration.axes.source_status = 'VERIFIED';
    expect(() => buildExploreEntries(promoted, { sourceSearch: source.search })).toThrow('SOURCE_STATUS_MISMATCH');
  });
});
