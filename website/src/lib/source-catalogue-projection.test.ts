import { beforeAll, describe, expect, test } from 'vitest';
import { validatePublicRecordSchema } from './catalog';
import { canonicalJson, sha256Hex } from './integrity';
import { buildKnowledgeMap } from './knowledge-map';
import {
  mergeProjectionCollections,
  projectSourceCatalogueV1,
  type ProjectionCollection,
} from './object-projections';
import { loadSourceCatalogueV1, type ValidatedSourceCatalogueV1 } from './source-catalogue';
import { loadLivingKnowledgeProjections } from '../data/source-catalogue';
import { loadObjectProjections } from '../data/object-projections';

let catalogue: ValidatedSourceCatalogueV1;
let projected: ProjectionCollection;

beforeAll(async () => {
  catalogue = await loadSourceCatalogueV1();
  projected = projectSourceCatalogueV1(catalogue);
});

describe('authority-free source catalogue website projections', () => {
  test('projects exact modules, occurrences and structural relations without terminal authority', () => {
    expect(projected.objects).toHaveLength(13 + 2345);
    expect(projected.relations).toHaveLength(3571);
    expect(projected.objects.filter(item => item.kind === 'SOURCE_MODULE')).toHaveLength(13);
    expect(projected.objects.filter(item => item.kind === 'SOURCE_DECLARATION')).toHaveLength(2345);
    for (const object of projected.objects) {
      expect(object.authority).toBe('NONE');
      expect(object.axes.source_status).toBe('SOURCE_INDEXED');
      expect(object.axes.independent_verification).toBe('NOT_CHECKED');
      expect(object.axes.historical_result).toBe('UNKNOWN');
      expect(object.axes.action_authorization).toBe('NONE');
      expect(object.verifier_authority).toEqual([]);
      expect(object).not.toHaveProperty('terminal_form');
      expect(() => validatePublicRecordSchema(object)).toThrow('PUBLIC_RECORD_SCHEMA_INVALID');
    }
    for (const relation of projected.relations) {
      expect(relation.authority).toBe('NONE');
      expect(relation.logical_implication).toBe(false);
      expect(relation.semantic_equivalence).toBe(false);
    }
    expect(new Set(projected.relations.map(item => item.type))).toEqual(new Set(['DECLARES', 'IMPORTS_MODULE', 'TYPE_REFERENCES']));
  });

  test('preserves every existing record and capability projection byte-for-byte', async () => {
    const before = await loadObjectProjections();
    expect(sha256Hex(canonicalJson(before))).toBe('86df306cf8e726881fd4eafd4574c3210fb4b70b84098f8186815b77836eb72f');
    await loadLivingKnowledgeProjections();
    const after = await loadObjectProjections();
    expect(canonicalJson(after)).toBe(canonicalJson(before));
  });

  test('merges independently validated adapters and rejects every identity surface collision', async () => {
    const legacy = await loadObjectProjections();
    const living = await loadLivingKnowledgeProjections();
    expect(living.objects).toHaveLength(legacy.objects.length + projected.objects.length);
    expect(living.relations).toHaveLength(legacy.relations.length + projected.relations.length);

    const base = structuredClone(legacy.objects[0]);
    const fragment = (object = base, relation: ProjectionCollection['relations'][number] | null = null): ProjectionCollection => ({ objects: [object], relations: relation ? [relation] : [] });
    expect(() => mergeProjectionCollections([fragment(base), fragment(structuredClone(base))])).toThrow('PROJECTION_ID_COLLISION');
    expect(() => mergeProjectionCollections([
      fragment(base),
      fragment({ ...structuredClone(base), id: `${base.id}-other` }),
    ])).toThrow('SOURCE_OBJECT_ID_COLLISION');
    expect(() => mergeProjectionCollections([
      fragment(base),
      fragment({ ...structuredClone(base), id: `${base.id}-other`, source_id: `${base.source_id}-other` }),
    ])).toThrow('CANONICAL_NAME_COLLISION');
    expect(() => mergeProjectionCollections([
      { objects: legacy.objects, relations: [legacy.relations[0]] },
      { objects: [], relations: [structuredClone(legacy.relations[0])] },
    ])).toThrow('RELATION_ID_COLLISION');
    expect(() => mergeProjectionCollections([
      fragment(base),
      fragment({ ...structuredClone(base), id: `${base.id}-other`, source_id: `${base.source_id}-other`, title: `${base.title}-other` }),
    ], { slugger: () => 'same-route' })).toThrow('OBJECT_ROUTE_COLLISION');
  });

  test('enforces relation-kind semantics and bounded catalogue projections', () => {
    const map = buildKnowledgeMap(projected, { maxNodes: 50, maxEdges: 100 });
    expect(map.context.max_nodes).toBe(catalogue.manifest.limits.max_projection_nodes);
    expect(map.context.max_edges).toBe(catalogue.manifest.limits.max_projection_edges);
    expect(map.completeness.truncated).toBe(true);
    expect(map.nodes).toHaveLength(50);
    expect(map.edges.length).toBeLessThanOrEqual(100);

    const logical = structuredClone(projected);
    (logical.relations[0] as { logical_implication: boolean }).logical_implication = true;
    expect(() => buildKnowledgeMap(logical)).toThrow('INVALID_CATALOGUE_RELATION_SEMANTICS');

    const wrongProvenance = structuredClone(projected);
    const typeReference = wrongProvenance.relations.find(edge => edge.type === 'TYPE_REFERENCES')!;
    typeReference.provenance.source = wrongProvenance.objects.find(node => node.kind === 'SOURCE_MODULE' && canonicalJson(node.source) !== canonicalJson(typeReference.provenance.source))!.source;
    expect(() => buildKnowledgeMap(wrongProvenance)).toThrow('INVALID_PROJECTION_PROVENANCE');
  });
});
