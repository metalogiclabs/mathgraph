import Ajv from 'ajv';
import { canonicalJson } from './integrity';
import { objectKinds, relationTypes, type ObjectKind, type ObjectProjection, type ProjectionCollection, type RelationProjection, type SourcePin } from './object-projections';

export interface KnowledgeMapProjection {
  schema: 'mathgraph.website-knowledge-map.v1';
  kind: 'PRESENTATION_PROJECTION';
  authority: 'NONE';
  context: { object_ids: string[]; kinds: ObjectKind[]; max_nodes: number; max_edges: number; mode?: 'NEIGHBORHOOD' };
  completeness: { scope: 'SELECTED_ADAPTER_OUTPUT'; total_nodes: number; total_edges: number; omitted_nodes: number; omitted_edges: number; truncated: boolean };
  source_pins: SourcePin[];
  nodes: ObjectProjection[];
  edges: RelationProjection[];
  extensions: Array<{ id: string; critical: boolean; payload: unknown }>;
}
export interface MapSelection { objectIds?: string[]; kinds?: ObjectKind[]; maxNodes?: number; maxEdges?: number }
export interface NeighborhoodSelection {
  depth?: 1 | 2;
  maxNodes?: number;
  maxEdges?: number;
  kinds?: ObjectKind[];
  relationTypes?: RelationProjection['type'][];
}
export interface ReadOnlyProjection {
  kind: 'READ_ONLY_PROJECTION';
  authority: 'NONE';
  projection: KnowledgeMapProjection;
}

// Local presentation-format validation only. Never registered with an evidence importer.
const text = { type: 'string', minLength: 1 };
const strings = { type: 'array', items: text };
const natural = { type: 'integer', minimum: 0, maximum: Number.MAX_SAFE_INTEGER };
const digest = { type: 'string', pattern: '^[a-f0-9]{64}$' };
function shape(properties: Record<string, unknown>, required = Object.keys(properties)) {
  return { type: 'object', properties, required, additionalProperties: false };
}
const sourcePinShape = {
  ...shape({ id: text, contract: text, version: text, locator: text, content_sha256: digest, transport_sha256: digest }, ['id', 'contract', 'version', 'locator']),
  anyOf: [{ required: ['content_sha256'] }, { required: ['transport_sha256'] }],
};
const nodeShape = shape({
  id: text, source_id: text, title: text, kind: { enum: objectKinds }, authority: { const: 'NONE' },
  source: sourcePinShape, supporting_sources: { type: 'array', items: sourcePinShape }, pointer: { type: 'string', pattern: '^($|/)' },
  axes: shape({
    historical_result: text, lifecycle: text, research_maturity: text, current_applicability: text,
    freshness: text, action_authorization: text, source_status: text, independent_verification: text,
  }, ['historical_result', 'lifecycle', 'research_maturity', 'current_applicability', 'freshness', 'action_authorization']),
  verifier_authority: strings, assumptions: strings, replay_boundary: strings, unknowns: strings, unsupported_semantics: strings,
  details: { type: 'object' },
});
const edgeShape = shape({
  id: text, type: { enum: relationTypes }, from: text, to: text, source_id: text, target_id: text,
  directed: { const: true }, authority: { const: 'NONE' }, source_relation_id: text,
  logical_implication: { type: 'boolean' }, semantic_equivalence: { type: 'boolean' },
  provenance: shape({ source: sourcePinShape, pointer: { type: 'string', pattern: '^/' } }),
}, ['id', 'type', 'from', 'to', 'source_id', 'target_id', 'directed', 'authority', 'provenance']);
const format = shape({
  schema: { const: 'mathgraph.website-knowledge-map.v1' }, kind: { const: 'PRESENTATION_PROJECTION' }, authority: { const: 'NONE' },
  context: shape({ object_ids: { ...strings, uniqueItems: true }, kinds: { type: 'array', items: { enum: objectKinds }, uniqueItems: true }, max_nodes: natural, max_edges: natural, mode: { const: 'NEIGHBORHOOD' } }, ['object_ids', 'kinds', 'max_nodes', 'max_edges']),
  completeness: shape({ scope: { const: 'SELECTED_ADAPTER_OUTPUT' }, total_nodes: natural, total_edges: natural, omitted_nodes: natural, omitted_edges: natural, truncated: { type: 'boolean' } }),
  source_pins: { type: 'array', items: sourcePinShape, uniqueItems: true },
  nodes: { type: 'array', items: nodeShape }, edges: { type: 'array', items: edgeShape },
  extensions: { type: 'array', items: shape({ id: text, critical: { type: 'boolean' }, payload: {} }) },
});
const ajv = new Ajv({ allErrors: true, strict: true, strictRequired: false });
const validateFormat = ajv.compile<KnowledgeMapProjection>(format);
const validateCollection = ajv.compile<ProjectionCollection>(shape({ objects: { type: 'array', items: nodeShape }, relations: { type: 'array', items: edgeShape } }));

function requireMap(condition: boolean, code: string): asserts condition {
  if (!condition) throw new Error(code);
}
function graphIntegrity(nodes: ObjectProjection[], edges: RelationProjection[]): void {
  const byId = new Map(nodes.map(node => [node.id, node]));
  requireMap(byId.size === nodes.length
    && new Set(nodes.map(node => node.source_id)).size === nodes.length
    && new Set(edges.map(edge => edge.id)).size === edges.length
    && new Set(edges.flatMap(edge => edge.source_relation_id === undefined ? [] : [edge.source_relation_id])).size
      === edges.filter(edge => edge.source_relation_id !== undefined).length, 'DUPLICATE_PROJECTION_ID');
  for (const edge of edges) {
    const from = byId.get(edge.from);
    const to = byId.get(edge.to);
    requireMap(from !== undefined && to !== undefined && from.source_id === edge.source_id && to.source_id === edge.target_id, 'INVALID_PROJECTION_ENDPOINT');
    const legacy = edge.type === 'EVIDENCE_FOR' || edge.type === 'PREMISE_FOR' || edge.type === 'WITHDRAWS';
    if (legacy) {
      requireMap(canonicalJson(edge.provenance.source) === canonicalJson(from.source)
        && canonicalJson(edge.provenance.source) === canonicalJson(to.source), 'INVALID_PROJECTION_PROVENANCE');
      requireMap(edge.logical_implication === undefined && edge.semantic_equivalence === undefined
        && edge.source_relation_id === undefined, 'INVALID_PROJECTION_RELATION');
    } else {
      requireMap(canonicalJson(edge.provenance.source) === canonicalJson(from.source), 'INVALID_PROJECTION_PROVENANCE');
      requireMap(edge.logical_implication === false && edge.semantic_equivalence === false
        && edge.source_relation_id !== undefined, 'INVALID_CATALOGUE_RELATION_SEMANTICS');
      const fromDetails = from.details as { module_id?: unknown; source?: { repository?: unknown; commit?: unknown; tree?: unknown } };
      const toDetails = to.details as { module_id?: unknown; source?: { repository?: unknown; commit?: unknown; tree?: unknown } };
      requireMap(typeof fromDetails.module_id === 'string' && typeof toDetails.module_id === 'string', 'INVALID_PROJECTION_PROVENANCE');
      requireMap([
        fromDetails.source?.repository, fromDetails.source?.commit, fromDetails.source?.tree,
        toDetails.source?.repository, toDetails.source?.commit, toDetails.source?.tree,
      ].every(value => typeof value === 'string'), 'INVALID_PROJECTION_PROVENANCE');
      const sourceIdentity = (details: typeof fromDetails) => canonicalJson({
        repository: details.source?.repository, commit: details.source?.commit, tree: details.source?.tree,
      });
      requireMap(sourceIdentity(fromDetails) === sourceIdentity(toDetails), 'INVALID_PROJECTION_PROVENANCE');
      if (edge.type === 'DECLARES') requireMap(fromDetails.module_id === toDetails.module_id
        && canonicalJson(from.source) === canonicalJson(to.source), 'INVALID_PROJECTION_PROVENANCE');
    }
    const validType = edge.type === 'EVIDENCE_FOR'
      ? from.kind === 'RESOLVE_RECEIPT' && to.kind === 'RESOLVE_CLAIM'
      : edge.type === 'PREMISE_FOR'
        ? from.kind === 'RESOLVE_CLAIM' && to.kind === 'RESOLVE_CLAIM'
        : edge.type === 'WITHDRAWS'
          ? from.kind === 'RESOLUTION_SNAPSHOT' && to.kind === 'RESOLVE_RECEIPT'
          : edge.type === 'DECLARES'
            ? from.kind === 'SOURCE_MODULE' && to.kind === 'SOURCE_DECLARATION'
            : edge.type === 'IMPORTS_MODULE'
              ? from.kind === 'SOURCE_MODULE' && to.kind === 'SOURCE_MODULE'
              : from.kind === 'SOURCE_DECLARATION' && to.kind === 'SOURCE_DECLARATION';
    requireMap(validType, 'INVALID_PROJECTION_RELATION');
  }
}
function pinsFor(nodes: ObjectProjection[], edges: RelationProjection[]): SourcePin[] {
  const pins = [...nodes.flatMap(node => [node.source, ...node.supporting_sources]), ...edges.map(edge => edge.provenance.source)];
  return [...new Map(pins.map(pin => [canonicalJson(pin), pin])).entries()].sort(([a], [b]) => compare(a, b)).map(([, pin]) => pin);
}
function compare(left: string, right: string) { return left < right ? -1 : left > right ? 1 : 0; }
function sorted<T extends { id: string }>(items: T[]): T[] { return [...items].sort((a, b) => compare(a.id, b.id)); }

export function buildKnowledgeMap(collection: ProjectionCollection, selection: MapSelection = {}): KnowledgeMapProjection {
  requireMap(validateCollection(collection), 'INVALID_PRESENTATION_PROJECTION');
  graphIntegrity(collection.objects, collection.relations);
  const maxNodes = selection.maxNodes ?? 100;
  const maxEdges = selection.maxEdges ?? 200;
  requireMap([maxNodes, maxEdges].every(value => Number.isSafeInteger(value) && value >= 0), 'INVALID_PROJECTION_LIMIT');
  const objectIds = [...new Set(selection.objectIds ?? [])].sort();
  const kinds = [...new Set(selection.kinds ?? [])].sort();
  const selected = sorted(collection.objects.filter(node => (!objectIds.length || objectIds.includes(node.id)) && (!kinds.length || kinds.includes(node.kind))));
  const selectedIds = new Set(selected.map(node => node.id));
  const candidates = sorted(collection.relations.filter(edge => selectedIds.has(edge.from) && selectedIds.has(edge.to)));
  const nodes = selected.slice(0, maxNodes);
  const ids = new Set(nodes.map(node => node.id));
  const edges = candidates.filter(edge => ids.has(edge.from) && ids.has(edge.to)).slice(0, maxEdges);
  const omittedNodes = selected.length - nodes.length;
  const omittedEdges = candidates.length - edges.length;
  const map: KnowledgeMapProjection = {
    schema: 'mathgraph.website-knowledge-map.v1', kind: 'PRESENTATION_PROJECTION', authority: 'NONE',
    context: { object_ids: objectIds, kinds, max_nodes: maxNodes, max_edges: maxEdges },
    completeness: { scope: 'SELECTED_ADAPTER_OUTPUT', total_nodes: selected.length, total_edges: candidates.length, omitted_nodes: omittedNodes, omitted_edges: omittedEdges, truncated: omittedNodes > 0 || omittedEdges > 0 },
    source_pins: pinsFor(selected, candidates), nodes, edges, extensions: [],
  };
  validateProjection(map);
  return structuredClone(map);
}

/** A bounded presentation projection around one exact object. It derives no new relation or warrant. */
export function buildKnowledgeNeighborhood(
  collection: ProjectionCollection,
  centerId: string,
  selection: NeighborhoodSelection = {},
): KnowledgeMapProjection {
  requireMap(validateCollection(collection), 'INVALID_PRESENTATION_PROJECTION');
  graphIntegrity(collection.objects, collection.relations);
  const center = collection.objects.find(node => node.id === centerId);
  requireMap(center !== undefined, 'UNKNOWN_PROJECTION_CENTER');
  const depth = selection.depth ?? 1;
  const maxNodes = selection.maxNodes ?? 50;
  const maxEdges = selection.maxEdges ?? 100;
  requireMap(depth === 1 || depth === 2, 'INVALID_PROJECTION_DEPTH');
  requireMap(Number.isSafeInteger(maxNodes) && maxNodes >= 1
    && Number.isSafeInteger(maxEdges) && maxEdges >= 0, 'INVALID_PROJECTION_LIMIT');
  const kinds = [...new Set(selection.kinds ?? [])].sort();
  requireMap(kinds.every(kind => objectKinds.includes(kind)), 'INVALID_PROJECTION_KIND');
  const selectedRelationTypes = [...new Set(selection.relationTypes ?? relationTypes)].sort();
  requireMap(selectedRelationTypes.every(type => relationTypes.includes(type)), 'INVALID_PROJECTION_RELATION');
  const allowed = sorted(collection.relations.filter(edge => selectedRelationTypes.includes(edge.type)));
  const byId = new Map(collection.objects.map(node => [node.id, node]));
  const distances = new Map<string, number>([[centerId, 0]]);
  let frontier = [centerId];
  for (let step = 0; step < depth; step += 1) {
    const next = new Set<string>();
    for (const current of frontier) {
      for (const edge of allowed) {
        const neighbor = edge.from === current ? edge.to : edge.to === current ? edge.from : null;
        if (neighbor === null || distances.has(neighbor)) continue;
        const node = byId.get(neighbor)!;
        if (kinds.length > 0 && !kinds.includes(node.kind)) continue;
        distances.set(neighbor, step + 1);
        next.add(neighbor);
      }
    }
    frontier = [...next].sort(compare);
  }
  const candidates = [...distances.keys()];
  const incoming = new Set(allowed.filter(edge => edge.to === centerId).map(edge => edge.from));
  const outgoing = new Set(allowed.filter(edge => edge.from === centerId).map(edge => edge.to));
  const directSeeds = selectedRelationTypes.flatMap(type => {
    const neighbors = allowed.filter(edge => edge.type === type && (edge.from === centerId || edge.to === centerId))
      .map(edge => edge.from === centerId ? edge.to : edge.from)
      .filter(id => distances.has(id))
      .sort(compare);
    return neighbors.slice(0, 1);
  });
  const seeded = new Set(directSeeds);
  const remainder = candidates.filter(id => id !== centerId && !seeded.has(id)).sort((left, right) => {
    const distance = distances.get(left)! - distances.get(right)!;
    if (distance !== 0) return distance;
    return compare(left, right);
  });
  const priority = [...new Set([...directSeeds, ...remainder])];
  const selectedIds = new Set([centerId, ...priority.slice(0, maxNodes - 1)]);
  const incomingNodes = priority.filter(id => selectedIds.has(id) && incoming.has(id)).sort(compare);
  const outgoingNodes = priority.filter(id => selectedIds.has(id) && !incoming.has(id) && outgoing.has(id)).sort(compare);
  const otherNodes = priority.filter(id => selectedIds.has(id) && !incoming.has(id) && !outgoing.has(id))
    .sort((left, right) => distances.get(left)! - distances.get(right)! || compare(left, right));
  const nodes = [...incomingNodes, centerId, ...outgoingNodes, ...otherNodes].map(id => byId.get(id)!);
  const candidateIds = new Set(candidates);
  const candidateEdges = allowed.filter(edge => candidateIds.has(edge.from) && candidateIds.has(edge.to));
  const edges = candidateEdges.filter(edge => selectedIds.has(edge.from) && selectedIds.has(edge.to))
    .sort((left, right) => {
      const leftCenter = left.from === centerId || left.to === centerId ? 0 : 1;
      const rightCenter = right.from === centerId || right.to === centerId ? 0 : 1;
      return leftCenter - rightCenter || compare(left.id, right.id);
    })
    .slice(0, maxEdges);
  const map: KnowledgeMapProjection = {
    schema: 'mathgraph.website-knowledge-map.v1', kind: 'PRESENTATION_PROJECTION', authority: 'NONE',
    context: { object_ids: [centerId], kinds, max_nodes: maxNodes, max_edges: maxEdges, mode: 'NEIGHBORHOOD' },
    completeness: {
      scope: 'SELECTED_ADAPTER_OUTPUT', total_nodes: candidates.length, total_edges: candidateEdges.length,
      omitted_nodes: candidates.length - nodes.length, omitted_edges: candidateEdges.length - edges.length,
      truncated: candidates.length > nodes.length || candidateEdges.length > edges.length,
    },
    source_pins: pinsFor(nodes, edges), nodes: structuredClone(nodes), edges: structuredClone(edges),
    extensions: [{
      id: 'mathgraph.website-neighborhood.v1', critical: false,
      payload: { center_id: centerId, depth, relation_types: selectedRelationTypes, semantics: 'PRESENTATION_ONLY' },
    }],
  };
  validateProjection(map);
  return map;
}

function validateProjection(value: unknown): asserts value is KnowledgeMapProjection {
  requireMap(typeof value === 'object' && value !== null && 'schema' in value && value.schema === 'mathgraph.website-knowledge-map.v1', 'UNSUPPORTED_PROJECTION_VERSION');
  requireMap(validateFormat(value), 'INVALID_PRESENTATION_PROJECTION');
  requireMap(!value.extensions.some(extension => extension.critical), 'UNSUPPORTED_CRITICAL_EXTENSION');
  graphIntegrity(value.nodes, value.edges);
  const pins = new Set(value.source_pins.map(canonicalJson));
  requireMap(pinsFor(value.nodes, value.edges).every(pin => pins.has(canonicalJson(pin))), 'MISSING_PROJECTION_SOURCE_PIN');
  const { completeness: c, context } = value;
  requireMap(c.total_nodes === value.nodes.length + c.omitted_nodes && c.total_edges === value.edges.length + c.omitted_edges && c.truncated === (c.omitted_nodes > 0 || c.omitted_edges > 0) && value.nodes.length <= context.max_nodes && value.edges.length <= context.max_edges, 'INVALID_PROJECTION_COMPLETENESS');
  requireMap(value.nodes.every(node => (context.mode === 'NEIGHBORHOOD' || !context.object_ids.length || context.object_ids.includes(node.id))
    && (!context.kinds.length || node.id === context.object_ids[0] || context.kinds.includes(node.kind))), 'INVALID_PROJECTION_SELECTION');
}

/** Stable serialization of a presentation, never a certificate or proof. */
export function serializeKnowledgeMap(map: KnowledgeMapProjection): string {
  validateProjection(map);
  return canonicalJson({ ...map, nodes: sorted(map.nodes), edges: sorted(map.edges), source_pins: [...map.source_pins].sort((a, b) => compare(canonicalJson(a), canonicalJson(b))) });
}

/** A distinct read-only wrapper that is deliberately not an evidence-import input. */
export function readKnowledgeMap(serialized: string): ReadOnlyProjection {
  const parsed: unknown = JSON.parse(serialized);
  validateProjection(parsed);
  return { kind: 'READ_ONLY_PROJECTION', authority: 'NONE', projection: parsed };
}
