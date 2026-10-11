import { describe, expect, test } from 'vitest';
import { loadObjectProjections } from '../data/object-projections';
import { validatePublicRecordSchema } from './catalog';
import { buildKnowledgeMap, serializeKnowledgeMap, readKnowledgeMap } from './knowledge-map';
import { displayProjection, traceDisplayed } from '../scripts/knowledge-map';
import { objectRoutes, objectSlug } from './object-locators';

describe('non-authoritative map export and separate read-only reader', () => {
  test('preserves filtered export provenance, exact edges, scope and selection without evidence authority', async () => {
    const map = buildKnowledgeMap(await loadObjectProjections());
    const receipt = map.nodes.find(node => node.source_id === 'mathgraph.l4yaml.48-case-qualification')!;
    const displayed = displayProjection(map, ['RESOLVE_RECEIPT', 'RESOLVE_CLAIM'], 100, receipt.id);
    expect(displayed.nodes).toHaveLength(11);
    expect(displayed.edges).toHaveLength(4);
    expect(displayed.source_pins).toEqual(map.source_pins);
    expect(displayed.completeness).toEqual({ scope: 'SELECTED_ADAPTER_OUTPUT', total_nodes: 14, total_edges: 7, omitted_nodes: 3, omitted_edges: 3, truncated: true });
    expect(displayed.extensions.at(-1)?.payload).toEqual({ selected_id: receipt.id, kinds: ['RESOLVE_RECEIPT', 'RESOLVE_CLAIM'], max_nodes: 100, semantics: 'DISPLAY_ONLY', counts_scope: 'ORIGINAL_SELECTED_ADAPTER_OUTPUT' });
    for (const edge of displayed.edges) expect(edge).toEqual(map.edges.find(original => original.id === edge.id));
    expect(readKnowledgeMap(JSON.stringify(displayed)).authority).toBe('NONE');
    expect(() => validatePublicRecordSchema(displayed)).toThrow('PUBLIC_RECORD_SCHEMA_INVALID');
    expect(displayProjection(map, [], 100, null).nodes).toEqual([]);
    expect(displayProjection(map, ['RESOLVE_CLAIM'], 0, null).edges).toEqual([]);
    expect(map.completeness.truncated).toBe(false);
  });

  test('traverses only currently displayed directed edge occurrences and terminates on cycles', async () => {
    const map = buildKnowledgeMap(await loadObjectProjections());
    const receipt = map.nodes.find(node => node.source_id === 'mathgraph.l4yaml.48-case-qualification')!;
    const claim = map.nodes.find(node => node.source_id === 'jpl.l4yaml.finite_parser_acceptance')!;
    expect(traceDisplayed(map, receipt.id, 'outgoing')).toEqual([claim.id]);
    expect(traceDisplayed(map, receipt.id, 'incoming')).toEqual([]);
    expect(traceDisplayed(map, claim.id, 'incoming')).toEqual([receipt.id]);
    const filtered = displayProjection(map, ['RESOLVE_CLAIM'], 100, claim.id);
    expect(traceDisplayed(filtered, claim.id, 'incoming')).toEqual([]);
    expect(traceDisplayed(filtered, receipt.id, 'outgoing')).toEqual([]);
    const parallel = { ...map, completeness: { ...map.completeness, total_edges: 8 }, edges: [...map.edges, { ...map.edges[0], id: 'parallel-occurrence' }] };
    const parallelView = displayProjection(parallel, ['RESOLVE_CLAIM', 'RESOLVE_RECEIPT', 'RESOLUTION_SNAPSHOT'], 100, null);
    expect(readKnowledgeMap(JSON.stringify(parallelView)).projection.edges).toHaveLength(8);
    const cycle = { ...map, edges: [...map.edges, { ...map.edges[0], from: claim.id, to: receipt.id }] };
    expect(traceDisplayed(cycle, receipt.id, 'outgoing')).toEqual([claim.id]);
  });

  test('retains original omissions when a bounded projection is filtered again', async () => {
    const bounded = buildKnowledgeMap(await loadObjectProjections(), { maxNodes: 2, maxEdges: 0 });
    const view = displayProjection(bounded, ['FINITE_CAPABILITY', 'SOURCE_CHECK'], 1, null);
    expect(view.completeness.total_nodes).toBe(14);
    expect(view.completeness.omitted_nodes).toBe(13);
    expect(view.completeness.omitted_edges).toBe(7);
    expect(readKnowledgeMap(JSON.stringify(view)).projection.nodes).toHaveLength(1);
  });

  test('uses stable presentation locators while refusing duplicate route identities', async () => {
    const { objects } = await loadObjectProjections();
    expect(objectRoutes(objects)).toHaveLength(14);
    expect(objectSlug('same name@1')).not.toBe(objectSlug('same name@2'));
    expect(objectSlug(objects[0].id)).toBe(objectRoutes(objects)[0].slug);
    expect(() => objectRoutes([objects[0], objects[0]])).toThrow('OBJECT_LOCATOR_COLLISION');
  });

  test('exports deterministic directed relations with valid endpoints, provenance and all source pins', async () => {
    const source = await loadObjectProjections();
    const map = buildKnowledgeMap(source);
    const reversed = buildKnowledgeMap({ objects: [...source.objects].reverse(), relations: [...source.relations].reverse() });
    expect(serializeKnowledgeMap(map)).toBe(serializeKnowledgeMap(reversed));
    expect(map.authority).toBe('NONE');
    expect(map.kind).toBe('PRESENTATION_PROJECTION');
    expect(map.completeness).toEqual({ scope: 'SELECTED_ADAPTER_OUTPUT', total_nodes: source.objects.length, total_edges: source.relations.length, omitted_nodes: 0, omitted_edges: 0, truncated: false });
    const ids = new Set(map.nodes.map(node => node.id));
    expect(map.nodes.map(node => node.id)).toEqual([...ids].sort());
    for (const edge of map.edges) {
      expect(edge.directed).toBe(true);
      expect(ids.has(edge.from) && ids.has(edge.to)).toBe(true);
      expect(map.source_pins).toContainEqual(edge.provenance.source);
    }
    for (const object of source.objects) {
      expect(map.source_pins).toContainEqual(object.source);
      for (const pin of object.supporting_sources) expect(map.source_pins).toContainEqual(pin);
    }
    expect(readKnowledgeMap(serializeKnowledgeMap(map))).toEqual({ kind: 'READ_ONLY_PROJECTION', authority: 'NONE', projection: map });
    expect(() => validatePublicRecordSchema(map)).toThrow('PUBLIC_RECORD_SCHEMA_INVALID');
    expect(() => validatePublicRecordSchema(readKnowledgeMap(serializeKnowledgeMap(map)))).toThrow('PUBLIC_RECORD_SCHEMA_INVALID');
  });

  test('records filters and selection, bounds nodes and edges, and reports truncation without dangling edges', async () => {
    const source = await loadObjectProjections();
    const map = buildKnowledgeMap(source, { kinds: ['RESOLVE_CLAIM', 'RESOLVE_RECEIPT'], maxNodes: 6, maxEdges: 1 });
    expect(map.context).toEqual({ object_ids: [], kinds: ['RESOLVE_CLAIM', 'RESOLVE_RECEIPT'], max_nodes: 6, max_edges: 1 });
    expect(map.nodes).toHaveLength(6);
    expect(map.edges.length).toBeLessThanOrEqual(1);
    expect(map.completeness.total_nodes).toBe(11);
    expect(map.completeness.total_edges).toBe(4);
    expect(map.completeness.omitted_nodes).toBe(5);
    expect(map.completeness.omitted_edges).toBe(4 - map.edges.length);
    expect(map.completeness.truncated).toBe(true);
    expect(map.edges.every(edge => map.nodes.some(node => node.id === edge.from) && map.nodes.some(node => node.id === edge.to))).toBe(true);
    const selected = buildKnowledgeMap(source, { objectIds: [source.objects[0].id], maxNodes: 0, maxEdges: 0 });
    expect(selected.context.object_ids).toEqual([source.objects[0].id]);
    expect(selected.nodes).toEqual([]);
    expect(selected.completeness.total_nodes).toBe(1);
    expect(() => buildKnowledgeMap(source, { maxNodes: -1 })).toThrow('INVALID_PROJECTION_LIMIT');
  });

  test('declines unsupported versions and critical extensions and rejects forged graph structure', async () => {
    const source = await loadObjectProjections();
    const map = buildKnowledgeMap(source);
    const read = (value: unknown) => readKnowledgeMap(JSON.stringify(value));
    expect(() => read({ ...map, schema: 'mathgraph.website-knowledge-map.v2' })).toThrow('UNSUPPORTED_PROJECTION_VERSION');
    expect(() => read({ ...map, extensions: [{ id: 'urn:future', critical: true, payload: {} }] })).toThrow('UNSUPPORTED_CRITICAL_EXTENSION');
    const extended = { ...map, extensions: [{ id: 'urn:note', critical: false, payload: { note: 'opaque' } }] };
    expect(read(extended).projection.extensions).toEqual(extended.extensions);
    expect(() => read({ ...map, authority: 'VERIFIED_PROOF' })).toThrow('INVALID_PRESENTATION_PROJECTION');
    expect(() => read({ ...map, edges: [{ ...map.edges[0], to: 'missing' }] })).toThrow('INVALID_PROJECTION_ENDPOINT');
    expect(() => read({ ...map, edges: [{ ...map.edges[0], type: 'EQUIVALENT_TO' }] })).toThrow('INVALID_PRESENTATION_PROJECTION');
    expect(() => read({ ...map, nodes: [...map.nodes, map.nodes[0]] })).toThrow('DUPLICATE_PROJECTION_ID');
    expect(() => read({ ...map, source_pins: [] })).toThrow('MISSING_PROJECTION_SOURCE_PIN');
    expect(() => read({ ...map, completeness: { ...map.completeness, total_nodes: 0 } })).toThrow('INVALID_PROJECTION_COMPLETENESS');
    expect(() => read({ ...map, nodes: [{ ...map.nodes[0], authority: 'VERIFIED_PROOF' }] })).toThrow('INVALID_PRESENTATION_PROJECTION');
    expect(() => read({ ...map, extra_authority: 'VERIFIED_PROOF' })).toThrow('INVALID_PRESENTATION_PROJECTION');
    expect(() => buildKnowledgeMap({ ...source, relations: [{ ...source.relations[0], to: 'missing' }] })).toThrow('INVALID_PROJECTION_ENDPOINT');
  });

  test('refuses relation provenance or endpoint kinds that disagree with the declared relation type', async () => {
    const map = buildKnowledgeMap(await loadObjectProjections());
    const evidence = map.edges.find(edge => edge.type === 'EVIDENCE_FOR')!;
    const foreignSource = map.nodes.find(node => node.kind === 'SOURCE_CHECK')!.source;
    const wrongSource = map.edges.map(edge => edge.id === evidence.id ? { ...edge, provenance: { ...edge.provenance, source: foreignSource } } : edge);
    const wrongType = map.edges.map(edge => edge.id === evidence.id ? { ...edge, type: 'WITHDRAWS' } : edge);
    expect(() => readKnowledgeMap(JSON.stringify({ ...map, edges: wrongSource }))).toThrow('INVALID_PROJECTION_PROVENANCE');
    expect(() => readKnowledgeMap(JSON.stringify({ ...map, edges: wrongType }))).toThrow('INVALID_PROJECTION_RELATION');
  });
});
