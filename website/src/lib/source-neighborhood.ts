import { canonicalJson } from './integrity';
import type { KnowledgeMapProjection } from './knowledge-map';
import { objectSlug } from './object-locators';

export interface SourceNeighborhoodV1 {
  schema: 'mathgraph.website-source-neighborhood.v1';
  kind: 'PRESENTATION_PROJECTION';
  authority: 'NONE';
  center_id: string;
  context: { depth: 1 | 2; max_nodes: number; max_edges: number };
  completeness: KnowledgeMapProjection['completeness'];
  source_pins: KnowledgeMapProjection['source_pins'];
  status: {
    source_status: 'SOURCE_INDEXED';
    independent_verification: 'NOT_CHECKED';
    current_applicability: 'NOT_CHECKED';
    freshness: 'PINNED_HISTORICAL_SOURCE';
    action_authorization: 'NONE';
  };
  nodes: Array<{ id: string; title: string; kind: 'SOURCE_MODULE' | 'SOURCE_DECLARATION'; href: string }>;
  relations: Array<{
    id: string;
    type: 'DECLARES' | 'IMPORTS_MODULE' | 'TYPE_REFERENCES';
    from: string;
    to: string;
    directed: true;
    authority: 'NONE';
    logical_implication: false;
    semantic_equivalence: false;
  }>;
  semantics: 'READ_ONLY_SOURCE_STRUCTURE';
}

function requireNeighborhood(condition: boolean, code: string): asserts condition {
  if (!condition) throw new Error(code);
}

/** Compact browser/export view of an already validated bounded map. It creates no relation or authority. */
export function sourceNeighborhoodV1(map: KnowledgeMapProjection): SourceNeighborhoodV1 {
  const extension = map.extensions.find(item => item.id === 'mathgraph.website-neighborhood.v1');
  const payload = extension?.payload as { center_id?: unknown; depth?: unknown; semantics?: unknown } | undefined;
  requireNeighborhood(map.context.mode === 'NEIGHBORHOOD'
    && map.authority === 'NONE'
    && payload?.semantics === 'PRESENTATION_ONLY'
    && typeof payload.center_id === 'string'
    && (payload.depth === 1 || payload.depth === 2), 'INVALID_SOURCE_NEIGHBORHOOD');
  const center = map.nodes.find(node => node.id === payload.center_id);
  requireNeighborhood(center !== undefined, 'MISSING_SOURCE_NEIGHBORHOOD_CENTER');
  requireNeighborhood(map.nodes.every(node => node.kind === 'SOURCE_MODULE' || node.kind === 'SOURCE_DECLARATION'), 'UNSUPPORTED_SOURCE_NEIGHBORHOOD_NODE');
  requireNeighborhood(map.edges.every(edge => (edge.type === 'DECLARES' || edge.type === 'IMPORTS_MODULE' || edge.type === 'TYPE_REFERENCES')
    && edge.authority === 'NONE' && edge.logical_implication === false && edge.semantic_equivalence === false), 'UNSUPPORTED_SOURCE_NEIGHBORHOOD_RELATION');
  const nodes = map.nodes.map(node => ({
    id: node.source_id,
    title: node.title,
    kind: node.kind as 'SOURCE_MODULE' | 'SOURCE_DECLARATION',
    href: `/objects/${objectSlug(node)}/`,
  }));
  const ids = new Set(nodes.map(node => node.id));
  const relations = map.edges.map(edge => ({
    id: edge.source_relation_id!, type: edge.type as SourceNeighborhoodV1['relations'][number]['type'],
    from: edge.source_id, to: edge.target_id, directed: true as const, authority: 'NONE' as const,
    logical_implication: false as const, semantic_equivalence: false as const,
  }));
  requireNeighborhood(new Set(nodes.map(node => node.id)).size === nodes.length
    && new Set(relations.map(edge => edge.id)).size === relations.length
    && relations.every(edge => ids.has(edge.from) && ids.has(edge.to)), 'INVALID_SOURCE_NEIGHBORHOOD_ENDPOINT');
  return {
    schema: 'mathgraph.website-source-neighborhood.v1', kind: 'PRESENTATION_PROJECTION', authority: 'NONE',
    center_id: center.source_id,
    context: { depth: payload.depth, max_nodes: map.context.max_nodes, max_edges: map.context.max_edges },
    completeness: structuredClone(map.completeness),
    source_pins: structuredClone(map.source_pins),
    status: {
      source_status: 'SOURCE_INDEXED', independent_verification: 'NOT_CHECKED', current_applicability: 'NOT_CHECKED',
      freshness: 'PINNED_HISTORICAL_SOURCE', action_authorization: 'NONE',
    },
    nodes, relations, semantics: 'READ_ONLY_SOURCE_STRUCTURE',
  };
}

export function serializeSourceNeighborhoodV1(map: KnowledgeMapProjection): string {
  return canonicalJson(sourceNeighborhoodV1(map));
}
